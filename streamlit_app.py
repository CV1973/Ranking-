# ============================================
# AI Infrastructure Ranking v7.37 KISS FINAL
# 6 KPIs + Strategic | v7.36 Engine - 4 Punkte KISS
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import io
import warnings
import requests
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Infrastructure Ranking v7.37", layout="wide")
VERSION = "v7.37"
AI_CYCLE_ASSUMPTION = "INTAKT BIS Q4 2027"

DEFAULTS = {
    "aktien_liste": [],
    "datenbank": {},
    "modus": "sammeln",
    "abfrage_queue": [],
    "version_loaded": ""
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if st.session_state.version_loaded!= VERSION:
    for key, val in DEFAULTS.items():
        st.session_state[key] = val
    st.session_state.version_loaded = VERSION

STOCK_UNIVERSE = [
{"ticker":"NVDA", "name":"Nvidia", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"AMD", "name":"AMD", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"AVGO", "name":"Broadcom", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"MRVL", "name":"Marvell", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"ARM", "name":"Arm Holdings", "country":"UK", "flag":"🇬🇧", "region":"Europe", "segment":"AI Compute", "index":"NASDAQ"},
{"ticker":"INTC", "name":"Intel", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"Dow Jones"},
{"ticker":"MU", "name":"Micron", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"000660.KS", "name":"SK Hynix", "country":"South Korea", "flag":"🇰🇷", "region":"Asia", "segment":"Memory / HBM", "index":"KOSPI"},
{"ticker":"005930.KS", "name":"Samsung Electronics", "country":"South Korea", "flag":"🇰🇷", "region":"Asia", "segment":"Memory / HBM", "index":"KOSPI"},
{"ticker":"WDC", "name":"Western Digital", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"STX", "name":"Seagate", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"4449.T", "name":"Kioxia", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Memory / HBM", "index":"TSE Prime"},
{"ticker":"ASML", "name":"ASML", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"AMAT", "name":"Applied Materials", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"LRCX", "name":"Lam Research", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"KLAC", "name":"KLA", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"8035.T", "name":"Tokyo Electron", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Semi Equipment", "index":"Nikkei 225"},
{"ticker":"ASMI.AS", "name":"ASM International", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"VATN.SW", "name":"VAT Group", "country":"Switzerland", "flag":"🇨🇭", "region":"Europe", "segment":"Semi Equipment", "index":"SMI"},
{"ticker":"BE.AS", "name":"Besi", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"6857.T", "name":"Advantest", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Semi Equipment", "index":"Nikkei 225"},
{"ticker":"TER", "name":"Teradyne", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"TSM", "name":"TSMC", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Foundry", "index":"Taiwan Weighted"},
{"ticker":"GFS", "name":"GlobalFoundries", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Foundry", "index":"NASDAQ 100"},
{"ticker":"2303.TW", "name":"UMC", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Foundry", "index":"Taiwan Weighted"},
{"ticker":"IFNNY", "name":"Infineon ADR", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Automotive Semiconductor / Power Semiconductor", "index":"DAX"},
{"ticker":"ANET", "name":"Arista Networks", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"CRED", "name":"Credo", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ"},
{"ticker":"COHR", "name":"Coherent", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"LITE", "name":"Lumentum", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"6967.T", "name":"Fujikura", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Networking / Optical", "index":"Nikkei 225"},
{"ticker":"CSCO", "name":"Cisco", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"Dow Jones"},
{"ticker":"NOK", "name":"Nokia", "country":"Finland", "flag":"🇫🇮", "region":"Europe", "segment":"Networking / Optical", "index":"OMX Helsinki"},
{"ticker":"DELL", "name":"Dell", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Server / DC Hardware", "index":"S&P 500"},
{"ticker":"SMCI", "name":"Super Micro Computer", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Server / DC Hardware", "index":"NASDAQ 100"},
{"ticker":"2353.TW", "name":"Quanta Computer", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Server / DC Hardware", "index":"Taiwan Weighted"},
{"ticker":"2392.TW", "name":"Wiwynn", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Server / DC Hardware", "index":"Taiwan Weighted"},
{"ticker":"SCHN.PA", "name":"Schneider Electric", "country":"France", "flag":"🇫🇷", "region":"Europe", "segment":"Power / Cooling", "index":"CAC 40"},
{"ticker":"ETN", "name":"Eaton", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"VRT", "name":"Vertiv", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"SIE.DE", "name":"Siemens", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Power / Cooling", "index":"DAX"},
{"ticker":"ENR.DE", "name":"Siemens Energy", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Power / Cooling", "index":"MDAX"},
{"ticker":"ABBN.SW", "name":"ABB", "country":"Switzerland", "flag":"🇨🇭", "region":"Europe", "segment":"Power / Cooling", "index":"SMI"},
{"ticker":"BE", "name":"Bloom Energy", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"NASDAQ"},
{"ticker":"GEV", "name":"GE Vernova", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"CEG", "name":"Constellation Energy", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"TXN", "name":"Texas Instruments", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"NASDAQ 100"},
{"ticker":"MSFT", "name":"Microsoft", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"AMZN", "name":"Amazon", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"GOOGL", "name":"Alphabet", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"META", "name":"Meta", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"ORCL", "name":"Oracle", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"NOW", "name":"ServiceNow", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"EQIX", "name":"Equinix", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"DLR", "name":"Digital Realty", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"S&P 500"},
{"ticker":"CCJ", "name":"Cameco", "country":"Canada", "flag":"🇨🇦", "region":"North America", "segment":"Nuclear Energy Supply", "index":"NYSE"},
{"ticker":"BWXT", "name":"BWX Technologies", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Nuclear Technology", "index":"NYSE"},
{"ticker":"8306.T", "name":"MUFG", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"AI Infrastructure Financing", "index":"Nikkei 225"},
{"ticker":"ANSS", "name":"Ansys", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Infrastructure Software", "index":"NASDAQ 100"},
{"ticker":"PLTR", "name":"Palantir", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Infrastructure Software", "index":"NASDAQ 100"},
]

if len(st.session_state.aktien_liste) == 0:
    st.session_state.aktien_liste = [s["ticker"] for s in STOCK_UNIVERSE]

# 3. NAMEN ENTFERNT

SEGMENT_SCORE = {
    "AI Compute": 90, "Memory / HBM": 88, "Semi Equipment": 85, "Foundry": 85,
    "Networking / Optical": 80, "Server / DC Hardware": 82, "Power / Cooling": 78,
    "Cloud / AI Platform": 85, "Automotive Semiconductor / Power Semiconductor": 78,
    "Nuclear Energy Supply": 70, "Nuclear Technology": 70, "AI Infrastructure Financing": 60,
    "AI Infrastructure Software": 83
}

PFLICHT_KPIS = [
    "Forward_KGV","EV_EBITDA","Umsatz_Wachstum","Bruttomarge",
    "Operating_Margin","FCF_Marge"
]

KPI_LABELS = {
    "Forward_KGV":"Forward KGV","EV_EBITDA":"EV/EBITDA","Umsatz_Wachstum":"Umsatzwachstum",
    "Bruttomarge":"Bruttomarge","Operating_Margin":"Operating Margin",
    "FCF_Marge":"FCF Marge","Strategic_Score":"Strategic Score", "Aktueller_Kurs":"Aktueller Kurs"
}

WEIGHTS = {
    'Forward_KGV':0.20, 'EV_EBITDA':0.15, 'Umsatz_Wachstum':0.15,
    'Bruttomarge':0.15, 'Operating_Margin':0.15, 'FCF_Marge':0.20,
    'Strategic_Score':0.10
}

@st.cache_data(ttl=3600)
def get_fear_greed():
    try:
        url="https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10)
        return r.json()["fear_and_greed"]["score"]
    except: return np.nan

def safe_get(info, key):
    try: value = info.get(key); return np.nan if value is None else value
    except: return np.nan

def parse_number(text):
    if text is None: return np.nan
    text = str(text).strip().replace(",", ".")
    try: return float(text)
    except: return np.nan

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        meta = next((s for s in STOCK_UNIVERSE if s["ticker"]==ticker), {"ticker":ticker,"name":ticker})
        st.session_state.datenbank[ticker] = {
            "daten":{"Ticker":ticker, **meta},
            "audit":{},
            "status":"neu"
        }

def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={"Wert":value,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_laden(ticker):
    try:
        time.sleep(0.8)
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        if not info: return None

        price = safe_get(info,"currentPrice")
        if pd.isna(price): price = safe_get(info,"regularMarketPrice")
        if pd.isna(price): price = safe_get(info,"previousClose")
        currency = safe_get(info, "currency")

        forward_kgv = safe_get(info, "forwardPE")
        ev_ebitda = safe_get(info, "enterpriseToEbitda")
        umsatz_wachstum = safe_get(info, "revenueGrowth")
        brutto = safe_get(info, "grossMargins")
        op_marge = safe_get(info, "operatingMargins")

        # 1. PERFORMANCE_52W ENTFERNT
        fcf = safe_get(info,"freeCashflow")
        revenue = safe_get(info,"totalRevenue")
        if not pd.isna(fcf) and not pd.isna(revenue) and revenue!= 0:
            fcf_marge = fcf / revenue
        else:
            fcf_marge = np.nan

        # 2. KEIN _info _financials mehr
        return {
            "Aktueller_Kurs": price, "Waehrung": currency,
            "Forward_KGV":forward_kgv,"EV_EBITDA":ev_ebitda,"Umsatz_Wachstum":umsatz_wachstum,
            "Bruttomarge":brutto,"Operating_Margin":op_marge,"FCF_Marge":fcf_marge
        }
    except: return None

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    fehlend = [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]
    return fehlend

def baue_abfrage_queue():
    queue = []
    for ticker in st.session_state.aktien_liste:
        init_ticker(ticker)
        obj = st.session_state.datenbank[ticker]
        if obj["status"] == "neu":
            daten = yahoo_laden(ticker)
            if daten:
                for kpi, wert in daten.items():
                    if not pd.isna(wert):
                        save_kpi(ticker, kpi, wert, "Yahoo")
                segment = obj["daten"]["segment"]
                save_kpi(ticker, "Strategic_Score", SEGMENT_SCORE.get(segment, 70), "Segment")
            obj["status"] = "geladen"
        fehlend = fehlende_kpis(ticker)
        for kpi in fehlend:
            queue.append((ticker, kpi))
    st.session_state.abfrage_queue = queue

def normalize(df, col, higher_better=True):
    s = pd.to_numeric(df[col], errors="coerce")
    valid = s.dropna()
    if len(valid) < 2: return pd.Series(0.5, index=s.index)
    x = s.copy()
    if not higher_better: x = -x
    rank = x.rank(pct=True)
    return rank.fillna(0.5)

def calculate_scores(df):
    for col, w in WEIGHTS.items():
        if col!= 'Strategic_Score':
            lower_better = col in ['Forward_KGV','EV_EBITDA']
            df[f'Norm_{col}'] = normalize(df, col, not lower_better) * w

    finanz_gewichte = {k:v for k,v in WEIGHTS.items() if k!= 'Strategic_Score'}
    df['Finanzscore'] = df[[f'Norm_{c}' for c in finanz_gewichte.keys()]].sum(axis=1) * 100

    df['Datenpunkte'] = df[PFLICHT_KPIS].notna().sum(axis=1)
    df['Datenqualität'] = df['Datenpunkte'] / len(PFLICHT_KPIS)

    # 4. STRATEGISCHER_AUFSCHLAG ENTFERNT
    df['Gesamtscore_Roh'] = df['Finanzscore'] * 0.9 + df['Strategic_Score'] * 0.1
    df['Gesamtscore'] = (df['Gesamtscore_Roh'] * (0.3 + 0.7 * df['Datenqualität'])).round(1)

    df = df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    df["Rang"] = df.index + 1
    return df
    def get_investment_rating(score):
    if score >= 80: return "Strong Buy"
    elif score >= 65: return "Buy"
    elif score >= 45: return "Hold"
    else: return "Sell"

def screen_sammeln():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    fear_greed = get_fear_greed()
    st.info(f"**Investment Thesis:** AI Infrastructure Cycle: {AI_CYCLE_ASSUMPTION} | Fear&Greed: {fear_greed:.0f}")
    st.subheader(f"Aktuelles Universum: {len(st.session_state.aktien_liste)} Werte")
    df_meta = pd.DataFrame([s for s in STOCK_UNIVERSE if s["ticker"] in st.session_state.aktien_liste])
    st.dataframe(df_meta, use_container_width=True, hide_index=True)
    st.divider()
    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Lade Yahoo Daten..."):
            baue_abfrage_queue()
        st.session_state.modus = "uebersicht"; st.rerun()

def screen_uebersicht():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    st.subheader("2. Daten-Übersicht")
    st.write(f"Fehlende KPIs: {len(st.session_state.abfrage_queue)}")
    if st.button("▶️ Zum Ranking", type="primary"): st.session_state.modus = "ranking"; st.rerun()
    if st.button("⬅️ Zurück"): st.session_state.modus = "sammeln"; st.rerun()

def screen_abfrage():
    if len(st.session_state.abfrage_queue) == 0: st.session_state.modus = "ranking"; st.rerun(); return
    ticker, kpi = st.session_state.abfrage_queue[0]
    st.error(f"Fehlender Wert: {ticker} - {KPI_LABELS[kpi]}")
    eingabe = st.text_input("Wert eingeben")
    col1,col2 = st.columns(2)
    with col1:
        if st.button("💾 Speichern"):
            wert = parse_number(eingabe)
            if pd.isna(wert): st.error("Keine gültige Zahl"); return
            save_kpi(ticker, kpi, wert, "Manuell")
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col2:
        if st.button("⏭️ Überspringen"):
            save_kpi(ticker, kpi, np.nan, "Übersprungen")
            st.session_state.abfrage_queue.pop(0); st.rerun()

def screen_ranking():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    liste=[]
    for ticker in st.session_state.aktien_liste:
        liste.append(st.session_state.datenbank[ticker]["daten"])
    df=pd.DataFrame(liste)
    if len(df)<2:
        st.error("Zu wenige Aktien")
        if st.button("⬅️ Zurück zur Liste"): st.session_state.modus = "sammeln"; st.rerun()
        return

    df = calculate_scores(df)
    df["Investment_Rating"] = df["Gesamtscore"].apply(get_investment_rating)

    st.subheader("Ranking v7.37 KISS")
    # 4. STRATEGISCHER_AUFSCHLAG AUS ANZEIGE ENTFERNT
    show_cols = ['Rang','Ticker','name','flag','country','region','segment','index',
                 'Aktueller_Kurs','Waehrung','Forward_KGV','EV_EBITDA','Umsatz_Wachstum',
                 'Bruttomarge','Operating_Margin','FCF_Marge',
                 'Strategic_Score','Finanzscore','Datenqualität','Gesamtscore','Investment_Rating']
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(df[show_cols].round(2), use_container_width=True, hide_index=True)

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranking_v7.37")
        pd.DataFrame(STOCK_UNIVERSE).to_excel(writer, index=False, sheet_name="Universum")
        df[['Ticker','name','Datenpunkte','Datenqualität']].to_excel(writer, index=False, sheet_name="Datenqualität")
        audit_rows = []
        for ticker, obj in st.session_state.datenbank.items():
            for kpi, audit in obj["audit"].items():
                audit_rows.append({"Ticker":ticker, "KPI":kpi, **audit})
        pd.DataFrame(audit_rows).to_excel(writer, index=False, sheet_name="Audit")

    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v7.37_{datetime.now().strftime('%Y-%m-%d')}.xlsx", use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 CSV herunterladen", csv, file_name=f"AI_Ranking_v7.37_{datetime.now().strftime('%Y-%m-%d')}.csv", use_container_width=True)
    if st.button("⬅️ Zurück zur Liste"): st.session_state.modus = "sammeln"; st.rerun()

if st.session_state.modus == "sammeln": screen_sammeln()
elif st.session_state.modus == "uebersicht": screen_uebersicht()
elif st.session_state.modus == "abfrage": screen_abfrage()
elif st.session_state.modus == "ranking": screen_ranking()
