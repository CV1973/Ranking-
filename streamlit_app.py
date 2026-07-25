import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Ranking US-ONLY v7.45.27", layout="wide")
st.title("🚀 AI Infrastructure Ranking v7.45.27-US ONLY")
st.caption("37 US Listings + ADRs aus ehemals 60 Werten | Daten: Yahoo Finance")

# === ALLE 37 US/ADR WERTE ===
STOCKS = [
# 1. AI Compute + Big Tech + Storage
{"t":"NVDA","name":"Nvidia","typ":"Empfaenger","sektor":"Chips"},
{"t":"AMD","name":"AMD","typ":"Empfaenger","sektor":"Chips"},
{"t":"AVGO","name":"Broadcom","typ":"Empfaenger","sektor":"Chips"},
{"t":"INTC","name":"Intel","typ":"Empfaenger","sektor":"Chips"},
{"t":"QCOM","name":"Qualcomm","typ":"Empfaenger","sektor":"Chips"},
{"t":"MU","name":"Micron","typ":"Empfaenger","sektor":"Memory"},
{"t":"SNDK","name":"Sandisk","typ":"Empfaenger","sektor":"Storage"},
{"t":"WDC","name":"Western Digital","typ":"Empfaenger","sektor":"Storage"},
{"t":"MSFT","name":"Microsoft","typ":"Spender","sektor":"Hyperscaler"},
{"t":"GOOGL","name":"Alphabet","typ":"Spender","sektor":"Hyperscaler"},
{"t":"AMZN","name":"Amazon","typ":"Spender","sektor":"Hyperscaler"},
{"t":"META","name":"Meta","typ":"Spender","sektor":"Hyperscaler"},
{"t":"AAPL","name":"Apple","typ":"Spender","sektor":"Device"},
{"t":"ORCL","name":"Oracle","typ":"Spender","sektor":"Cloud"},
{"t":"IBM","name":"IBM","typ":"Spender","sektor":"Enterprise"},
# 2. Semi Equipment
{"t":"ASML","name":"ASML ADR","typ":"Empfaenger","sektor":"Equipment"},
{"t":"AMAT","name":"Applied Materials","typ":"Empfaenger","sektor":"Equipment"},
{"t":"LRCX","name":"Lam Research","typ":"Empfaenger","sektor":"Equipment"},
{"t":"KLAC","name":"KLA Corp","typ":"Empfaenger","sektor":"Equipment"},
{"t":"ADI","name":"Analog Devices","typ":"Empfaenger","sektor":"Chips"},
{"t":"TXN","name":"Texas Instruments","typ":"Empfaenger","sektor":"Chips"},
{"t":"MCHP","name":"Microchip","typ":"Empfaenger","sektor":"Chips"},
# 3. Foundry + Memory ADR
{"t":"TSM","name":"TSMC ADR","typ":"Empfaenger","sektor":"Foundry"},
{"t":"SKHYY","name":"SK Hynix ADR","typ":"Empfaenger","sektor":"Memory"},
# 4. Server / DC / Networking
{"t":"DELL","name":"Dell","typ":"Empfaenger","sektor":"Server"},
{"t":"SMCI","name":"Super Micro","typ":"Empfaenger","sektor":"Server"},
{"t":"ANET","name":"Arista Networks","typ":"Empfaenger","sektor":"Network"},
{"t":"CSCO","name":"Cisco","typ":"Empfaenger","sektor":"Network"},
{"t":"HPQ","name":"HP","typ":"Empfaenger","sektor":"Server"},
# 5. Power / Cooling / Infrastructure
{"t":"PWR","name":"Quanta Services","typ":"Empfaenger","sektor":"Infrastructure"},
{"t":"ETN","name":"Eaton","typ":"Empfaenger","sektor":"Power"},
{"t":"JCI","name":"Johnson Controls","typ":"Empfaenger","sektor":"Cooling"},
# 6. Software / Data / AI
{"t":"ANSS","name":"Ansys","typ":"Neutral","sektor":"Software"},
{"t":"SNOW","name":"Snowflake","typ":"Neutral","sektor":"Data"},
{"t":"PLTR","name":"Palantir","typ":"Neutral","sektor":"AI"},
{"t":"CRWD","name":"CrowdStrike","typ":"Neutral","sektor":"Security"},
{"t":"MDB","name":"MongoDB","typ":"Neutral","sektor":"Data"},
{"t":"DDOG","name":"Datadog","typ":"Neutral","sektor":"Monitoring"},
{"t":"NET","name":"Cloudflare","typ":"Neutral","sektor":"CDN"},
{"t":"PANW","name":"Palo Alto","typ":"Neutral","sektor":"Security"},
]

# === SCORING LOGIK ===
BIAS = {"Empfaenger": 10, "Spender": -10, "Neutral": 0}
WEIGHTS = {
    "Empfaenger": {'KGV':0.10, 'EV':0.05, 'Wachstum':0.30, 'Brutto':0.10, 'OpM':0.30, 'FCF':0.05},
    "Spender": {'KGV':0.15, 'EV':0.10, 'Wachstum':0.05, 'Brutto':0.15, 'OpM':0.30, 'FCF':0.25},
    "Neutral": {'KGV':0.15, 'EV':0.15, 'Wachstum':0.15, 'Brutto':0.15, 'OpM':0.20, 'FCF':0.20}
KPIS = ['KGV','EV','Wachstum','Brutto','OpM','FCF','MarketCap']

@st.cache_data(ttl=1800, show_spinner=False)
def load_data(ticker):
    """Lädt KPIs von Yahoo Finance"""
    try:
        tk = yf.Ticker(ticker)
        time.sleep(0.8) # Gegen Rate Limit
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
            'FCF': fcf/revenue if revenue and fcf and revenue > 0 else np.nan,
            'MarketCap': i.get("marketCap")
        }
    except:
        return {k:np.nan for k in ['Kurs']+KPIS}

def norm(s, invert=False):
    """Normalisiert 0-1. invert=True = niedriger ist besser"""
    x = pd.to_numeric(s, errors="coerce")
    if invert: x = -x
    valid = x.dropna()
    if len(valid) <= 1: return pd.Series(np.nan, index=x.index)
    return x.rank(pct=True, method="average")

# === UI ===
st.sidebar.header("Filter")
typ_filter = st.sidebar.multiselect("Typ", ["Empfaenger","Spender","Neutral"], default=["Empfaenger","Spender","Neutral"])

if st.button("✅ Ranking starten", type="primary"):
    data = []
    prog = st.progress(0)
    status = st.empty()

    for idx, s in enumerate(STOCKS):
        status.text(f"Lade {idx+1}/{len(STOCKS)}: {s['t']} - {s['name']}")
        d = load_data(s['t'])
        data.append({"Ticker":s['t'], "Name":s['name'], "Typ":s['typ'], "Sektor":s['sektor'], **d})
        prog.progress((idx+1)/len(STOCKS))

    status.text("Berechne Scores...")
    df = pd.DataFrame(data)
    df = df[df['Typ'].isin(typ_filter)]
    df['Bias'] = df['Typ'].map(BIAS)
    df['Daten'] = df[KPIS].notna().sum(axis=1) / len(KPIS)

    # Normalisierung
    for k in KPIS:
        df[f'N_{k}'] = norm(df[k], invert=k in ['KGV','EV','MarketCap'])

    # Score
    df['Score'] = 0.0
    for idx, row in df.iterrows():
        w = WEIGHTS[row['Typ']]
        score = sum(row[f'N_{k}']*w[k] for k in ['KGV','EV','Wachstum','Brutto','OpM','FCF'] if not pd.isna(row[f'N_{k}']))
        df.at[idx,'Score'] = score * 100

    # Gesamt
    df['Gesamt'] = (df['Score'] * 0.9 * (0.3 + 0.7 * df['Daten']) + df['Bias']).round(1)
    df = df.sort_values('Gesamt', ascending=False).reset_index(drop=True)
    df['Rang'] = df.index + 1

    status.empty()
    st.success(f"✅ Fertig. {len(df)} Werte geladen um {datetime.now().strftime('%H:%M:%S')}")

    # Tabelle
    cols_to_show = ['Rang','Ticker','Name','Typ','Sektor','Gesamt','Bias','Daten','Kurs','MarketCap'] + ['KGV','EV','Wachstum','Brutto','OpM','FCF']
    st.dataframe(
        df[cols_to_show].style.format({
            'Kurs':'${:.2f}', 'Gesamt':'{:.1f}', 'Bias':'{:.0f}', 'Daten':'{:.0%}',
            'KGV':'{:.1f}', 'EV':'{:.1f}', 'MarketCap':'${:,.0f}',
            'Wachstum':'{:.1%}', 'Brutto':'{:.1%}', 'OpM':'{:.1%}', 'FCF':'{:.1%}'
        }).background_gradient(subset=['Gesamt'], cmap='RdYlGn'),
        use_container_width=True, height=650
    )

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV Download", csv, f"ai_ranking_us_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

else:
    st.info(f"{len(STOCKS)} US/ADR Werte bereit. NVDA, MU, SNDK, TSM, ASML enthalten.")
    st.warning("Klick auf 'Ranking starten' um Daten zu laden. Dauert ~30 Sekunden wegen Yahoo Rate Limit.")
