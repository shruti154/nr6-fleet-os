import altair as alt
import streamlit as st

# ---------- Design tokens: every colour used in the app, in one place ----------
INK = "#E4EAF0"        # main text
MUTED = "#93A3B5"      # labels, axes
SURFACE = "#141E28"    # card background
LINE = "#263443"       # borders
BLUE = "#7CC4F5"       # main accent
YELLOW = "#F5C542"     # "watch this"
GREEN = "#5CC08A"      # good / working
RED = "#F2685C"        # bad / fault
VENDOR_COLOURS = {"Keenon": "#8A9BB0", "Pudu": BLUE, "Unitree": YELLOW}
STATE_COLOURS = {"WORKING": GREEN, "CHARGING": BLUE, "FAULT": RED, "IDLE": MUTED, "OFFLINE": MUTED}


def apply_style():
    """Add the app's custom CSS to the current page."""
    st.html(f"""
    <style>
      .block-container {{ padding-top: 2.2rem; }}
      .eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; letter-spacing: 0.14em;
                  text-transform: uppercase; color: {BLUE}; margin-bottom: 0.2rem; }}
      .status-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end; padding-top: 1.6rem; }}
      .chip {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; padding: 0.3rem 0.7rem;
               border: 1px solid {LINE}; border-radius: 999px; color: {INK}; background: {SURFACE}; }}
      .chip b {{ font-weight: 500; margin-left: 0.35rem; }}
      .dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 0.4rem; }}
      [class*="st-key-panel"] {{ background: {SURFACE}; }}
      .board {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 0.6rem; }}
      .tile {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 4px; padding: 0.7rem 0.8rem; }}
      .tile .id {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: {INK}; }}
      .tile .vendor {{ font-size: 0.75rem; color: {MUTED}; margin-bottom: 0.5rem; }}
      .tile .state {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.06em; }}
      .tile .bar {{ height: 4px; background: {LINE}; border-radius: 2px; margin-top: 0.55rem; overflow: hidden; }}
      .tile .bar i {{ display: block; height: 100%; }}
      .tile .risk {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.05em;
                     margin-top: 0.5rem; }}
      .stButton button[kind="primary"] {{ color: #0E151D; font-weight: 600; }}
    </style>
    """)


# Charts follow the same quiet style as the page
@alt.theme.register("nr6", enable=True)
def nr6_chart_theme():
    return {"config": {
        "font": "Public Sans",
        "background": "transparent",
        "axis": {"labelColor": MUTED, "titleColor": MUTED, "gridColor": "#1F2B38",
                 "domainColor": "#33445A", "tickColor": "#33445A", "titleFontWeight": 500},
        "legend": {"labelColor": INK},
        "view": {"stroke": None},
    }}