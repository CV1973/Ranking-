import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Ranking US-ONLY v7.45.29", layout="wide")
st.title("🚀 AI Infrastructure Ranking v7.45.29-US ONLY")
st.markdown("**37 US Listings + ADRs aus ehemals 60 Werten** | Datenquelle: Yahoo Finance")

# === 1. DATENMODELL: ALLE 37 WERTE MIT KOMMENTAR ===
STOCKS = [
# AI Compute + Big Tech + Storage
{"t":"NVDA","name":"Nvidia","typ":"Empfaenger","sektor":"Chips","kommentar":"AI GPU Leader, DGX, H100"},
{"t":"AMD","name":"AMD","typ":"Empfaenger","sektor":"Chips","kommentar":"CPU + GPU, MI300, Konkurrenz zu NVDA"},
{"t":"AVGO","name":"Broadcom","typ":"Empfaenger","sektor":"Chips","kommentar":"ASIC + Networking, VMware"},
{"t":"INTC","name":"Intel","typ":"Empfaenger","sektor":"Chips","kommentar":"Foundry Turnaround, Gaudi"},
{"t":"QCOM","name":"Qualcomm","typ":"Empfaenger","sektor":"Chips","kommentar":"Mobile + AI Edge, NPU"},
{"t":"MU","name":"Micron","typ":"Empfaenger","sektor":"Memory","kommentar":"DRAM + HBM für AI"},
{"t":"SNDK","name":"Sandisk","typ":"Empfaenger","sektor":"Storage","kommentar":"NAND Flash, seit 02/2024 eigenständig"},
{"t":"WDC","name":"Western Digital","typ":"Empfaenger","sektor":"Storage","kommentar":"HDD + NAND, Cloud Storage"},
{"t":"MSFT","name":"Microsoft","typ":"Spender","sektor":"Hyperscaler","kommentar":"Azure + OpenAI, 10Mrd OpenAI"},
{"t":"GOOGL","name":"Alphabet","typ":"Spender","sektor":"Hyperscaler","kommentar":"GCP + TPU, Gemini"},
{"t":"AMZN","name":"Amazon","typ":"Spender","sektor":"Hyperscaler","kommentar":"AWS + Trainium + Inferentia"},
{"t":"META","name":"Meta","typ":"Spender","sektor":"Hyperscaler","kommentar":"Llama + Infra, massive GPU Käufe"},
{"t":"AAPL","name":"Apple","typ":"Spender","sektor":"Device","kommentar":"On-Device AI, Apple Intelligence"},
{"t":"ORCL","name":"Oracle","typ":"Spender","sektor":"Cloud","kommentar":"OCI + DB, AI Cloud"},
{"t":"IBM","name":"IBM","typ":"Spender","sektor":"Enterprise","kommentar":"Watson + Hybrid Cloud"},
# Semi Equipment
{"t":"ASML","name":"ASML ADR","typ":"Empfaenger","sektor":"Equipment","kommentar":"EUV Monopol, wichtigste Maschine"},
{"t":"AMAT","name":"Applied Materials","typ":"Empfaenger","sektor":"Equipment","kommentar":"Deposition + Etching"},
{"t":"LRCX","name":"Lam Research","typ":"Empfaenger","sektor":"Equipment","kommentar":"Etching + Cleaning"},
{"t":"KLAC","name":"KLA Corp","typ":"Empfaenger","sektor":"Equipment","kommentar":"Inspection + Metrology"},
{"t":"ADI","name":"Analog Devices","typ":"Empfaenger","sektor":"Chips","kommentar":"Analog + Power für DC"},
{"t":"TXN","name":"Texas Instruments","typ":"Empfaenger","sektor":"Chips","kommentar":"Analog + MCU, breites Portfolio"},
{"t":"MCHP","name":"Microchip","typ":"Empfaenger","sektor":"Chips","kommentar":"MCU + Analog, Auto + DC"},
# Foundry + Memory ADR
{"t":"TSM","name":"TSMC ADR","typ":"Empfaenger","sektor":"Foundry","kommentar":"Leading Foundry, fertigt für NVDA/AMD"},
{"t":"SKHYY","name":"SK Hynix ADR","typ":"Empfaenger","sektor":"Memory","kommentar":"HBM Leader, wichtigster NVDA Zulieferer"},
# Server / DC / Networking
{"t":"DELL","name":"Dell","typ":"Empfaenger","sektor":"Server","kommentar":"AI Server, Partnerschaft mit NVDA"},
{"t":"SMCI","name":"Super Micro","typ":"Empfaenger","sektor":"Server","kommentar":"Liquid Cooling, AI Server Boom"},
{"t":"ANET","name":"Arista Networks","typ":"Empfaenger","sektor":"Network","kommentar":"DC Switches, 400G/800G"},
{"t":"CSCO","name":"Cisco","typ":"Empfaenger","sektor":"Network","kommentar":"Networking, AI Pod"},
{"t":"HPQ","name":"HP","typ":"Empfaenger","sektor":"Server","kommentar":"Enterprise Server, Workstations"},
# Power / Cooling / Infrastructure
{"t":"PWR","name":"Quanta Services","typ":"Empfaenger","sektor":"Infrastructure","kommentar":"DC Buildout, Elektriker"},
{"t":"ETN","name":"Eaton","typ":"Empfaenger","sektor":"Power","kommentar":"Power Mgmt, USV, Schaltanlagen"},
{"t":"JCI","name":"Johnson Controls","typ":"Empfaenger","sektor":"Cooling","kommentar":"HVAC + Liquid Cooling für DC"},
# Software / Data / AI
{"t":"ANSS","name":"Ansys","typ":"Neutral","sektor":"Software","kommentar":"Simulation, Chip Design"},
{"t":"SNOW","name":"Snowflake","typ":"Neutral","sektor":"Data","kommentar":"Data Cloud, AI Data Platform"},
{"t":"PLTR","name":"Palantir","typ":"Neutral","sektor":"AI","kommentar":"Gov + Enterprise AI, AIP"},
{"t":"CRWD","name":"CrowdStrike","typ":"Neutral","sektor":"Security","kommentar":"Cybersec, Falcon"},
{"t":"MDB","name":"MongoDB","typ":"Neutral","sektor":"Data","kommentar":"Vector DB, Atlas"},
{"t":"DDOG","name":"Datadog","typ":"Neutral","sektor":"Monitoring","kommentar":"Observability, AI Ops"},
{"t":"NET","name":"Cloudflare","typ":"Neutral","sektor":"CDN","kommentar":"Edge + AI Inference"},
{"t":"PANW","name":"Palo Alto","typ":"Neutral","sektor":"Security","kommentar":"Firewall + AI Sec, Prisma"},
]

# === 2. SCORING KONFIGURATION ===
BIAS = {"Empfaenger": 10.0, "Spender": -10.0, "Neutral": 0.0}
WEIGHTS = {
    "Empfaenger": {'KGV':0.10, 'EV':0.05, 'Wachstum':0.30, 'Brutto':0.10, 'OpM':0.30, 'FCF':0.05}, # Wachstum + Marge wichtig
    "Spender": {'KGV':0.15, 'EV':0.10, 'Wachstum':0.05, 'Brutto':0.15, 'OpM':0.30, 'FCF':0.25}, # FCF wichtig für CAPEX
    "Neutral": {'KGV':0.15, 'EV':0.15, 'Wachstum':0.15, 'Brutto':0.15, 'OpM':0.20, 'FCF':0.20} # Ausgewogen
}
KPIS = ['KGV','EV','Wachstum','Brutto','OpM','FCF','MarketCap']
INVERT_KPIS = ['KGV','EV','MarketCap'] # Niedriger ist besser

# === 3. DATENLADEN MIT CACHING ===
@st.cache_data(ttl=1800, show_spinner="Lade Daten von Yahoo Finance... Dauert ~30s")
def load_all_data(stock_list):
    results = []
    for idx, s in enumerate(stock_list):
        try:
            tk = yf.Ticker(s['t'])
            time.sleep(0.7) # Wichtig gegen Yahoo Rate Limit Ban
            i = tk.info
            revenue = i.get("totalRevenue")
            fcf = i.get("freeCashflow")
            results.append({
                "Ticker":s['t'], "Name":s['name'], "Typ":s['typ'], "Sektor":s['sektor'], "Kommentar":s['kommentar'],
                'Kurs': i.get("currentPrice") or i.get("regularMarketPrice"),
                'KGV': i.get("forwardPE"),
                'EV': i.get("enterpriseToEbitda"),
                'Wachstum': i.get("revenueGrowth"),
                'Brutto': i.get("grossMargins"),
                'OpM': i.get("operatingMargins"),
                'FCF': fcf/revenue if revenue and fcf and revenue > 0 else np.nan,
                'MarketCap': i.get("marketCap")
            })
        except Exception as e:
            st.warning(f"Fehler bei {s['t']}: {e}")
            results.append({
                "Ticker":s['t'], "Name":s['name'], "Typ":s['typ'], "Sektor":s['sektor'], "Kommentar":s['kommentar'],
                'Kurs':np.nan, 'KGV':np.nan, 'EV':np.nan, 'Wachstum':np.nan, 'Brutto':np.nan, 'OpM':np.nan, 'FCF':np.nan, 'MarketCap':np.nan
            })
    return pd.DataFrame(results)

def norm_series(s, invert=False):
    """MinMax Normalisierung 0-1. invert=True = niedriger ist besser"""
    x = pd.to_numeric(s, errors="coerce")
    if invert: x = -x
    valid = x.dropna()
    if len(valid) <= 1: return pd.Series(np.nan, index=x.index)
    return (x - x.min()) / (x.max() - x.min() + 1e-9)

# === ENDE TEIL 1 - KOPIEREN UND NEUE WHATSAPP NACHRICHT STARTEN ===
# === ANFANG TEIL 2 - HINTER TEIL 1 EINFÜGEN ===

# === 4. UI UND FILTER ===
st.sidebar.header("⚙️ Einstellungen")
typ_filter = st.sidebar.multiselect("Filter nach Typ:", ["Empfaenger","Spender","Neutral"], default=["Empfaenger","Spender","Neutral"])
sektor_filter = st.sidebar.multiselect("Filter nach Sektor:", sorted(list(set([s['sektor'] for s in STOCKS]))), default=sorted(list(set([s['sektor'] for s in STOCKS]))))

col1, col2, col3 = st.columns(3)
with col1: st.metric("Gesamt Werte", len(STOCKS))
with col2: st.metric("Empfaenger", len([s for s in STOCKS if s['typ']=='Empfaenger']))
with col3: st.metric("Spender", len([s for s in STOCKS if s['typ']=='Spender']))

if st.button("🚀 Ranking berechnen", type="primary", use_container_width=True):
    df = load_all_data(STOCKS)
    df = df[df['Typ'].isin(typ_filter)]
    df = df[df['Sektor'].isin(sektor_filter)].copy()

    df['Bias'] = df['Typ'].map(BIAS)
    df['Datenqualität'] = df[KPIS].notna().sum(axis=1) / len(KPIS)

    # Normalisierung pro KPI
    for k in KPIS:
        df[f'N_{k}'] = norm_series(df[k], invert=k in INVERT_KPIS)

    # Gewichteter RohScore
    df['RohScore'] = 0.0
    for idx, row in df.iterrows():
        w = WEIGHTS[row['Typ']]
        score = 0
        for k in ['KGV','EV','Wachstum','Brutto','OpM','FCF']:
            val = row[f'N_{k}']
            if not pd.isna(val): score += val * w[k]
        df.at[idx,'RohScore'] = score * 100

    # Gesamt mit Datenqualität und Bias
    df['GesamtScore'] = (df['RohScore'] * 0.9 * (0.3 + 0.7 * df['Datenqualität']) + df['Bias']).round(2)
    df = df.sort_values('GesamtScore', ascending=False).reset_index(drop=True)
    df['Rang'] = df.index + 1

    st.success(f"Fertig! {len(df)} Unternehmen gerankt um {datetime.now().strftime('%H:%M:%S')}")

    # === 5. AUSGABE TABS ===
    tab1, tab2, tab3 = st.tabs(["📊 Ranking Tabelle", "📈 Top 10 Chart", "📉 KPI Analyse"])

    with tab1:
        cols = ['Rang','Ticker','Name','Typ','Sektor','GesamtScore','RohScore','Bias','Datenqualität','Kurs','MarketCap'] + KPIS + ['Kommentar']
        st.dataframe(
            df[cols].style.format({
                'Kurs':'${:.2f}', 'GesamtScore':'{:.2f}', 'RohScore':'{:.2f}', 'Bias':'{:+.1f}', 'Datenqualität':'{:.0%}',
                'KGV':'{:.1f}', 'EV':'{:.1f}', 'MarketCap':'${:,.0f}',
                'Wachstum':'{:.1%}', 'Brutto':'{:.1%}', 'OpM':'{:.1%}', 'FCF':'{:.1%}'
            }).background_gradient(subset=['GesamtScore'], cmap='RdYlGn'),
            use_container_width=True, height=700
        )

    with tab2:
        top10 = df.head(10)
        st.bar_chart(top10.set_index('Ticker')['GesamtScore'], height=400)

    with tab3:
        st.write("Korrelation der KPIs")
        st.dataframe(df[KPIS].corr().style.background_gradient(cmap='coolwarm'))

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV Download", csv, f"ai_ranking_us_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)

else:
    st.info(f"{len(STOCKS)} US/ADR Werte sind konfiguriert. Enthält NVDA, MU, SNDK, TSM, ASML.")
    st.warning("Klick auf 'Ranking berechnen'. Lädt ca 30 Sekunden wegen Yahoo Rate Limit.")
