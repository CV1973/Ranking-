# ============================================
# AI Infrastructure Return Ranking v17.3.3
# FINAL KISS UI: Ticker + AI_Score Box in Reihe
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

st.set_page_config(page_title="AI Return Ranking v17.3.3", layout="wide")
VERSION = "v17.3.3"
AI_CYCLE_ASSUMPTION = "INTAKT BIS Q4 2027"

# ============================================
# SESSION STATE
# ============================================

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

NAMEN = {
    "NVDA":"Nvidia", "000660.KS":"SK Hynix", "005930.KS":"Samsung", "TSM":"TSMC", "MU":"Micron",
    "AVGO":"Broadcom", "ASML":"ASML", "AMD":"AMD", "AMAT":"Applied Materials", "LRCX":"Lam Research",
    "KLAC":"KLA", "285A.T":"Kioxia", "SNDK":"SanDisk", "MSFT":"Microsoft", "GOOGL":"Alphabet", "AMZN":"Amazon"
}

AI_SCORES = {
    "NVDA": 100, "000660.KS": 90, "005930.KS": 80, "TSM": 95, "MU": 85, "AVGO": 85, "ASML": 95,
    "AMD": 80, "AMAT": 75, "LRCX": 75, "KLAC": 75, "285A.T": 75, "SNDK": 70, "MSFT": 85, "GOOGL": 85, "AMZN": 85
}

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
90-100 = dominanter AI Gewinner (Nvidia CUDA, TSMC Leading Edge)
70-90 = starke Position (SK Hynix HBM, Broadcom ASIC)
50-70 = AI Exposure vorhanden
30-50 = indirekter Gewinner
0-30 = kaum AI Vorteil"""
}

# ============================================
# HELPER FUNKTIONEN
# ============================================

@st.cache_data(ttl=3600)
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

def parse_number(text, kpi=None):
    if text is None: return np.nan
    text = str(text).strip().replace(",", ".")
    try:
        if "%" in text:
            value = float(text.replace("%",""))
            if kpi == "AI_Score": return value
            return value / 100
        return float(text)
    except: return np.nan

def web_suche_kpi(ticker, kpi):
    if kpi == "AI_Score": return None
    return None

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        ai_score = AI_SCORES.get(ticker, np.nan)
        st.session_state.datenbank[ticker] = {
            "daten":{"Ticker":ticker,"Name":NAMEN.get(ticker,ticker),"AI_Score":ai_score},
            "audit":{},
            "status":"neu"
        }
        if not pd.isna(ai_score):
            st.session_state.datenbank[ticker]["audit"]["AI_Score"] = {
                "Wert":ai_score,"Quelle":"Initial hinterlegt",
                "Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION
            }

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

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    fehlend = [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]
    if ticker not in AI_SCORES and pd.isna(daten.get("AI_Score",np.nan)):
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

# ============================================
# SCREEN 1: SAMMELN - MIT 2 BOXEN
# ============================================

def screen_sammeln():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    fear_greed = get_fear_greed(); cycle = get_cycle_score()
    col1, col2, col3 = st.columns(3)
    with col1: st.info(f"**Investment Thesis:**\nAI Infrastructure Cycle: {AI_CYCLE_ASSUMPTION}")
    with col2: st.info(f"**MARKTREGIME**\nFear & Greed: {fear_greed:.0f} / 100\nStatus: {fear_greed_status(fear_greed)}")
    with col3: st.info(f"**ZYKLUS**\nCycle Score: {cycle:.0f} / 100\nStatus: {cycle_status(cycle)}")

    st.subheader("Aktuelle Ticker Liste")
    cols = st.columns(4)
    for i, ticker in enumerate(st.session_state.aktien_liste):
        with cols[i%4]:
            init_ticker(ticker)
            ai = st.session_state.datenbank.get(ticker,{}).get("daten",{}).get("AI_Score", AI_SCORES.get(ticker,"?"))
            name = NAMEN.get(ticker,ticker)
            st.write(f"✓ {ticker} - {name} | AI:{ai}")

    # NEU: HINTERLEGTE TICKER ÜBERSICHT
    ticker_text = " | ".join(st.session_state.aktien_liste)
    st.text_area(
        "Hinterlegte Ticker",
        ticker_text,
        height=70,
        disabled=True
    )

    # AI SCORE ÜBERSICHT
    score_text = " | ".join([f"{t.split('.')[0]}:{s}" for t,s in AI_SCORES.items()])
    st.text_area(
        "Hinterlegte AI Strategische Scores",
        score_text,
        height=70,
        disabled=True
    )

    st.caption("Nur neue Aktien benötigen manuelle AI-Score Eingabe")
    st.divider()

    neuer_ticker = st.text_input("Einzeln hinzufügen", placeholder="z.B. INTC")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Hinzufügen", use_container_width=True):
            if neuer_ticker:
                neuer_ticker = neuer_ticker.upper().strip()
                if neuer_ticker in st.session_state.aktien_liste: st.warning(f"{neuer_ticker} ist bereits in der Liste")
                else:
                    with st.spinner(f"Prüfe {neuer_ticker}..."):
                        if yahoo_laden(neuer_ticker) is None: st.error(f"{neuer_ticker} nicht gefunden")
                        else: st.session_state.aktien_liste.append(neuer_ticker); st.success(f"{neuer_ticker} hinzugefügt"); st.rerun()
    with col2:
        if st.button("🗑️ Letzten entfernen", use_container_width=True):
            if len(st.session_state.aktien_liste) > 1: entfernt = st.session_state.aktien_liste.pop(); st.success(f"{entfernt} entfernt"); st.rerun()

    st.divider()
    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Lade Yahoo Daten und baue Abfrageliste..."):
            baue_abfrage_queue()
        st.session_state.modus = "uebersicht"; st.rerun()

# Screens 2-4 unverändert v17.3.2
def screen_uebersicht():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.subheader("2. Daten-Übersicht")
    cols = st.columns(2)
    with cols[0]:
        st.write("### Gefundene Daten")
        for ticker in st.session_state.aktien_liste:
            voll = len(PFLICHT_KPIS) - len([k for k in PFLICHT_KPIS if pd.isna(st.session_state.datenbank[ticker]["daten"].get(k,np.nan))])
            st.write(f"{ticker:<8} {voll}/{len(PFLICHT_KPIS)} KPIs")
    with cols[1]:
        st.write("### Fehlende Eingaben")
        if len(st.session_state.abfrage_queue) == 0: st.success("Alle Daten vorhanden")
        else:
            for ticker, kpi in st.session_state.abfrage_queue: st.write(f"{ticker} {KPI_LABELS[kpi]}")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Jetzt Eingabe starten", type="primary", use_container_width=True):
            if len(st.session_state.abfrage_queue) > 0: st.session_state.modus = "abfrage"
            else: st.session_state.modus = "ranking"
            st.rerun()
    with col2:
        if st.button("⬅️ Zurück zur Liste", use_container_width=True): st.session_state.modus = "sammeln"; st.rerun()

def screen_abfrage():
    if len(st.session_state.abfrage_queue) == 0: st.session_state.modus = "ranking"; st.rerun(); return
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
            raw = eingabe; wert = parse_number(raw, kpi)
            if pd.isna(wert): st.error(f"Keine gültige Zahl: '{raw}'"); return
            save_kpi(ticker, kpi, wert, "Manuell"); del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col2:
        if st.button("🔍 Websuche", key=f"web_{ticker}_{kpi}", disabled=(kpi=="AI_Score")): st.error("Für AI_Score keine Websuche")
    with col3:
        if st.button("⏭️ Überspringen", key=f"skip_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, np.nan, "Übersprungen")
            if input_key in st.session_state: del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()

def screen_ranking():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.success("Auswertung läuft...")
    liste=[]
    for ticker in st.session_state.aktien_liste: liste.append(st.session_state.datenbank[ticker]["daten"])
    if len(liste)<2: st.error("Zu wenige Aktien"); st.button("Zurück", on_click=lambda: setattr(st.session_state, 'modus', 'sammeln')); st.rerun(); return
    df=pd.DataFrame(liste)
    def percentile_score(series, higher_better=True):
        s = pd.to_numeric(series, errors="coerce"); valid = s.dropna()
        if len(valid)<2: return pd.Series(50, index=s.index)
        rank = valid.rank(pct=True);
        if not higher_better: rank = 1-rank
        result=pd.Series(50, index=s.index, dtype=float); result.loc[valid.index]=rank*100; return result
    kgv = percentile_score(df["Forward_KGV"], False); peg = percentile_score(df["PEG"], False)
    ev = percentile_score(df["EV_EBITDA"], False); fcf = percentile_score(df["FCF_Yield"], True)
    df["Bewertung_Score"]=(kgv*0.35+peg*0.25+ev*0.20+fcf*0.20)
    growth=percentile_score(df["Umsatz_Wachstum"], True); marge=percentile_score(df["OpMarge"], True); fcfm=percentile_score(df["FCF_Marge"], True)
    df["Qualitaet_Score"]=(growth*0.35+marge*0.35+fcfm*0.30)
    perf = percentile_score(df["Performance_52W"], True); rs = percentile_score(df["RS_vs_Nasdaq"], True)
    trend = percentile_score(df["Abstand_200"], True); vol = percentile_score(df["Volatilitaet"], False)
    df["Momentum_Score"]=(perf*0.40 + rs*0.30 + trend*0.20 + vol*0.10)
    df["Strategie_Score"] = df["AI_Score"].fillna(50)
    df["AI_Score_Status"] = np.where(df["AI_Score"].isna(), "fehlend", "hinterlegt")
    df["Rohscore"]=(df["Bewertung_Score"]*0.30 + df["Qualitaet_Score"]*0.30 + df["Momentum_Score"]*0.20 + df["Strategie_Score"]*0.20)
    daten_quali = df[PFLICHT_KPIS].notna().sum(axis=1) / len(PFLICHT_KPIS)
    df["Gesamtscore"]=(df["Rohscore"] * (0.6 + 0.4 * daten_quali)).round(1)
    df["Risiko"] = df["Volatilitaet"].apply(
        lambda x: "unbekannt" if pd.isna(x) else "hoch" if x>0.6 else "mittel" if x>0.4 else "niedrig"
    )
    df=df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    ratings=["STRONG BUY" if i < len(df)*0.2 else "BUY" if i < len(df)*0.5 else "HOLD" for i in range(len(df))]
    df["Rating"]=ratings; df["Datenqualitaet"] = (daten_quali*100).round(0).astype(int).astype(str) + "%"
    st.subheader("Ranking")
    st.dataframe(df[["Ticker","Name","Gesamtscore","AI_Score","AI_Score_Status","Bewertung_Score","Qualitaet_Score","Momentum_Score","Risiko","Datenqualitaet"]].round(1), use_container_width=True, hide_index=True)
    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="AI_Ranking_v17.3.3")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v17.3.3_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
    if st.button("⬅️ Zurück zur Liste"): st.session_state.modus = "sammeln"; st.rerun()

# APP START
if st.session_state.modus == "sammeln": screen_sammeln()
elif st.session_state.modus == "uebersicht": screen_uebersicht()
elif st.session_state.modus == "abfrage": screen_abfrage()
elif st.session_state.modus == "ranking": screen_ranking()
