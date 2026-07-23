# ============================================
# AI Infrastructure Return Ranking v13.8
# Aenderungen: Typo Fix, TextInput, Quelle-Spalte, Plausibilitaet,
# Auto-Websuche, Audit-Trail
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import io
import warnings
import re
import requests
from bs4 import BeautifulSoup
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Return Ranking v13.8", layout="wide")
VERSION = "v13.8"

st.warning("Axiom: KI-Capex-Zyklus intakt bis Q4 2027. Frage: Wer hat Gewinnhebel + ist nicht ueberteuert?")

if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = [
        "NVDA", "000660.KS", "005930.KS", "TSM", "MU", "AVGO", "ASML",
        "AMD", "AMAT", "LRCX", "KLAC", "285A.T", "SNDK", "MSFT", "GOOGL", "AMZN"
    ]
if "manual_overrides" not in st.session_state:
    st.session_state.manual_overrides = {} # {ticker: {kpi: {"wert": x, "quelle": "Manuell"}}}
if "web_suggestions" not in st.session_state:
    st.session_state.web_suggestions = {} # {ticker: {kpi: wert}}

NAMEN = {
    "NVDA": "Nvidia", "000660.KS": "SK Hynix", "005930.KS": "Samsung", "TSM": "TSMC", "MU": "Micron", "AVGO": "Broadcom", "ASML": "ASML",
    "AMD": "AMD", "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA",
    "285A.T": "Kioxia", "SNDK": "SanDisk", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon"
}

# 1. TYPO FIX
PFLICHT_KPIS = [
    "Forward_KGV", "PEG", "EV_EBITDA", "FCF_Yield",
    "Umsatz_Wachstum", "OpMarge", "FCF_Marge", "Performance_52W"
]

KPI_LABELS = {
    "Forward_KGV": "Forward KGV", "PEG": "PEG Ratio", "EV_EBITDA": "EV/EBITDA", "FCF_Yield": "FCF Yield",
    "Umsatz_Wachstum": "Umsatzwachstum", "OpMarge": "Op. Marge", "FCF_Marge": "FCF Marge", "Performance_52W": "52W Performance"
}
KPI_HINWEISE = {
    "Forward_KGV": "Beispiel: 25.4", "PEG": "Beispiel: 0.85", "EV_EBITDA": "Beispiel: 18.4",
    "FCF_Yield": "Beispiel: 0.052 = 5,2%", "Umsatz_Wachstum": "Beispiel: 0.15 = 15%",
    "OpMarge": "Beispiel: 0.22 = 22%", "FCF_Marge": "Beispiel: 0.18 = 18%", "Performance_52W": "Beispiel: 0.42 = 42%"
}

def safe_get(d, key, default=np.nan):
    try:
        if isinstance(d, dict): return d.get(key, default) if d.get(key, default) is not None else default
        return default
    except: return default

def momentum_score_100(perf):
    if pd.isna(perf): return np.nan
    if perf <= -0.20: bracket = 0.00
    elif perf <= -0.10: bracket = 0.50
    elif perf <= 0.10: bracket = 0.75
    elif perf <= 0.50: bracket = 1.00
    elif perf <= 1.00: bracket = 1.25
    else: bracket = 1.50
    return bracket / 1.5 * 100.0

def percentile_score(series, higher_better=True):
    s = pd.to_numeric(series, errors='coerce')
    valid = s.dropna()
    if len(valid) < 2: return pd.Series(50.0, index=s.index, dtype=float)
    rank = valid.rank(pct=True)
    if not higher_better: rank = 1 - rank
    result = pd.Series(50.0, index=s.index, dtype=float)
    result[valid.index] = rank * 100.0
    return result

# 6. AUTOMATISCHE INTERNETSUCHE
def web_search_kpi(ticker, kpi):
    """Einfache Suche auf StockAnalysis + Macrotrends. Gibt Wert oder None zurueck"""
    try:
        urls = {
            "PEG": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "Forward_KGV": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "EV_EBITDA": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "FCF_Yield": f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/"
        }
        if kpi not in urls: return None

        r = requests.get(urls[kpi], timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()

        patterns = {
            "PEG": r"PEG Ratio.*?([\d\.]+)",
            "Forward_KGV": r"Forward P/E.*?([\d\.]+)",
            "EV_EBITDA": r"EV/EBITDA.*?([\d\.]+)",
            "FCF_Yield": r"Free Cash Flow Yield.*?([\-\d\.]+)%"
        }
        match = re.search(patterns[kpi], text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if kpi == "FCF_Yield": val = val / 100 # % zu Dezimal
            return val
    except: pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol, max_retries=2):
    for attempt in range(max_retries):
        try:
            time.sleep(1.5 + attempt * 2)
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            if not info:
                if attempt < max_retries - 1: time.sleep(10)
                continue

            forward_kgv = safe_get(info, "forwardPE")
            if pd.isna(forward_kgv) or forward_kgv <= 0: forward_kgv = safe_get(info, "trailingPE")
            peg = safe_get(info, "pegRatio")
            ev_ebitda = safe_get(info, "enterpriseToEbitda")
            fcf_yield = safe_get(info, "freeCashflow") / safe_get(info, "marketCap") if safe_get(info, "marketCap") else np.nan
            umsatz_wachstum = safe_get(info, "revenueGrowth")
            op_marge = safe_get(info, "operatingMargins")
            fcf_marge = safe_get(info, "freeCashflow") / safe_get(info, "totalRevenue") if safe_get(info, "totalRevenue") else np.nan
            perf_52w = safe_get(info, "52WeekChange")
            if pd.isna(perf_52w):
                try:
                    hist = ticker.history(period="1y")
                    if not hist.empty and len(hist) > 5:
                        perf_52w = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
                except: pass

            # 7. AUDIT TRAIL: Quelle mitfuehren
            daten = {}
            quellen = {}
            for kpi, val in [("Forward_KGV", forward_kgv), ("PEG", peg), ("EV_EBITDA", ev_ebitda), ("FCF_Yield", fcf_yield),
                             ("Umsatz_Wachstum", umsatz_wachstum), ("OpMarge", op_marge), ("FCF_Marge", fcf_marge), ("Performance_52W", perf_52w)]:
                daten[kpi] = val
                quellen[kpi] = "Yahoo" if not pd.isna(val) else "Fehlt"

            daten.update({"Ticker": symbol, "Name": NAMEN.get(symbol, symbol), "_quellen": quellen})
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def berechne_scores(df):
    df["AI_Gewinnhebel"] = df["Performance_52W"].apply(momentum_score_100)
    kgv_score = percentile_score(df["Forward_KGV"], higher_better=False)
    peg_score = percentile_score(df["PEG"], higher_better=False)
    ev_score = percentile_score(df["EV_EBITDA"], higher_better=False)
    fcf_score = percentile_score(df["FCF_Yield"], higher_better=True)
    df["Bewertung_Score"] = (kgv_score*0.15 + peg_score*0.15 + ev_score*0.05 + fcf_score*0.05).round(1)
    umsatz_score = percentile_score(df["Umsatz_Wachstum"], higher_better=True)
    marge_score = percentile_score(df["OpMarge"], higher_better=True)
    fcfm_score = percentile_score(df["FCF_Marge"], higher_better=True)
    df["Gewinnqualitaet_Score"] = (umsatz_score*0.40 + marge_score*0.40 + fcfm_score*0.20).round(1)
    df["Daten_Score"] = 100.0
    df["Gesamtscore"] = (
        df["AI_Gewinnhebel"]*0.35 + df["Bewertung_Score"]*0.40 +
        df["Gewinnqualitaet_Score"]*0.20 + df["Daten_Score"]*0.05
    ).round(1)
    df = df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    n = len(df)
    def get_ranking_rating(idx):
        pct = (idx + 1) / n
        if pct <= 0.20: return "STRONG BUY"
        elif pct <= 0.50: return "BUY"
        else: return "HOLD"
    df["Rating"] = [get_ranking_rating(i) for i in range(n)]
    return df

st.title(f"AI Infrastructure Return Ranking {VERSION}")
st.caption("Gewichtung: Gewinnhebel 35% | Bewertung 40% | Gewinnqualitaet 20% | Daten 5%")
st.info("**Regel:** Ranking nur mit 100% vollstaendigen Pflicht-KPIs. Fehlende Werte koennen manuell ergaenzt oder per Websuche gefunden werden.")

col1,col2 = st.columns([1,2])
with col1:
    st.write("**Inkludierte Ticker:**")
    st.code(", ".join(st.session_state.aktien_liste))
with col2:
    such_ticker = st.text_input("Ticker hinzufuegen")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Hinzufuegen") and such_ticker:
            ticker_up = such_ticker.upper()
            if ticker_up in st.session_state.aktien_liste:
                st.error(f"Fehler: {ticker_up} ist bereits in der Liste")
            else:
                st.session_state.aktien_liste.append(ticker_up)
                st.rerun()
    with c2:
        if st.button("Liste leeren"): st.session_state.aktien_liste=[]; st.session_state.manual_overrides={}; st.rerun()

if st.button("Daten laden & pruefen", type="primary"):
    st.session_state.raw_data = []
    st.session_state.fehlende_kpis = {}
    progress = st.progress(0); status = st.empty()

    for i,symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol} {i+1}/{len(st.session_state.aktien_liste)}")
        data,error = get_yahoo_data(symbol)
        if data:
            quellen = data.pop("_quellen")
            # Manual Overrides einspielen
            if symbol in st.session_state.manual_overrides:
                for kpi, v in st.session_state.manual_overrides[symbol].items():
                    data[kpi] = v["wert"]
                    quellen[kpi] = v["quelle"]

            fehlend = [k for k in PFLICHT_KPIS if pd.isna(data.get(k))]
            if fehlend:
                st.session_state.fehlende_kpis[symbol] = {"kpis": fehlend, "quellen": quellen}
            data["_quellen"] = quellen
            st.session_state.raw_data.append(data)
        else:
            st.error(f"Ticker nicht gefunden: {symbol}")
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        time.sleep(1.5)

if "raw_data" in st.session_state and st.session_state.raw_data:
    df_raw = pd.DataFrame(st.session_state.raw_data)

    if st.session_state.fehlende_kpis:
        st.error("Folgende Ticker haben fehlende Pflicht-KPIs:")
        for ticker, info in st.session_state.fehlende_kpis.items():
            with st.expander(f"{ticker} - {NAMEN.get(ticker, ticker)}"):
                st.write(f"Für Ticker {ticker} konnten folgende Kennzahlen nicht geladen werden:")

                for kpi in info["kpis"]:
                    c1, c2, c3, c4 = st.columns([2,2,2,1])
                    with c1:
                        st.write(f"**{KPI_LABELS[kpi]}**")
                        st.caption(KPI_HINWEISE[kpi]) # 4. EINGABE-HILFE
                    with c2:
                        # 2. TEXT_INPUT statt number_input
                        eingabe = st.text_input("Wert", key=f"manual_{ticker}_{kpi}", placeholder="z.B. 0.85")

                    # 6. WEBSUCHE BUTTON
                    with c3:
                        if st.button("🔍 Im Internet suchen", key=f"web_{ticker}_{kpi}"):
                            vorschlag = web_search_kpi(ticker, kpi)
                            if vorschlag:
                                st.session_state.web_suggestions[(ticker,kpi)] = vorschlag
                                st.rerun()
                            else: st.warning("Nichts gefunden")

                    if (ticker,kpi) in st.session_state.web_suggestions:
                        vorschlag = st.session_state.web_suggestions[(ticker,kpi)]
                        st.info(f"Vorschlag: {vorschlag} Quelle: StockAnalysis")
                        if st.button("Übernehmen", key=f"apply_web_{ticker}_{kpi}"):
                            if ticker not in st.session_state.manual_overrides: st.session_state.manual_overrides[ticker] = {}
                            st.session_state.manual_overrides[ticker][kpi] = {"wert": vorschlag, "quelle": "Internet"}
                            st.rerun()

                    # 5. PLAUSIBILITAETSPRUEFUNG
                    if eingabe:
                        try:
                            val = float(eingabe)
                            if kpi in ["Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"] and val > 2:
                                st.warning("Wert > 200%. Meintest du 0.15 statt 15?")
                            if kpi == "PEG" and val > 50:
                                st.warning("PEG > 50 ist unueblich. Bitte pruefen.")
                            if st.button("Manuell übernehmen", key=f"apply_man_{ticker}_{kpi}"):
                                if ticker not in st.session_state.manual_overrides: st.session_state.manual_overrides[ticker] = {}
                                st.session_state.manual_overrides[ticker][kpi] = {"wert": val, "quelle": "Manuell"}
                                st.rerun()
                        except: st.error("Keine Zahl")

        if st.button("Alle manuellen Werte übernehmen und neu prüfen"):
            st.rerun()
        st.stop()

    df = df_raw.copy()
    for c in df.columns:
        if c not in ["Ticker", "Name", "_quellen"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    # 3. QUELLE ANZEIGEN + 7. AUDIT TRAIL
    for kpi in PFLICHT_KPIS:
        df[f"{kpi}_Quelle"] = df["_quellen"].apply(lambda x: x.get(kpi, "Unbekannt"))

    df["Umsatz_Wachstum"] = (df["Umsatz_Wachstum"]*100).round(1)
    df["OpMarge"] = (df["OpMarge"]*100).round(1)
    df["FCF_Yield"] = (df["FCF_Yield"]*100).round(1)
    df["FCF_Marge"] = (df["FCF_Marge"]*100).round(1)
    df["Performance_52W"] = (df["Performance_52W"]*100).round(1)

    st.success(f"{len(df)} Aktien vollstaendig bewertet")

    tab1,tab2,tab3 = st.tabs(["Transparenz + Audit", "Ranking", "Export"])
    with tab1:
        anzeige_df1 = df.rename(columns={"AI_Gewinnhebel": "AI_Gewinnhebel (52W-Momentum)"})
        cols = ["Ticker","Name","Gesamtscore","Rating","AI_Gewinnhebel (52W-Momentum)","Performance_52W","Bewertung_Score"]
        for kpi in PFLICHT_KPIS:
            cols.extend([kpi, f"{kpi}_Quelle"])
        st.dataframe(anzeige_df1[cols], use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Rating","Forward_KGV","PEG","EV_EBITDA"]], use_container_width=True, hide_index=True)
    with tab3:
        output=io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v13.8")
        st.download_button("Excel herunterladen", output.getvalue(), f"AI_Return_Ranking_v13.8_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
