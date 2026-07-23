# ============================================
# AI Infrastructure Return Ranking v15.9
# FIX: Vereinfachter Start. Nur Anzeige + Hinzufügen
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

st.set_page_config(page_title="AI Return Ranking v15.9", layout="wide")
VERSION = "v15.9"

# ============================================
# SESSION STATE
# ============================================

DEFAULTS = {
    "aktien_liste": ["NVDA","000660.KS","005930.KS","TSM","MU","AVGO","ASML","AMD","AMAT","LRCX","KLAC","285A.T","SNDK","MSFT","GOOGL","AMZN"],
    "datenbank": {},
    "modus": "sammeln", # 'sammeln', 'uebersicht', 'abfrage', 'ranking'
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
PFLICHT_KPIS = ["Forward_KGV","PEG","EV_EBITDA","FCF_Yield","Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"]
KPI_LABELS = {"Forward_KGV":"Forward KGV","PEG":"PEG Ratio","EV_EBITDA":"EV/EBITDA","FCF_Yield":"FCF Yield","Umsatz_Wachstum":"Umsatzwachstum","OpMarge":"Operative Marge","FCF_Marge":"FCF Marge","Performance_52W":"52 Wochen Performance"}
KPI_HINTS = {"Forward_KGV":"z.B. 25.4","PEG":"z.B. 0.8","EV_EBITDA":"z.B. 18","FCF_Yield":"z.B. 0.05 = 5%","Umsatz_Wachstum":"z.B. 0.15 = 15%","OpMarge":"z.B. 0.30 = 30%","FCF_Marge":"z.B. 0.20 = 20%","Performance_52W":"z.B. 0.40 = +40%"}

def safe_get(info, key):
    try: value = info.get(key); return np.nan if value is None else value
    except: return np.nan

def parse_number(text):
    if text is None: return np.nan
    text = str(text).strip()
    if text == "": return np.nan
    text = text.replace(",", ".")
    try:
        if "%" in text: return float(text.replace("%","")) / 100
        return float(text)
    except: return np.nan

def web_suche_kpi(ticker, kpi):
    try:
        urls = {"PEG": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/","Forward_KGV": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/","EV_EBITDA": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/","FCF_Yield": f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/"}
        if kpi not in urls: return None
        r = requests.get(urls[kpi], timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
        text = BeautifulSoup(r.text, 'html.parser').get_text()
        patterns = {"PEG": r"PEG Ratio.*?([\d\.]+)","Forward_KGV": r"Forward P/E.*?([\d\.]+)","EV_EBITDA": r"EV/EBITDA.*?([\d\.]+)","FCF_Yield": r"Free Cash Flow Yield.*?([\-\d\.]+)%"}
        match = re.search(patterns[kpi], text, re.IGNORECASE)
        if match: val = float(match.group(1)); return val/100 if kpi == "FCF_Yield" else val
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
        info = yf.Ticker(ticker).info or {}
        if not info: return None
        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv): forward_kgv = safe_get(info, "trailingPE")
        peg = safe_get(info, "pegRatio"); ev_ebitda = safe_get(info, "enterpriseToEbitda")
        fcf = safe_get(info, "freeCashflow"); marketcap = safe_get(info, "marketCap"); umsatz = safe_get(info, "totalRevenue")
        fcf_yield = fcf / marketcap if not pd.isna(fcf) and not pd.isna(marketcap) and marketcap!= 0 else np.nan
        fcf_marge = fcf / umsatz if not pd.isna(fcf) and not pd.isna(umsatz) and umsatz!= 0 else np.nan
        umsatz_wachstum = safe_get(info, "revenueGrowth"); op_marge = safe_get(info, "operatingMargins"); performance = safe_get(info, "52WeekChange")
        if pd.isna(performance):
            try:
                hist = yf.Ticker(ticker).history(period="1y")
                if len(hist)>5: performance = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] -1)
            except: pass
        return {"Forward_KGV":forward_kgv,"PEG":peg,"EV_EBITDA":ev_ebitda,"FCF_Yield":fcf_yield,"Umsatz_Wachstum":umsatz_wachstum,"OpMarge":op_marge,"FCF_Marge":fcf_marge,"Performance_52W":performance}
    except: return None

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    return [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]

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
# SCREEN 1: SAMMELN - VEREINFACHT
# ============================================

def screen_sammeln():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.warning("KI-Capex-Zyklus intakt bis Q4 2027. Ziel: Gewinner mit Gewinnhebel und vernünftiger Bewertung finden.")

    st.subheader("Aktuelle Ticker Liste")

    # PROFESSIONELLE ANZEIGE MIT HÄKCHEN
    cols = st.columns(4)
    for i, ticker in enumerate(st.session_state.aktien_liste):
        with cols[i%4]:
            name = NAMEN.get(ticker, ticker)
            st.write(f"✓ {ticker} - {name}")

    st.caption(f"{len(st.session_state.aktien_liste)} Aktien geladen")
    st.info("Fehlende Werte werden später einzeln abgefragt.")

    st.divider()

    neuer_ticker = st.text_input("Einzeln hinzufügen", placeholder="z.B. INTC")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Hinzufügen", use_container_width=True):
            if neuer_ticker:
                neuer_ticker = neuer_ticker.upper().strip()
                if neuer_ticker in st.session_state.aktien_liste:
                    st.warning(f"{neuer_ticker} ist bereits in der Liste")
                else:
                    with st.spinner(f"Prüfe {neuer_ticker}..."):
                        if yahoo_laden(neuer_ticker) is None:
                            st.error(f"{neuer_ticker} nicht gefunden")
                        else:
                            st.session_state.aktien_liste.append(neuer_ticker)
                            st.success(f"{neuer_ticker} hinzugefügt")
                            st.rerun()
    with col2:
        if st.button("🗑️ Letzten entfernen", use_container_width=True):
            if len(st.session_state.aktien_liste) > 1:
                entfernt = st.session_state.aktien_liste.pop()
                st.success(f"{entfernt} entfernt")
                st.rerun()

    st.divider()
    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Lade Yahoo Daten und baue Abfrageliste..."):
            baue_abfrage_queue()
        st.session_state.modus = "uebersicht"
        st.rerun()

# ============================================
# SCREEN 2: ÜBERSICHT
# ============================================

def screen_uebersicht():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.subheader("2. Daten-Übersicht")

    cols = st.columns(2)
    with cols[0]:
        st.write("### Gefundene Daten")
        for ticker in st.session_state.aktien_liste:
            voll = 8 - len(fehlende_kpis(ticker))
            st.write(f"{ticker:<8} {voll}/8 KPIs")

    with cols[1]:
        st.write("### Fehlende Eingaben")
        if len(st.session_state.abfrage_queue) == 0:
            st.success("Alle Daten vorhanden")
        else:
            for ticker, kpi in st.session_state.abfrage_queue:
                st.write(f"{ticker} {KPI_LABELS[kpi]}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Jetzt Eingabe starten", type="primary", use_container_width=True):
            if len(st.session_state.abfrage_queue) > 0:
                st.session_state.modus = "abfrage"
            else:
                st.session_state.modus = "ranking"
            st.rerun()
    with col2:
        if st.button("⬅️ Zurück zur Liste", use_container_width=True):
            st.session_state.modus = "sammeln"; st.rerun()

# ============================================
# SCREEN 3: ABFRAGE
# ============================================

def screen_abfrage():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    if len(st.session_state.abfrage_queue) == 0:
        st.session_state.modus = "ranking"; st.rerun(); return

    ticker, kpi = st.session_state.abfrage_queue[0]
    st.progress(1 - len(st.session_state.abfrage_queue)/max(1, len(st.session_state.abfrage_queue)+1))
    st.error(f"❗ {ticker} - {NAMEN.get(ticker,ticker)}")
    st.warning(f"Fehlender Wert: {KPI_LABELS[kpi]}")
    st.caption(f"Noch {len(st.session_state.abfrage_queue)} Abfragen offen")
    st.divider()
    st.write(f"### {KPI_LABELS[kpi]}"); st.info(KPI_HINTS[kpi])

    input_key = f"input_{ticker}_{kpi}"
    if input_key not in st.session_state:
        st.session_state[input_key] = ""

    if (ticker,kpi) in st.session_state.web_vorschlaege:
        vorschlag = st.session_state.web_vorschlaege[(ticker,kpi)]
        st.success(f"Vorschlag: {vorschlag}")
        if st.button("Übernehmen", key=f"apply_web_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, vorschlag, "Internet"); del st.session_state.web_vorschlaege[(ticker,kpi)]
            del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()

    eingabe = st.text_input("Wert eingeben", key=input_key, placeholder="z.B. 0.08")

    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern", key=f"save_{ticker}_{kpi}"):
            raw = eingabe
            wert = parse_number(raw)
            if pd.isna(wert):
                st.error(f"Keine gültige Zahl: '{raw}'")
                return
            save_kpi(ticker, kpi, wert, "Manuell")
            del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()

    with col2:
        if st.button("🔍 Websuche", key=f"web_{ticker}_{kpi}"):
            with st.spinner("Suche..."):
                vorschlag = web_suche_kpi(ticker, kpi)
                if vorschlag: st.session_state.web_vorschlaege[(ticker,kpi)] = vorschlag; st.rerun()
                else: st.error("Nichts gefunden")
    with col3:
        if st.button("⏭️ Überspringen", key=f"skip_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, np.nan, "Übersprungen")
            if input_key in st.session_state: del st.session_state[input_key]
            st.session_state.abfrage_queue.pop(0); st.rerun()

# ============================================
# SCREEN 4: RANKING
# ============================================

def screen_ranking():
    st.title(f"AI Infrastructure Return Ranking {VERSION}")
    st.success("Auswertung läuft...")
    liste=[]; audit=[]
    for ticker in st.session_state.aktien_liste:
        obj = st.session_state.datenbank[ticker]
        liste.append(obj["daten"]); audit.append(obj["audit"])

    if len(liste)<2:
        st.error("Zu wenige Aktien für Ranking")
        if st.button("Zurück"):
            st.session_state.modus = "sammeln"; st.rerun()
        return

    df=pd.DataFrame(liste)
    def percentile_score(series, higher_better=True):
        s = pd.to_numeric(series, errors="coerce"); valid = s.dropna()
        if len(valid)<2: return pd.Series(50, index=s.index)
        rank = valid.rank(pct=True)
        if not higher_better: rank = 1-rank
        result=pd.Series(50, index=s.index, dtype=float); result.loc[valid.index]=rank*100; return result
    def momentum_score(value):
        if pd.isna(value): return 50.0
        if value <= -0.20: return 0
        elif value <= -0.10: return 33.3
        elif value <= 0.10: return 50.0
        elif value <= 0.50: return 66.7
        elif value <= 1.00: return 83.3
        else: return 100.0

    df["AI_Gewinnhebel"] = df["Performance_52W"].apply(momentum_score)
    kgv = percentile_score(df["Forward_KGV"], False); peg = percentile_score(df["PEG"], False)
    ev = percentile_score(df["EV_EBITDA"], False); fcf = percentile_score(df["FCF_Yield"], True)
    df["Bewertung_Score"]=(kgv*0.15+peg*0.15+ev*0.05+fcf*0.05)
    growth=percentile_score(df["Umsatz_Wachstum"], True); marge=percentile_score(df["OpMarge"], True); fcfm=percentile_score(df["FCF_Marge"], True)
    df["Gewinnqualitaet_Score"]=(growth*0.4+marge*0.4+fcfm*0.2)

    daten_score = (df[PFLICHT_KPIS].notna().sum(axis=1) / len(PFLICHT_KPIS)) * 5

    df["Gesamtscore"]=(df["AI_Gewinnhebel"]*0.35+df["Bewertung_Score"]*0.40+df["Gewinnqualitaet_Score"]*0.20 + daten_score).round(1)
    df=df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    ratings=["STRONG BUY" if i < len(df)*0.2 else "BUY" if i < len(df)*0.5 else "HOLD" for i in range(len(df))]
    df["Rating"]=ratings
    df.insert(0,"Datum",datetime.now().strftime("%Y-%m-%d"))

    st.subheader("Ranking")
    st.dataframe(df[["Ticker","Name","Gesamtscore","Rating","AI_Gewinnhebel","Bewertung_Score","Gewinnqualitaet_Score"]], use_container_width=True, hide_index=True)

    with st.expander("KPI Audit Trail"):
        audit_df = pd.DataFrame([
            {"Ticker":t, "KPI":k, **v}
            for t,obj in st.session_state.datenbank.items()
            for k,v in obj["audit"].items()
        ])
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="AI_Ranking_v15.9")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v15.9_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
    if st.button("⬅️ Zurück zur Liste"):
        st.session_state.modus = "sammeln"; st.rerun()

# ============================================
# APP START
# ============================================

if st.session_state.modus == "sammeln":
    screen_sammeln()
elif st.session_state.modus == "uebersicht":
    screen_uebersicht()
elif st.session_state.modus == "abfrage":
    screen_abfrage()
elif st.session_state.modus == "ranking":
    screen_ranking()
