import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import os
from sqlalchemy import create_engine

st.set_page_config(page_title="Tech Sentiment Monitor", layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────
#  DESIGN SYSTEM
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #080c12 !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #1e2733 !important;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }
[data-testid="stSelectbox"] > div > div {
    background-color: #131920 !important;
    border: 1px solid #1e2733 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stMultiSelect"] > div > div {
    background-color: #131920 !important;
    border: 1px solid #1e2733 !important;
    border-radius: 8px !important;
}
[data-testid="stNumberInput"] > div > div > input {
    background-color: #131920 !important;
    border: 1px solid #1e2733 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Mono', monospace !important;
}
[data-testid="stMetric"] {
    background: #0d1117 !important;
    border: 1px solid #1e2733 !important;
    border-radius: 12px !important;
    padding: 20px 24px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #475569 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 26px !important;
    font-weight: 500 !important;
    color: #f1f5f9 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid #1e2733 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] table { font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; }
[data-testid="stDataFrame"] thead tr th {
    background: #0d1117 !important; color: #475569 !important; font-size: 11px !important;
    font-weight: 500 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important;
    border-bottom: 1px solid #1e2733 !important; padding: 10px 16px !important;
}
[data-testid="stDataFrame"] tbody tr td {
    font-family: 'DM Mono', monospace !important; color: #cbd5e1 !important;
    border-bottom: 1px solid #111820 !important; padding: 11px 16px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td { background: #131920 !important; }
[data-testid="stExpander"] {
    background: #0d1117 !important; border: 1px solid #1e2733 !important; border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-size: 13px !important; font-weight: 500 !important;
    color: #94a3b8 !important; padding: 14px 18px !important;
}
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #1e2733 !important; gap: 0 !important; }
[data-testid="stTabs"] [role="tab"] {
    font-size: 12px !important; font-weight: 500 !important; letter-spacing: 0.04em !important;
    color: #475569 !important; padding: 8px 18px !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important; background: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #38bdf8 !important; border-bottom: 2px solid #38bdf8 !important;
}
hr { border-color: #1e2733 !important; }
[data-testid="stAlert"] { border-radius: 10px !important; border-width: 1px !important; font-size: 13px !important; }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#94a3b8", size=11),
    margin=dict(l=0, r=0, t=0, b=0),
)



_COLOR_PALETTE = [
    "#38bdf8","#76ef9f","#fb923c","#a78bfa","#f472b6",
    "#facc15","#34d399","#60a5fa","#f87171","#c084fc",
    "#e879f9","#4ade80","#fbbf24","#818cf8","#f43f5e",
]

def get_ticker_colors(tickers):
    return {t: _COLOR_PALETTE[i % len(_COLOR_PALETTE)] for i, t in enumerate(sorted(tickers))}

def mood_label(score):
    if score >= 0.25:  return "High Conviction",       "#22c55e", "#052e16"
    if score > 0.05:   return "Positive Momentum",     "#4ade80", "#052e16"
    if score < -0.25:  return "Significant Headwinds", "#f87171", "#1c0a0a"
    if score < -0.05:  return "Softening Sentiment",   "#fca5a5", "#1c0a0a"
    return             "Neutral / Low Signal",          "#94a3b8", "#0f172a"

def get_color(score):
    if score > 0.10:  return "#22c55e"
    if score < -0.10: return "#ef4444"
    return "#64748b"

def safe_keyword(raw):
    if pd.isna(raw) or str(raw).strip() in ["", "0", "None"]:
        return "General News"
    return str(raw).split(',')[0].strip()

def sentiment_bar_html(score, color):
    pct = min(max((score + 1) / 2 * 100, 0), 100)
    return f"""
    <div style="margin:18px 0 4px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#475569;
                    margin-bottom:6px;font-family:'DM Sans',sans-serif;letter-spacing:0.05em;">
            <span>PANIC −1.0</span><span>NEUTRAL</span><span>EUPHORIA +1.0</span>
        </div>
        <div style="height:6px;border-radius:3px;background:#1e2733;position:relative;overflow:hidden;">
            <div style="position:absolute;height:100%;width:2px;left:50%;background:#2d3a4a;"></div>
            <div style="position:absolute;height:100%;border-radius:3px;background:{color};
                        left:{min(pct,50):.1f}%;width:{abs(pct-50):.1f}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:5px;font-size:11px;
                    color:{color};font-family:'DM Mono',monospace;">
            <span></span><span style="font-weight:500;">{score:+.3f}</span>
        </div>
    </div>"""

def section_label(text):
    st.markdown(
        f'<div style="font-size:11px;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#334155;margin-bottom:10px;margin-top:4px;">{text}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────────
try:
    conn_uri = st.secrets["SUPABASE_URL"]
except (FileNotFoundError, KeyError):
    conn_uri = os.environ.get("SUPABASE_URL")

if not conn_uri:
    raise ValueError("Set SUPABASE_URL in Streamlit secrets or your environment")

engine   = create_engine(conn_uri)

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_sql("SELECT * FROM combined_data ORDER BY timestamp DESC LIMIT 500", engine)
    df['timestamp']       = pd.to_datetime(df['timestamp'])
    df['confidence']      = pd.to_numeric(df['confidence'],      errors='coerce').fillna(0.0)
    df['sentiment_score'] = pd.to_numeric(df['sentiment_score'], errors='coerce').fillna(0.0)
    return df


# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "alerts" not in st.session_state:
    st.session_state.alerts = {}   # {ticker: {"above": float|None, "below": float|None}}


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 20px;">
        <div style="font-size:15px;font-weight:600;color:#f1f5f9;letter-spacing:-0.01em;margin-bottom:4px;">
            Sentiment Terminal
        </div>
        <div style="font-size:11px;color:#334155;letter-spacing:0.06em;text-transform:uppercase;">
            Tech sector · 2026
        </div>
    </div>
    <div style="font-size:11px;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;
                color:#334155;margin-bottom:12px;">Signal Guide</div>
    """, unsafe_allow_html=True)
    for dot, label in [("#22c55e","Bullish > 0.20"),("#fbbf24","Neutral ±0.05"),("#ef4444","Bearish < −0.20")]:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:9px;margin-bottom:8px;">'
            f'<div style="width:7px;height:7px;border-radius:50%;background:{dot};flex-shrink:0;"></div>'
            f'<span style="font-size:12px;color:#64748b;font-family:\'DM Sans\',sans-serif;">{label}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#334155;margin-bottom:10px;">Asset Deep Dive</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
try:
    full_df      = load_data()
    all_tickers   = sorted(full_df['ticker'].unique())
    TICKER_COLORS = get_ticker_colors(all_tickers)

    # Page header
    st.markdown("""
    <div style="display:flex;align-items:baseline;justify-content:space-between;
                margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1e2733;">
        <div>
            <h1 style="font-size:22px;font-weight:600;color:#f1f5f9;letter-spacing:-0.02em;margin:0;">
                2026 Tech Sentiment Monitor
            </h1>
            <p style="font-size:13px;color:#334155;margin:4px 0 0;font-family:'DM Sans',sans-serif;">
                AI hardware cycle · Real-time news signal tracking
            </p>
        </div>
        <div style="font-size:11px;color:#334155;letter-spacing:0.05em;text-transform:uppercase;
                padding:6px 12px;border:1px solid #1e2733;border-radius:6px;">Data updated periodically</div>
    </div>
    """, unsafe_allow_html=True)

    # Delta calc
    full_df = full_df.sort_values(['ticker', 'timestamp'])
    full_df['sentiment_delta'] = full_df.groupby('ticker')['sentiment_score'].diff()
    latest_all = full_df.sort_values('timestamp', ascending=False).drop_duplicates('ticker').copy()

    # ── Alert banners ──────────────────────────
    triggered = []
    for _, row in latest_all.iterrows():
        t, s = row['ticker'], row['sentiment_score']
        cfg   = st.session_state.alerts.get(t, {})
        if cfg.get("above") is not None and s >= cfg["above"]:
            triggered.append((t, s, "above", cfg["above"]))
        if cfg.get("below") is not None and s <= cfg["below"]:
            triggered.append((t, s, "below", cfg["below"]))

    for t, s, direction, threshold in triggered:
        c = "#22c55e" if direction == "above" else "#ef4444"
        arrow = "▲" if direction == "above" else "▼"
        st.markdown(
            f'<div style="background:#0d1117;border:1px solid {c}44;border-left:3px solid {c};'
            f'border-radius:10px;padding:12px 18px;margin-bottom:10px;'
            f'display:flex;align-items:center;justify-content:space-between;">'
            f'<div><span style="font-size:13px;font-weight:600;color:{c};">{arrow} {t} Alert</span>'
            f'<span style="font-size:12px;color:#475569;margin-left:12px;">'
            f'Sentiment {direction} threshold — {s:+.3f} vs {threshold:+.2f}</span></div>'
            f'<span style="font-size:11px;color:#334155;font-family:\'DM Mono\',monospace;">{s:+.3f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Four main tabs ─────────────────────────
    tab_grid, tab_compare, tab_heatmap, tab_alerts = st.tabs([
        "Market pulse", "Compare assets", "Sentiment heatmap", "Watchlist & alerts"
    ])

    # ══════════════════════════════════════
    #  TAB 1 — GRID with sparklines + Δ
    # ══════════════════════════════════════
    with tab_grid:
        section_label("Full sector grid")

        latest_all['conf_display'] = latest_all['confidence'] * 100
        latest_all['24h'] = latest_all['sentiment_delta'].apply(
            lambda v: "▲" if v > 0.02 else ("▼" if v < -0.02 else "—")
        )
        latest_all['Δ'] = latest_all['sentiment_delta'].apply(
            lambda v: f"{v:+.3f}" if pd.notna(v) else "—"
        )

        # Sparkline lists per ticker (last 20 price points)
        sparklines = {
            tkr: full_df[full_df['ticker'] == tkr].sort_values('timestamp').tail(20)['price'].tolist()
            for tkr in all_tickers
        }
        latest_all['Sparkline'] = latest_all['ticker'].map(sparklines)

        st.dataframe(
            latest_all[['ticker','24h','Δ','price','Sparkline','sentiment_score','conf_display','top_keywords']],
            column_config={
                "ticker":          st.column_config.TextColumn("Ticker"),
                "24h":             st.column_config.TextColumn("24h"),
                "Δ":               st.column_config.TextColumn("Δ Sent."),
                "price":           st.column_config.NumberColumn("Spot Price", format="$%.2f"),
                "Sparkline":       st.column_config.LineChartColumn("7-day price"),
                "sentiment_score": st.column_config.ProgressColumn(
                    "Sentiment", min_value=-0.5, max_value=0.5, format="%.2f"
                ),
                "conf_display":    st.column_config.NumberColumn("Confidence", format="%d%%"),
                "top_keywords":    st.column_config.TextColumn("Keywords"),
            },
            hide_index=True, use_container_width=True,
            height=max(150, 38 + len(latest_all) * 35),
        )

    # ══════════════════════════════════════
    #  TAB 2 — COMPARE
    # ══════════════════════════════════════
    with tab_compare:
        section_label("Overlay up to 4 assets")

        compare_tickers = st.multiselect(
            "Tickers", all_tickers,
            default=all_tickers[:3] if len(all_tickers) >= 3 else all_tickers,
            max_selections=4, label_visibility="collapsed",
        )
        compare_mode = st.radio(
            "View", ["Price", "Sentiment score", "Confidence (%)"],
            horizontal=True, label_visibility="collapsed",
        )
        y_col_map = {"Price":"price","Sentiment score":"sentiment_score","Confidence (%)":"confidence"}
        y_col = y_col_map[compare_mode]

        if compare_tickers:
            fig = go.Figure()
            for tkr in compare_tickers:
                sub = full_df[full_df['ticker'] == tkr].sort_values('timestamp')
                y   = sub[y_col] * 100 if y_col == "confidence" else sub[y_col]
                fig.add_trace(go.Scatter(
                    x=sub['timestamp'], y=y, mode="lines", name=tkr,
                    line=dict(color=TICKER_COLORS.get(tkr,"#94a3b8"), width=2),
                    hovertemplate=f"<b>{tkr}</b> %{{y:.3f}}<extra></extra>",
                ))
            fig.update_layout(
                **PLOTLY_BASE, height=300,
                xaxis=dict(showgrid=False, zeroline=False, color="#334155"),
                yaxis=dict(showgrid=True, gridcolor="#1e2733", zeroline=False, color="#334155"),
                legend=dict(orientation="h", y=1.1, x=0, font=dict(size=11, color="#64748b"),
                            bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

            # KPI comparison cards
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            kpi_cols = st.columns(len(compare_tickers))
            for i, tkr in enumerate(compare_tickers):
                row = latest_all[latest_all['ticker'] == tkr]
                if row.empty: continue
                row = row.iloc[0]
                c   = TICKER_COLORS.get(tkr, "#94a3b8")
                with kpi_cols[i]:
                    st.markdown(
                        f'<div style="background:#0d1117;border:1px solid #1e2733;border-top:2px solid {c};'
                        f'border-radius:10px;padding:14px 16px;">'
                        f'<div style="font-size:12px;font-weight:600;color:{c};margin-bottom:8px;">{tkr}</div>'
                        f'<div style="font-size:11px;color:#475569;margin-bottom:2px;">SENTIMENT</div>'
                        f'<div style="font-size:16px;font-family:\'DM Mono\',monospace;color:#f1f5f9;margin-bottom:6px;">'
                        f'{row["sentiment_score"]:+.3f}</div>'
                        f'<div style="font-size:11px;color:#475569;margin-bottom:2px;">CONFIDENCE</div>'
                        f'<div style="font-size:16px;font-family:\'DM Mono\',monospace;color:#f1f5f9;">'
                        f'{row["confidence"]*100:.0f}%</div></div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown('<div style="color:#334155;font-size:13px;padding:32px 0;text-align:center;">'
                        'Select at least one asset above.</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════
    #  TAB 3 — HEATMAP
    # ══════════════════════════════════════
    with tab_heatmap:
        section_label("Sentiment intensity · ticker × date · last 14 days")

        hm = full_df.copy()
        hm['date'] = hm['timestamp'].dt.date
        pivot = (
            hm.groupby(['ticker','date'])['sentiment_score'].mean()
            .reset_index()
            .pivot(index='ticker', columns='date', values='sentiment_score')
            .sort_index()
            .iloc[:, -14:]
        )

        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[
                [0.0, "#7f1d1d"],[0.25,"#ef4444"],
                [0.45,"#1e2733"],[0.55,"#1e2733"],
                [0.75,"#4ade80"],[1.0, "#14532d"],
            ],
            zmid=0, zmin=-0.5, zmax=0.5,
            text=[[f"{v:.2f}" if pd.notna(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=10, color="#94a3b8", family="DM Mono"),
            hoverongaps=False,
            hovertemplate="<b>%{y}</b> · %{x}<br>Sentiment: %{z:.3f}<extra></extra>",
            colorbar=dict(
                title=dict(text="Sentiment", font=dict(size=11, color="#475569")),
                tickfont=dict(size=10, color="#475569"),
                thickness=12, len=0.8,
                bgcolor="rgba(0,0,0,0)", bordercolor="#1e2733", borderwidth=1,
            ),
            xgap=2, ygap=2,
        ))
        fig_hm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans, sans-serif", color="#94a3b8", size=11),
            margin=dict(l=0, r=0, t=0, b=0),
            height=max(280, len(pivot) * 38 + 60),
            yaxis=dict(showgrid=False, gridcolor="#1e2733", zeroline=False, color="#64748b",
                       tickfont=dict(size=11), automargin=True),
            xaxis=dict(showgrid=False, zeroline=False, color="#64748b",
                       tickfont=dict(size=10), tickangle=-30),
        )
        st.plotly_chart(fig_hm, use_container_width=True)
        st.markdown('<div style="font-size:11px;color:#334155;margin-top:4px;">'
                    'Green = bullish · Red = bearish · Grey = neutral or no data</div>',
                    unsafe_allow_html=True)

    # ══════════════════════════════════════
    #  TAB 4 — ALERTS
    # ══════════════════════════════════════
    with tab_alerts:
        section_label("Set threshold alerts · banner fires when sentiment crosses your level")

        col_form, col_active = st.columns([1, 1], gap="large")

        with col_form:
            st.markdown('<div style="font-size:12px;color:#64748b;margin-bottom:14px;">'
                        'Choose a ticker and set upper/lower sentiment thresholds. '
                        'A banner will appear at the top of the page on next refresh.</div>',
                        unsafe_allow_html=True)

            alert_ticker = st.selectbox("Ticker", all_tickers, key="alert_ticker")
            existing     = st.session_state.alerts.get(alert_ticker, {})

            a1, a2 = st.columns(2)
            with a1:
                above_val    = st.number_input("Alert above ▲", -1.0, 1.0,
                                               value=existing.get("above") or 0.25,
                                               step=0.05, format="%.2f", key="above_val")
                enable_above = st.checkbox("Enable", value=existing.get("above") is not None,
                                           key="en_above")
            with a2:
                below_val    = st.number_input("Alert below ▼", -1.0, 1.0,
                                               value=existing.get("below") or -0.20,
                                               step=0.05, format="%.2f", key="below_val")
                enable_below = st.checkbox("Enable", value=existing.get("below") is not None,
                                           key="en_below")

            if st.button("Save alert", type="primary"):
                st.session_state.alerts[alert_ticker] = {
                    "above": above_val if enable_above else None,
                    "below": below_val if enable_below else None,
                }
                st.success(f"Alert saved for {alert_ticker}")

        with col_active:
            st.markdown('<div style="font-size:12px;color:#64748b;margin-bottom:14px;">'
                        'Active alerts</div>', unsafe_allow_html=True)

            active = {t: c for t, c in st.session_state.alerts.items()
                      if c.get("above") is not None or c.get("below") is not None}

            if active:
                for tkr, cfg in active.items():
                    row = latest_all[latest_all['ticker'] == tkr]
                    cur = row['sentiment_score'].iloc[0] if not row.empty else None
                    c   = TICKER_COLORS.get(tkr, "#94a3b8")
                    ab  = f"▲ {cfg['above']:+.2f}" if cfg.get("above") is not None else ""
                    bl  = f"▼ {cfg['below']:+.2f}" if cfg.get("below") is not None else ""
                    sep = " · " if ab and bl else ""
                    cur_str = f"{cur:+.3f}" if cur is not None else "—"
                    st.markdown(
                        f'<div style="background:#0d1117;border:1px solid #1e2733;border-left:3px solid {c};'
                        f'border-radius:10px;padding:12px 16px;margin-bottom:8px;'
                        f'display:flex;align-items:center;justify-content:space-between;">'
                        f'<div><span style="font-size:13px;font-weight:600;color:{c};">{tkr}</span>'
                        f'<div style="font-size:11px;color:#334155;margin-top:3px;">{ab}{sep}{bl}</div></div>'
                        f'<div style="text-align:right;">'
                        f'<div style="font-size:11px;color:#475569;margin-bottom:2px;">NOW</div>'
                        f'<div style="font-family:\'DM Mono\',monospace;font-size:13px;color:#f1f5f9;">{cur_str}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(f"Remove {tkr}", key=f"rm_{tkr}"):
                        del st.session_state.alerts[tkr]
                        st.rerun()
            else:
                st.markdown('<div style="color:#334155;font-size:13px;padding:24px 0;">'
                            'No active alerts — configure one on the left.</div>',
                            unsafe_allow_html=True)

    # ══════════════════════════════════════
    #  DEEP DIVE
    # ══════════════════════════════════════
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    with st.sidebar:
        ticker_choice = st.selectbox("Select asset", all_tickers, label_visibility="collapsed")

    ticker_df = full_df[full_df['ticker'] == ticker_choice].copy()

    if not ticker_df.empty:
        latest   = ticker_df.iloc[-1]
        score    = latest['sentiment_score']
        color    = get_color(score)
        mood, bg_c, bg_dark = mood_label(score)
        conf_pct = latest['confidence'] * 100
        primary_kw = safe_keyword(latest.get('top_keywords'))
        raw_kw   = latest.get('top_keywords', '')
        other_kws = (
            ', '.join(k.strip() for k in str(raw_kw).split(',')[1:3])
            if not pd.isna(raw_kw) else ''
        )

        section_label(f"Deep dive · {ticker_choice}")

        # Hero card
        st.markdown(
            f'<div style="background:#0d1117;border:1px solid #1e2733;border-radius:14px;'
            f'padding:24px 28px;margin-bottom:16px;position:relative;overflow:hidden;">'
            f'<div style="position:absolute;top:0;left:0;width:3px;height:100%;'
            f'background:{color};border-radius:2px 0 0 2px;"></div>'
            f'<div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;">'
            f'<div><div style="font-size:11px;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;'
            f'color:#334155;margin-bottom:6px;">Selected asset</div>'
            f'<div style="font-size:28px;font-weight:600;color:#f1f5f9;letter-spacing:-0.02em;line-height:1;">'
            f'{ticker_choice}</div></div>'
            f'<div style="background:{bg_dark};border:1px solid {color}33;border-radius:8px;padding:8px 14px;text-align:right;">'
            f'<div style="font-size:11px;color:{color}99;margin-bottom:3px;letter-spacing:0.05em;">MARKET MOOD</div>'
            f'<div style="font-size:13px;font-weight:500;color:{color};">{mood}</div>'
            f'</div></div>'
            f'{sentiment_bar_html(score, color)}</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Spot Price",       f"${latest['price']:.2f}")
        c2.metric("AI Confidence",    f"{conf_pct:.1f}%")
        c3.metric("Primary Catalyst", primary_kw)

        if other_kws:
            st.markdown(
                f'<div style="font-size:11px;color:#334155;margin-top:-4px;margin-bottom:8px;">'
                f'Also tracking: <span style="color:#475569;">{other_kws}</span></div>',
                unsafe_allow_html=True,
            )

        # Dual-axis Plotly chart (price + sentiment)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        section_label(f"Price & sentiment · {ticker_choice}")

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=ticker_df['timestamp'], y=ticker_df['price'],
            mode="lines", name="Price",
            line=dict(color=color, width=2),
            fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)",
            yaxis="y1",
            hovertemplate="$%{y:.2f}<extra>Price</extra>",
        ))
        fig2.add_trace(go.Scatter(
            x=ticker_df['timestamp'], y=ticker_df['sentiment_score'],
            mode="lines", name="Sentiment",
            line=dict(color="#38bdf8", width=1.5, dash="dot"),
            yaxis="y2",
            hovertemplate="%{y:+.3f}<extra>Sentiment</extra>",
        ))
        fig2.update_layout(
            **PLOTLY_BASE, height=240,
            xaxis=dict(showgrid=False, zeroline=False, color="#334155"),
            yaxis=dict(showgrid=True, gridcolor="#1e2733", zeroline=False,
                       color="#334155", tickformat="$,.0f", side="left"),
            yaxis2=dict(showgrid=False, zeroline=True, zerolinecolor="#1e2733",
                        color="#38bdf8", overlaying="y", side="right",
                        tickformat="+.2f", range=[-0.6, 0.6]),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11, color="#64748b"),
                        bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error("Database connection failed")
    st.exception(e)


# ─────────────────────────────────────────────
#  METHODOLOGY
# ─────────────────────────────────────────────
st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
section_label("System methodology")

with st.expander("How the scores work", expanded=False):
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("""
**Sentiment Intensity Index** — range −1.0 to +1.0

| Score | Signal |
|-------|--------|
| 0.25+ | High conviction catalyst |
| 0.05 – 0.24 | Positive momentum |
| −0.05 – 0.05 | Neutral / noisy |
| Below −0.25 | Significant headwinds |
        """)
    with col2:
        st.markdown("""
**AI Confidence Score** — the trust metric

1. **News volume** (40%) — more articles → higher trust
2. **Keyword match** (30%) — specific 2026 catalysts detected
3. **Trend alignment** (30%) — price action matches sentiment
4. **Volatility penalty** — noisy stocks are penalized
        """)
    st.info("**Golden Cross:** Sentiment > 0.25 *and* Confidence > 60% is the strongest signal.")

# ─────────────────────────────────────────────
#  MARKET CONTEXT
# ─────────────────────────────────────────────
st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
_month_label = datetime.datetime.now().strftime("%B %Y")
section_label(f"Market context · {_month_label}")

tab_logic, tab_cats = st.tabs(["Scoring logic", "Active catalysts"])

with tab_logic:
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("""
**Reading the bar** — centered at 0.0
- **Right / green** → bullish news dominates; +0.25 = high conviction
- **Left / red** → bearish news dominates

**Confidence weights**
1. News volume (40%)
2. Keyword relevance (30%)
3. Price–sentiment alignment (30%)
4. Volatility penalty
        """)
    with col_b:
        st.markdown("""
**When to act**

| Sentiment | Confidence | Read |
|-----------|------------|------|
| High | High | Strong signal |
| High | Low | Flash in the pan |
| Low | High | Watch for reversal |
| Low | Low | Ignore |
        """)

with tab_cats:
    # Built entirely from live DB data — no hardcoded values
    if 'latest_all' in dir():
        cat_df = (
            latest_all[['ticker', 'top_keywords', 'sentiment_score', 'confidence']]
            .copy()
            .sort_values('confidence', ascending=False)
        )
        cat_df['Primary Catalyst'] = cat_df['top_keywords'].apply(safe_keyword)
        cat_df['Confidence']       = (cat_df['confidence'] * 100).apply(lambda x: f"{x:.0f}%")
        cat_df['Sentiment']        = cat_df['sentiment_score'].apply(lambda x: f"{x:+.3f}")
        st.dataframe(
            cat_df[['ticker', 'Primary Catalyst', 'Sentiment', 'Confidence']],
            column_config={
                "ticker":           st.column_config.TextColumn("Ticker"),
                "Primary Catalyst": st.column_config.TextColumn("Top Keyword"),
                "Sentiment":        st.column_config.TextColumn("Sentiment"),
                "Confidence":       st.column_config.TextColumn("Confidence"),
            },
            hide_index=True,
            use_container_width=True,
        )
        # Highlight the highest-confidence ticker dynamically
        top = cat_df.iloc[0]
        top_kw = top['Primary Catalyst']
        top_ticker = top['ticker']
        st.info(f"Highest confidence signal: **{top_ticker}** — top keyword **{top_kw}** · {top['Confidence']} confidence")
    else:
        st.warning("Load the dashboard first to see live catalyst data.")