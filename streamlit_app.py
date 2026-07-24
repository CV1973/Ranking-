# ============================================
# AI Infrastructure Return Ranking v17.2.1
# FINAL: KISS Frozen. Nur Bugfixes
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
from bs4 import BeautifulSoup
import re
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Return Ranking v17.2.1", layout="wide")
VERSION = "v17.2.1"
AI_CYCLE_ASSUMPTION = "INTAKT BIS Q4 2027"

DEFAULTS = {
    "aktien_liste": ["NVDA","000660.KS","005930.KS","TSM","MU","AVGO","ASML","AMD","AMAT","LRCX","KLAC","285A.T","SNDK","MSFT","GOOGL","AMZN"],
    "datenbank": {},
    "modus": "sammeln",
    "abfrage_queue": [],
    "web_vorschlaege": {},
    "version_loaded": ""
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if st.session_state.version_loaded!= VERSION:
    for key, val in DEFAULTS.items():
        st.session_state[key] = val
    st.session_state.version_loaded = VERSION

NAMEN = {"NVDA":"Nvidia", "000660.KS":"SK Hynix", "005930.KS":"Samsung", "TSM":"TSMC", "MU":"Micron", "AVGO":"Broadcom", "ASML":"ASML", "AMD":"AMD", "AMAT":"Applied Materials", "LRCX":"Lam Research", "KLAC":"KLA", "285A.T":"Kioxia", "SNDK":"SanDisk", "MSFT":"Microsoft", "GOOGL":"Alphabet", "AMZN":"Amazon"}

PFLICHT_KPIS = [
    "Forward_KGV","PEG","EV_EBITDA","FCF_Yield",
    "Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"
]

KPI_LABELS = {
    "Forward_KGV":"Forward KGV","PEG":"PEG Ratio","EV_EBITDA":"EV/EBITDA","FCF_Yield":"FCF Yield",
    "Umsatz_Wachstum":"Umsatzwachstum","OpMarge":"Operative Marge","FCF_Marge":"FCF Marge",
    "Performance_52W":"52 Wochen Performance",
    "AI_Score":"AI Strategischer Score"
}

KPI_HINTS = {
    "Forward_KGV":"z.B. 25.4","PEG":"z.B. 0.8","EV_EBITDA":"z.B. 18","FCF_Yield":"z.B. 0.05 = 5%",
    "Umsatz_Wachstum":"z.B. 0.15 = 15%","OpMarge":"z.B. 0.30 = 30%","FCF_Marge":"z.B. 0.20 = 20%",
    "Performance_52W":"z.B. 0.40 = +40%",
    "AI_Score":"""0-100 Punkte:
90-100 = dominanter AI Gewinner
(z.B. Nvidia CUDA, TSMC Leading Edge)
70-90 = starke Position
(z.B. SK Hynix HBM, Broadcom ASIC)
50-70 = AI Exposure vorhanden
30-50 = indirekter Gewinner
0-30 = kaum AI Vorteil"""
}

def get_fear_greed():
    try:
        url="https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10)
        return r.json()["fear_and_greed"]["score"]
    except: return np.nan

def get_cycle_score(): return 80
def fear_greed_status(score): return "Neutral" if pd.isna(score) else "Extreme Fear" if score<20 else "Fear" if score<40 else "Neutral" if score<60 else "Greed" if score<80 else "Extreme Greed"
def cycle_status(score): return "Spätzyklisch / Attraktiv" if score >= 80 else "Mid-Cycle" if score >= 60 else "Frühzyklisch / Vorsicht"
def safe_get(info, key):
    try: value = info.get(key); return np.nan if value is None else value
    except: return np.nan

# 2. FIX: parse_number kpi-aware
def parse_number(text, kpi=None):
    if text is None: return np.nan
    text = str(text).strip().replace(",", ".")
    try:
        if "%" in text:
            value = float(text.replace("%",""))
            if kpi == "AI_Score": # AI_Score ist 0-100, nicht %
                return value
            return value / 100
        return float(text)
    except: return np.nan

def web_suche_kpi(ticker, kpi):
    if kpi == "AI_Score": return None
    try: pass
    except: pass
    return None

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        st.session_state.datenbank[ticker] = {"daten":{"Ticker":ticker,"Name":NAMEN.get(ticker,ticker)},"audit":{},"status":"neu"}

def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={"Wert":value,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_laden(ticker):
    try:
        time.sleep(1.2)
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        if not info: return None
        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv): forward_kgv = safe_get(info, "trailingPE")
        peg = safe_get(info, "pegRatio"); ev_ebitda = safe_get(info, "enterpriseToEbitda")
        fcf = safe_get(info, "freeCashflow"); marketcap = safe_get(info, "marketCap"); umsatz = safe_get(info, "totalRevenue")
        fcf_yield = fcf / marketcap if not pd.isna(fcf) and not pd.isna(marketcap) and marketcap!= 0 else np.nan
        fcf_marge = fcf / umsatz if not pd.isna(fcf) and not pd.isna(umsatz) and umsatz!= 0 else np.nan
        umsatz_wachstum = safe_get(info, "revenueGrowth"); op_marge = safe_get(info, "operatingMargins")
        hist = tk.history(period="1y")
        perf_52w = np.nan; rs_vs_nasdaq = np.nan; abstand_200 = np.nan; volat = np.nan
        if len(hist) > 200:
            perf_52w = hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1
            sma200 = hist["Close"].tail(200).mean()
            abstand_200 = hist["Close"].iloc[-1] / sma200 - 1
            volat = hist["Close"].pct_change().std() * np.sqrt(252)
            nasdaq = yf.Ticker("^IXIC").history(period="1y")
            if len(nasdaq) > 0: rs_vs_nasdaq = perf_52w - (nasdaq["Close"].iloc[-1] / nasdaq["Close"].iloc[0] - 1)
        return {
            "Forward_KGV":forward_kgv,"PEG":peg,"EV_EBITDA":ev_ebitda,"FCF_Yield":fcf_yield,
            "Umsatz_Wachstum":umsatz_wachstum,"OpMarge":op_marge,"FCF_Marge":fcf_marge,"Performance_52W":perf_52w,
            "RS_vs_Nasdaq":rs_vs_nasdaq, "Abstand_200":abstand_200, "Volatilitaet":volat
        }
    except: return None

# 1. FIX: AI_Score immer abfragen
def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    fehlend = [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi, np.nan))]
    if pd.isna(daten.get("AI_Score", np.nan)):
        fehlend.append("AI_Score")
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
            obj["status"] = "geladen"
        fehlend = fehlende_kpis(ticker)
        for kpi in fehlend:
            queue.append((ticker, kpi))
    st.session_state.abfrage_queue = queue

def screen_sammeln():...
def screen_uebersicht():...
def screen_abfrage():
    if len(st.session_state.abfrage_queue) == 0:
        st.session_state.modus = "ranking"; st.rerun(); return
    ticker, kpi = st.session_state.abfrage_queue[0]
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.progress(1 - len(st.session_state.abfrage_queue)/max(1, len(st.session_state.abfrage_queue)+1))
    st.error(f"❗ {ticker} - {NAMEN.get(ticker,ticker)}")
    st.warning(f"Fehlender Wert: {KPI_LABELS[kpi]}")
    st.caption(f"Noch {len(st.session_state.abfrage_queue)} Abfragen offen")
    st.divider()
    st.write(f"### {KPI_LABELS[kpi]}"); st.info(KPI_HINTS[kpi])
    input_key = f"input_{ticker}_{kpi}"
    if input_key not in st.session_state: st.session_state[input_key] = ""
    eingabe = st.text_input("Wert eingeben", key=input_key, placeholder="z.B. 0.08 oder 85")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern", key=f"save_{ticker}_{kpi}"):
            raw = eingabe
            # 2. FIX: kpi mit übergeben
            wert = parse_number(raw, kpi)
            if pd.isna(wert): st.error(f"Keine gültige Zahl: '{raw}'"); return
            save_kpi(ticker, kpi, wert, "Manuell"); del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col2:
        if st.button("🔍 Websuche", key=f"web_{ticker}_{kpi}", disabled=(kpi=="AI_Score")):
            st.error("Für AI_Score keine Websuche")
    with col3:
        if st.button("⏭️ Überspringen", key=f"skip_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, np.nan, "Übersprungen")
            if input_key in st.session_state: del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()

def screen_ranking():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.success("Auswertung läuft...")
    liste=[]
    for ticker in st.session_state.aktien_liste:
        liste.append(st.session_state.datenbank[ticker]["daten"])

    df=pd.DataFrame(liste)
    def percentile_score(series, higher_better=True):
        s = pd.to_numeric(series, errors="coerce"); valid = s.dropna()
        if len(valid)<2: return pd.Series(50, index=s.index)
        rank = valid.rank(pct=True)
        if not higher_better: rank = 1-rank
        result=pd.Series(50, index=s.index, dtype=float); result.loc[valid.index]=rank*100; return result

    kgv = percentile_score(df["Forward_KGV"], False); peg = percentile_score(df["PEG"], False)
    ev = percentile_score(df["EV_EBITDA"], False); fcf = percentile_score(df["FCF_Yield"], True)
    df["Bewertung_Score"]=(kgv*0.35+peg*0.25+ev*0.20+fcf*0.20)
    growth=percentile_score(df["Umsatz_Wachstum"], True); marge=percentile_score(df["OpMarge"], True); fcfm=percentile_score(df["FCF_Marge"], True)
    df["Qualitaet_Score"]=(growth*0.35+marge*0.35+fcfm*0.30)
    perf = percentile_score(df["Performance_52W"], True)
    rs = percentile_score(df["RS_vs_Nasdaq"], True)
    trend = percentile_score(df["Abstand_200"], True)
    vol = percentile_score(df["Volatilitaet"], False)
    df["Momentum_Score"]=(perf*0.40 + rs*0.30 + trend*0.20 + vol*0.10)

    # 2. FIX: Direkt nutzen
    df["Strategie_Score"] = df["AI_Score"].fillna(50)

    # 3. NEU: Status Spalte
    df["AI_Score_Status"] = np.where(df["AI_Score"].isna(), "fehlend", "manuell")

    df["Rohscore"]=(df["Bewertung_Score"]*0.30 + df["Qualitaet_Score"]*0.30 + df["Momentum_Score"]*0.20 + df["Strategie_Score"]*0.20)
    daten_quali = df[PFLICHT_KPIS].notna().sum(axis=1) / len(PFLICHT_KPIS)
    df["Gesamtscore"]=(df["Rohscore"] * (0.6 + 0.4 * daten_quali)).round(1)
    df["Risiko"] = df["Volatilitaet"].apply(lambda x: "hoch" if x>0.6 else "mittel" if x>0.4 else "niedrig")
    df=df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    ratings=["STRONG BUY" if i < len(df)*0.2 else "BUY" if i < len(df)*0.5 else "HOLD" for i in range(len(df))]
    df["Rating"]=ratings
    df["Datenqualitaet"] = (daten_quali*100).round(0).astype(int).astype(str) + "%"

    st.subheader("Ranking")
    st.dataframe(
        df[["Ticker","Name","Gesamtscore","AI_Score","AI_Score_Status","Bewertung_Score","Qualitaet_Score","Momentum_Score","Risiko","Datenqualitaet"]].round(1),
        use_container_width=True, hide_index=True
    )

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="AI_Ranking_v17.2.1")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v17.2.1_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
    if st.button("⬅️ Zurück zur Liste"):
        st.session_state.modus = "sammeln"; st.rerun()

if st.session_state.modus == "sammeln": screen_sammeln()
elif st.session_state.modus == "uebersicht": screen_uebersicht()
elif st.session_state.modus == "abfrage": screen_abfrage()
elif st.session_state.modus == "ranking": screen_ranking()
