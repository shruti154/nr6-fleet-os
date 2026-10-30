import random

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from nr6.pipeline import run_pipeline

REPORTS_PER_HOUR = 12
LOOKBACK = 24 * REPORTS_PER_HOUR      # features use the last 24 hours
HORIZON = 6 * REPORTS_PER_HOUR        # predict a fault in the next 6 hours
VENDORS = ["Keenon", "Pudu", "Unitree"]
FEATURES = ["motor_temp_c", "temp_avg_last_6h", "faults_last_24h", "fault_time_last_24h", "battery_pct"] + \
    [f"is_{v}" for v in VENDORS]


def make_features(telemetry):
    """Turn raw canonical telemetry into one row per robot per hour, with
    what we knew at that moment (features) and what happened next (label)."""
    df = telemetry.sort_values(["robot_serial", "observed_at"]).copy()
    df["in_fault"] = (df["state"] == "FAULT").astype(int)
    previous = df.groupby("robot_serial")["in_fault"].shift(1, fill_value=0)
    df["fault_started"] = ((df["in_fault"] == 1) & (previous == 0)).astype(int)

    rows = []
    for robot, g in df.groupby("robot_serial"):
        g = g.reset_index(drop=True)
        # Looking back: what happened in the last 24 hours
        g["faults_last_24h"] = g["fault_started"].rolling(LOOKBACK, min_periods=1).sum()
        g["fault_time_last_24h"] = g["in_fault"].rolling(LOOKBACK, min_periods=1).mean()
        g["temp_avg_last_6h"] = g["motor_temp_c"].rolling(HORIZON, min_periods=1).mean()
        # Looking forward: did a new fault start in the next 6 hours? (the answer we try to predict)
        future = g["fault_started"][::-1].rolling(HORIZON, min_periods=1).sum()[::-1].shift(-1)
        g["fault_next_6h"] = (future > 0).astype(int)
        # Keep one row per hour, skipping the first day (not enough history) and the last 6 hours (no answer yet)
        g = g.iloc[LOOKBACK:len(g) - HORIZON:REPORTS_PER_HOUR]
        rows.append(g)

    data = pd.concat(rows, ignore_index=True)
    for v in VENDORS:
        data[f"is_{v}"] = (data["vendor"] == v).astype(int)
    return data


def train_and_evaluate(order, days=28, seed=7):
    """Simulate a month, train on the first three weeks, test on the last week."""
    random.seed(seed)
    data = make_features(run_pipeline(order, days))

    cutoff = data["observed_at"].sort_values().iloc[int(len(data) * 0.75)]
    train = data[data["observed_at"] < cutoff]
    test = data[data["observed_at"] >= cutoff]

    model = LogisticRegression(max_iter=1000)
    model.fit(train[FEATURES], train["fault_next_6h"])
    test = test.assign(risk=model.predict_proba(test[FEATURES])[:, 1])

    auc = roc_auc_score(test["fault_next_6h"], test["risk"])
    return model, train, test, auc


DEFAULT_TRAINING_FLEET = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}


def train_model(order=None, days=28, seed=7):
    """Train the health model on a simulated month. Used by the dashboard."""
    random.seed(seed)
    data = make_features(run_pipeline(order or DEFAULT_TRAINING_FLEET, days))
    model = LogisticRegression(max_iter=1000)
    model.fit(data[FEATURES], data["fault_next_6h"])
    return model


def current_risk(telemetry, model):
    """Each robot's chance of a new fault in the next 6 hours, judged from its latest report."""
    rows = []
    for robot, g in telemetry.sort_values("observed_at").groupby("robot_serial"):
        in_fault = (g["state"] == "FAULT").astype(int)
        started = (in_fault == 1) & (in_fault.shift(1, fill_value=0) == 0)
        last = g.iloc[-1]
        rows.append({
            "robot": robot,
            "vendor": last["vendor"],
            "motor_temp_c": last["motor_temp_c"],
            "temp_avg_last_6h": g["motor_temp_c"].tail(HORIZON).mean(),
            "faults_last_24h": started.tail(LOOKBACK).sum(),
            "fault_time_last_24h": in_fault.tail(LOOKBACK).mean(),
            "battery_pct": last["battery_pct"],
        })
    now = pd.DataFrame(rows)
    for v in VENDORS:
        now[f"is_{v}"] = (now["vendor"] == v).astype(int)
    now["risk"] = model.predict_proba(now[FEATURES])[:, 1]
    return now.sort_values("risk", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    order = {"pudu_cc1": 3, "keenon_t8": 3, "pudu_t300": 2, "unitree_g1": 1}
    model, train, test, auc = train_and_evaluate(order)

    print(f"Training rows: {len(train):,}   Test rows: {len(test):,}")
    print(f"Share of test rows with a fault in the next 6h: {test['fault_next_6h'].mean():.1%}")
    print(f"\nModel quality (AUC, 0.5 = guessing, 1.0 = perfect): {auc:.2f}")

    print("\nWhat the model learned (bigger = more risk):")
    weights = pd.Series(model.coef_[0], index=FEATURES).sort_values(ascending=False)
    print(weights.round(2).to_string())

    print("\nDoes higher predicted risk really mean more faults? (test week)")
    test["risk_band"] = pd.cut(test["risk"], [0, 0.1, 0.3, 0.6, 1.0], labels=["low", "medium", "high", "very high"])
    check = test.groupby("risk_band", observed=True).agg(rows=("risk", "size"),
                                                         predicted=("risk", "mean"),
                                                         actual=("fault_next_6h", "mean"))
    print(check.round(2).to_string())