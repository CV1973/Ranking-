import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Ranking US-ONLY v7.45.31", layout="wide")
st.title("AI Infrastructure Ranking v7.45.31-US ONLY")
st.caption("Nur US Listings + ADRs aus ehemals 60 Werten")

# === ALLE 37 US/ADR WERTE ===
STOCKS = [
# AI Compute + Big Tech + Storage
{"t":"NVDA","name":"Nvidia","typ":"Empfaenger"},
{"t":"AMD","name":"AMD","typ":"Empfaenger"},
{"t":"AVGO","name":"Broadcom","typ":"Empfaenger"},
{"t":"INTC","name":"Intel","typ":"Empfaenger"},
{"t":"QCOM","name":"Qualcomm","typ":"Empfaenger"},
{"t":"MU","name":"Micron","typ":"Empfaenger"},
{"t":"SNDK","name":"Sandisk","typ":"Empfaenger"},
{"t":"WDC","name":"Western Digital","typ":"Empfaenger"},
{"t":"MSFT","name":"Microsoft","typ":"Spender"},
{"t":"GOOGL","name":"Alphabet","typ":"Spender"},
{"t":"AMZN","name":"Amazon","typ":"Spender"},
{"t":"META","name":"Meta","typ":"Spender"},
{"t":"AAPL","name":"Apple","typ":"Spender"},
{"t":"ORCL","name":"Oracle","typ":"Spender"},
{"t":"IBM","name":"IBM","typ":"Spender"},
# Semi Equipment
{"t":"ASML","name":"ASML ADR","typ":"Empfaenger"},
{"t":"AMAT","name":"Applied Materials","typ":"Empfaenger"},
{"t":"LRCX","name":"Lam Research","typ":"Empfaenger"},
{"t":"KLAC","name":"KLA Corp","typ":"Empfaenger"},
{"t":"ADI","name":"Analog Devices","typ":"Empfaenger"},
{"t":"TXN","name":"Texas Instruments","typ":"Empfaenger"},
{"t":"MCHP","name":"Microchip","typ":"Empfaenger"},
# Foundry + Memory ADR
{"t":"TSM","name":"TSMC ADR","typ":"Empfaenger"},
{"t":"SKHYY","name":"SK Hynix ADR","typ":"Empfaenger"},
# Server / DC / Networking
{"t":"DELL","name":"Dell","typ":"Empfaenger"},
{"t":"SMCI","name":"Super Micro","typ":"Empfaenger"},
{"t":"ANET","name":"Arista Networks","typ":"Empfaenger"},
{"t":"CSCO","name":"Cisco","typ":"Empfaenger"},
{"t":"HPQ","name":"HP","typ":"Empfaenger"},
# Power / Cooling / Infrastructure
{"t":"PWR","name":"Quanta Services","typ":"Empfaenger"},
{"t":"ETN","name":"Eaton","typ":"Empfaenger"},
{"t":"JCI","name":"Johnson Controls","typ":"Empfaenger"},
# Software / Data / AI
{"t":"ANSS","name":"Ansys","typ":"Neutral"},
{"t":"SNOW","name":"Snowflake","typ":"Neutral"},
{"t":"PLTR","name":"Palantir","typ":"Neutral"},
{"t":"CRWD","name":"CrowdStrike","typ":"Neutral"},
{"t":"MDB","name":"MongoDB","typ":"Neutral"},
{"t":"DDOG","name":"Datadog","typ":"Neutral"},
{"t":"NET","name":"Cloudflare","typ":"Neutral"},
{"t":"PANW","name":"Palo Alto","typ":"Neutral"},
]

BIAS = {"Empfaenger": 10, "Spender": -10, "Neutral": 0}
WEIGHTS = {
    "Empfaenger": {'KGV':0.10, 'EV':0.05, 'Wachstum':0.30, 'Brutto':0.10, 'OpM':0.30, 'FCF':0.05},
    "Spender": {'KGV':0.15, 'EV':0.10, 'Wachstum':0.05, 'Brutto':0.15, 'OpM':0.30, 'FCF':0.25},
    "Neutral": {'KGV':0.15, 'EV':0.15, 'Wachstum':0.15, 'Brutto':0.15, 'OpM':0.20, 'FCF':0.20}
}
KPIS = ['KGV','EV','Wachstum','Brutto','OpM','FCF']

@st.cache_data(ttl=1800)
def load_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        time.sleep(0.8)
        i = tk.info
        revenue = i.get("totalRevenue")
        fcf = i.get("freeCashflow")
        return {
            'Kurs': i.get("currentPrice") or i.get("regularMarketPrice"),
            'KGV': i.get("forwardPE"),
            'EV': i.get("enterpriseToEbitda"),
            'Wachstum': i.get("revenueGrowth"),
            'Brutto': i.get("grossMargins"),
            'OpM': i.get("operatingMargins"),
            'FCF': fcf/revenue if revenue and fcf else np.nan
        }
    except:
        return {k:np.nan for k in ['Kurs']+KPIS}

def norm(s, invert=False):
    x = pd.to_numeric(s, errors="coerce")
    if invert: x = -x
    valid = x.dropna()
    return x.rank(pct=True) if len(valid)>1 else pd.Series(np.nan, index=x.index)

if st.button("✅ Ranking starten", type="primary"):
    data = []
    prog = st.progress(0)
    status = st.empty()

    for idx, s in enumerate(STOCKS):
        status.text(f"Lade {idx+1}/{len(STOCKS)}: {s['t']}")
        d = load_data(s['t'])
        data.append({"Ticker":s['t'], "Name":s['name'], "Typ":s['typ'], **d})
        prog.progress((idx+1)/len(STOCKS))

    df = pd.DataFrame(data)
    df['Bias'] = df['Typ'].map(BIAS)
    df['Daten'] = df[KPIS].notna().sum(axis=1) / len(KPIS)

    for k in KPIS:
        df[f'N_{k}'] = norm(df[k], invert=k in ['KGV','EV'])

    df['Score'] = 0
    for idx, row in df.iterrows():
        w = WEIGHTS[row['Typ']]
        score = 0
        for k in KPIS:
            if not pd.isna(row[f'N_{k}']): score += row[f'N_{k}']*w[k]
        df.at[idx,'Score'] = score*100

    df['Gesamt'] = (df['Score']*0.9 * (0.3 + 0.7*df['Daten']) + df['Bias']).round(1)
    df = df.sort_values('Gesamt', ascending=False).reset_index(drop=True)
    df['Rang'] = df.index + 1

    status.empty()
    st.success(f"Fertig. {len(df)} US/ADR Werte geladen")

    # KEIN background_gradient mehr -> kein matplotlib fehler
    st.dataframe(
        df[['Rang','Ticker','Name','Typ','Gesamt','Bias','Daten'] + KPIS].style.format({
            'Gesamt':'{:.1f}', 'Daten':'{:.0%}', 'KGV':'{:.1f}', 'EV':'{:.1f}',
            'Wachstum':'{:.1%}', 'Brutto':'{:.1%}', 'OpM':'{:.1%}', 'FCF':'{:.1%}'
        }),
        use_container_width=True
    )

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV Download", csv, "ai_ranking_us.csv", "text/csv")
else:
    st.info(f"{len(STOCKS)} US/ADR Werte. NVDA, MU, SNDK enthalten.")
