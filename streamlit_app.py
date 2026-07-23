# ============================================
# AI Infrastructure Return Ranking v15.4.1
# FIX: SyntaxError in yahoo_laden try/except
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

st.set_page_config(page_title="AI Return Ranking v15.4.1", layout="wide")
VERSION = "v15.4.1"

st.warning("KI-Capex-Zyklus intakt bis Q4 2027. Ziel: Gewinner mit Gewinnhebel und vernünftiger Bewertung finden.")

# ============================================
# SESSION STATE + HARD RESET
# ============================================

DEFAULTS = {
    "aktien_liste": ["NVDA","000660.KS","005930.KS","TSM","MU","AVGO","ASML","AMD","AMAT","LRCX","KLAC","285A.T","SNDK","MSFT","GOOGL","AMZN"],
    "datenbank": {},
    "ticker_index": 0,
    "ranking_start": False,
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
    st.rerun()

NAMEN = {
    "NVDA":"Nvidia", "000660.KS":"SK Hynix", "005930.KS":"Samsung", "TSM":"TSMC", "MU":"Micron", "AVGO":"Broadcom", "ASML":"ASML",
    "AMD":"AMD", "AMAT":"Applied Materials", "LRCX":"Lam Research", "KLAC":"KLA",
    "285A.T":"Kioxia", "SNDK":"SanDisk", "MSFT":"Microsoft", "GOOGL":"Alphabet", "AMZN":"Amazon"
}

PFLICHT_KPIS = ["Forward_KGV","PEG","EV_EBITDA","FCF_Yield","Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"]
KPI_LABELS = {"Forward_KGV":"Forward KGV","PEG":"PEG Ratio","EV_EBITDA":"EV/EBITDA","FCF_Yield":"FCF Yield","Umsatz_Wachstum":"Umsatzwachstum","OpMarge":"Operative Marge","FCF_Marge":"FCF Marge","Performance_52W":"52 Wochen Performance"}
KPI_HINTS = {"Forward_KGV":"z.B. 25.4","PEG":"z.B. 0.8","EV_EBITDA":"z.B. 18","FCF_Yield":"z.B. 0.05 = 5%","Umsatz_Wachstum":"z.B. 0.15 = 15%","OpMarge":"z.B. 0.30 = 30%","FCF_Marge":"z.B. 0.20 = 20%","Performance_52W":"z.B. 0.40 = +40%"}

def safe_get(info, key):
    try: value = info.get(key); return np.nan if value is None else value
    except: return np.nan

def parse_number(text):
    if text is None or text == "": return np.nan
    text = str(text).strip().replace(",", ".")
    if "%" in text: return float(text.replace("%",""))/100
    return float(text)

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
        time.sleep(1)
        info = yf.Ticker(ticker).info or {}
        if not info: return None
        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv): forward_kgv = safe_get(info, "trailingPE")
        peg = safe_get(info, "pegRatio"); ev_ebitda = safe_get(info, "enterpriseToEbitda")
        fcf = safe_get(info, "freeCashflow"); marketcap = safe_get(info, "marketCap"); umsatz = safe_get(info, "totalRevenue")
        fcf_yield = fcf / marketcap if not pd.isna(fcf) and not pd.isna(marketcap) and marketcap!= 0 else np.nan
        fcf_marge = fcf / umsatz if not pd.isna(fcf) and not pd.isna(umsatz) and umsatz!= 0 else np.nan
        umsatz_wachstum = safe_get(info, "revenueGrowth"); op_marge = safe_get(info, "operatingMargins"); performance = safe_get(info, "52WeekChange")

        # FIX: try/except Block korrekt eingerückt
        if pd.isna(performance):
            try:
                hist = yf.Ticker(ticker).history(period="1y")
                if len(hist)>5:
                    performance = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] -1)
            except:
                pass

        return {"Forward_KGV":forward_kgv,"PEG":peg,"EV_EBITDA":ev_ebitda,"FCF_Yield":fcf_yield,"Umsatz_Wachstum":umsatz_wachstum,"OpMarge":op_marge,"FCF_Marge":fcf_marge,"Performance_52W":performance}
    except: return None

def ticker_laden(ticker):
    init_ticker(ticker)
    obj = st.session_state.datenbank[ticker]
    if obj["status"] in ["pruefen","fertig","übersprungen"]: return
    daten = yahoo_laden(ticker)
    if daten is None: obj["status"]="fehler"; return
    for kpi, wert in daten.items():
        if kpi not in obj["daten"] or pd.isna(obj["daten"].get(kpi)):
            obj["daten"][kpi]=wert
            quelle="Yahoo" if not pd.isna(wert) else "Fehlt"
            obj["audit"][kpi]={"Wert":wert,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}
    obj["status"]="pruefen"

def fehlende_kpis(ticker): return [kpi for kpi in PFLICHT_KPIS if pd.isna(st.session_state.datenbank[ticker]["daten"].get(kpi,np.nan))]
def ticker_vollstaendig(ticker): return len(fehlende_kpis(ticker)) == 0
def naechster_ticker(): st.session_state.ticker_index += 1

def status_text(ticker):
    obj = st.session_state.datenbank.get(ticker)
    if obj is None: return "⏳"
    if obj["status"]=="fehler": return "❌"
    if obj["status"]=="übersprungen": return "⏭️"
    if ticker_vollstaendig(ticker): return "✅"
    return "⚠️"

def kpi_assistent(ticker):
    obj = st.session_state.datenbank[ticker]
    fehlend = fehlende_kpis(ticker)
    if len(fehlend) == 0:
        obj["status"] = "fertig"
        st.success(f"✅ {ticker} vollständig")
        return True
    kpi = fehlend[0]
    st.error(f"❗ {ticker} - {NAMEN.get(ticker,ticker)}")
    st.warning(f"Fehlender Wert: {KPI_LABELS[kpi]}")
    st.caption(f"Noch {len(fehlend)} KPI(s) offen")
    st.divider()
    st.write(f"### {KPI_LABELS[kpi]}"); st.info(KPI_HINTS[kpi])
    if (ticker,kpi) in st.session_state.web_vorschlaege:
        vorschlag = st.session_state.web_vorschlaege[(ticker,kpi)]
        st.success(f"Vorschlag: {vorschlag}")
        if st.button("Übernehmen", key=f"apply_web_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, vorschlag, "Internet"); del st.session_state.web_vorschlaege[(ticker,kpi)]; st.rerun()
    eingabe = st.text_input("Wert eingeben", key=f"input_{ticker}_{kpi}", placeholder="z.B. 0.08", value="")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern", key=f"save_{ticker}_{kpi}"):
            raw = st.session_state.get(f"input_{ticker}_{kpi}", "")
            try:
                wert = parse_number(raw)
                if pd.isna(wert): st.error("Bitte gültige Zahl eingeben"); return False
                if kpi in ["Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"] and wert > 2: st.warning("Wert > 200%. Meintest du 0.15 statt 15?")
                save_kpi(ticker, kpi, wert, "Manuell"); st.success(f"{KPI_LABELS[kpi]} gespeichert: {wert}"); st.rerun()
            except: st.error(f"Keine gültige Zahl: {raw}")
    with col2:
        if st.button("🔍 Websuche", key=f"web_{ticker}_{kpi}"):
            with st.spinner("Suche..."):
                vorschlag = web_suche_kpi(ticker, kpi)
                if vorschlag: st.session_state.web_vorschlaege[(ticker,kpi)] = vorschlag; st.rerun()
                else: st.error("Nichts gefunden")
    with col3:
        if st.button("⏭️ Überspringen", key=f"skip_{ticker}"):
            obj["status"]="übersprungen"; naechster_ticker(); st.rerun()
    return False

def ticker_hinzufuegen_box():
    st.subheader("Ticker hinzufügen")
    col1, col2 = st.columns([3,1])
    with col1:
        neuer_ticker = st.text_input("Ticker Symbol", key="neuer_ticker_input", placeholder="z.B. INTC").upper().strip()
    with col2:
        if st.button("➕ Hinzufügen", key="btn_add_ticker"):
            if not neuer_ticker:
                st.warning("Bitte Ticker eingeben")
                return
            if neuer_ticker in st.session_state.aktien_liste:
                st.warning(f"{neuer_ticker} ist bereits in der Liste")
                return
            with st.spinner(f"Prüfe {neuer_ticker}..."):
                test_daten = yahoo_laden(neuer_ticker)
            if test_daten is None:
                st.error(f"{neuer_ticker} nicht gefunden")
                return
            st.session_state.aktien_liste.append(neuer_ticker)
            st.success(f"{neuer_ticker} hinzugefügt")
            st.rerun()

def assistenten_lauf():
    if st.session_state.ticker_index >= len(st.session_state.aktien_liste):
        st.success("Alle Ticker geprüft")
        if st.button("✅ Auswertung jetzt starten", type="primary"):
            st.session_state.ranking_start=True
            st.rerun()
        return
    ticker = st.session_state.aktien_liste[st.session_state.ticker_index]
    ticker_laden(ticker)
    obj = st.session_state.datenbank[ticker]
    if obj["status"]=="fehler":
        st.error(f"{ticker}: Keine Yahoo Daten")
        if st.button("Weiter"): naechster_ticker(); st.rerun()
        return
    fertig = kpi_assistent(ticker)
    if fertig:
        naechster_ticker(); st.rerun()

def fortschritt():
    gesamt=len(st.session_state.aktien_liste); aktuell=st.session_state.ticker_index
    if gesamt>0:
        st.progress(aktuell/gesamt, text=f"{aktuell}/{gesamt} Aktien geprüft")
        cols = st.columns(4)
        for i, t in enumerate(st.session_state.aktien_liste):
            with cols[i%4]: st.write(f"{status_text(t)} {t}")

def percentile_score(series, higher_better=True):
    s = pd.to_numeric(series, errors="coerce"); valid = s.dropna()
    if len(valid)<2: return pd.Series(50, index=s.index)
    rank = valid.rank(pct=True)
    if not higher_better: rank = 1-rank
    result=pd.Series(50, index=s.index, dtype=float); result.loc[valid.index]=rank*100; return result

def momentum_score(value):
    if pd.isna(value): return np.nan
    if value <= -0.20: return 0
    elif value <= -0.10: return 33.3
    elif value <= 0.10: return 50.0
    elif value <= 0.50: return 66.7
    elif value <= 1.00: return 83.3
    else: return 100.0

def berechne_ranking(df):
    df["AI_Gewinnhebel"] = df["Performance_52W"].apply(momentum_score)
    kgv = percentile_score(df["Forward_KGV"], False); peg = percentile_score(df["PEG"], False)
    ev = percentile_score(df["EV_EBITDA"], False); fcf = percentile_score(df["FCF_Yield"], True)
    df["Bewertung_Score"]=(kgv*0.15+peg*0.15+ev*0.05+fcf*0.05)
    growth=percentile_score(df["Umsatz_Wachstum"], True); marge=percentile_score(df["OpMarge"], True); fcfm=percentile_score(df["FCF_Marge"], True)
    df["Gewinnqualitaet_Score"]=(growth*0.4+marge*0.4+fcfm*0.2)
    df["Gesamtscore"]=(df["AI_Gewinnhebel"]*0.35+df["Bewertung_Score"]*0.40+df["Gewinnqualitaet_Score"]*0.20+5).round(1)
    df=df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    ratings=["STRONG BUY" if i < len(df)*0.2 else "BUY" if i < len(df)*0.5 else "HOLD" for i in range(len(df))]
    df["Rating"]=ratings; return df

# ============================================
# APP START
# ============================================

st.title(f"AI Infrastructure Return Ranking {VERSION}")

with st.sidebar:
    st.header("Steuerung")
    st.write(f"Version: {VERSION}")
    st.write(f"Status: {'Ranking' if st.session_state.ranking_start else 'Assistent'}")
    st.write(f"Index: {st.session_state.ticker_index}/{len(st.session_state.aktien_liste)}")
    if st.button("🔄 Hard Reset"):
        for key, val in DEFAULTS.items(): st.session_state[key] = val
        st.session_state.version_loaded = VERSION; st.rerun()

if not st.session_state.ranking_start:
    ticker_hinzufuegen_box()
    st.divider()
    fortschritt()
    assistenten_lauf()
else:
    st.success("Auswertung läuft...")
    liste=[]; audit=[]
    for ticker,obj in st.session_state.datenbank.items():
        if obj["status"]=="fertig":
            liste.append(obj["daten"]); audit.append(obj["audit"])
    if len(liste)<2:
        st.error("Zu wenige vollständige Aktien")
        if st.button("Zurück zum Assistenten"):
            st.session_state.ranking_start=False; st.rerun()
        st.stop()
    df=pd.DataFrame(liste); df=berechne_ranking(df)
    df.insert(0,"Datum",datetime.now().strftime("%Y-%m-%d"))
    for kpi in PFLICHT_KPIS:
        df[f"{kpi}_Quelle"]=[a.get(kpi,{}).get("Quelle","") for a in audit]
        df[f"{kpi}_Zeit"]=[a.get(kpi,{}).get("Zeit","") for a in audit]
    st.subheader("Ranking")
    st.dataframe(df[["Ticker","Name","Gesamtscore","Rating","AI_Gewinnhebel","Bewertung_Score","Gewinnqualitaet_Score"]], use_container_width=True, hide_index=True)
    with st.expander("KPI Audit Trail"): st.dataframe(df, use_container_width=True, hide_index=True)
    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="AI_Ranking_v15.4.1")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v15.4.1_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
