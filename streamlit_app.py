# ============================================
# AI Infrastructure Return Ranking v15.1
# Neuer Assistenten-Modus + Websuche
#
# Ablauf:
# 1. Yahoo Daten laden
# 2. Fehlenden KPI einzeln abfragen
# 3. Wert speichern + Audit
# 4. Nächster KPI
# 5. Nächster Ticker
# 6. Ranking erst am Ende
#
# Neu in v15.1:
# - 🔍 Websuche pro KPI
# - Status "übersprungen" = ⏭️
# - Momentum 6er Skala wie v13.6
# - Button "Alle Daten aktualisieren"
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

# ============================================
# APP SETUP
# ============================================

st.set_page_config(
    page_title="AI Return Ranking v15.1",
    layout="wide"
)

VERSION = "v15.1"

st.warning(
    "KI-Capex-Zyklus intakt bis Q4 2027. "
    "Ziel: Gewinner mit Gewinnhebel und vernünftiger Bewertung finden."
)

# ============================================
# SESSION STATE
# ============================================

if "aktien_liste" not in st.session_state:

    st.session_state.aktien_liste = [
        "NVDA",
        "000660.KS",
        "005930.KS",
        "TSM",
        "MU",
        "AVGO",
        "ASML",
        "AMD",
        "AMAT",
        "LRCX",
        "KLAC",
        "285A.T",
        "SNDK",
        "MSFT",
        "GOOGL",
        "AMZN"
    ]

if "datenbank" not in st.session_state:
    st.session_state.datenbank = {}

if "ticker_index" not in st.session_state:
    st.session_state.ticker_index = 0

if "ranking_start" not in st.session_state:
    st.session_state.ranking_start = False

if "web_vorschlaege" not in st.session_state:
    st.session_state.web_vorschlaege = {} # {(ticker,kpi): wert}

# ============================================
# NAMEN
# ============================================

NAMEN = {
    "NVDA":"Nvidia",
    "000660.KS":"SK Hynix",
    "005930.KS":"Samsung",
    "TSM":"TSMC",
    "MU":"Micron",
    "AVGO":"Broadcom",
    "ASML":"ASML",
    "AMD":"AMD",
    "AMAT":"Applied Materials",
    "LRCX":"Lam Research",
    "KLAC":"KLA",
    "285A.T":"Kioxia",
    "SNDK":"SanDisk",
    "MSFT":"Microsoft",
    "GOOGL":"Alphabet",
    "AMZN":"Amazon"
}

# ============================================
# PFLICHT KPI
# ============================================

PFLICHT_KPIS = [
    "Forward_KGV",
    "PEG",
    "EV_EBITDA",
    "FCF_Yield",
    "Umsatz_Wachstum",
    "OpMarge",
    "FCF_Marge",
    "Performance_52W"
]

KPI_LABELS = {
    "Forward_KGV":"Forward KGV",
    "PEG":"PEG Ratio",
    "EV_EBITDA":"EV/EBITDA",
    "FCF_Yield":"FCF Yield",
    "Umsatz_Wachstum":"Umsatzwachstum",
    "OpMarge":"Operative Marge",
    "FCF_Marge":"FCF Marge",
    "Performance_52W":"52 Wochen Performance"
}

KPI_HINTS = {
    "Forward_KGV":"z.B. 25.4",
    "PEG":"z.B. 0.8",
    "EV_EBITDA":"z.B. 18",
    "FCF_Yield":"z.B. 0.05 = 5%",
    "Umsatz_Wachstum":"z.B. 0.15 = 15%",
    "OpMarge":"z.B. 0.30 = 30%",
    "FCF_Marge":"z.B. 0.20 = 20%",
    "Performance_52W":"z.B. 0.40 = +40%"
}

# ============================================
# HILFSFUNKTIONEN
# ============================================

def safe_get(info, key):
    try:
        value = info.get(key)
        if value is None:
            return np.nan
        return value
    except:
        return np.nan

def parse_number(text):
    """
    Akzeptiert:
    0.08
    0,08
    8%
    """
    if text is None:
        return np.nan
    text = str(text).strip()
    text = text.replace(",", ".")
    if "%" in text:
        text = text.replace("%","")
        return float(text)/100
    return float(text)

# ============================================
# WEBSUCHE
# ============================================

def web_suche_kpi(ticker, kpi):
    """Einfache Suche auf StockAnalysis"""
    try:
        urls = {
            "PEG": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "Forward_KGV": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "EV_EBITDA": f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/",
            "FCF_Yield": f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/"
        }
        if kpi not in urls:
            return None

        r = requests.get(urls[kpi], timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
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
            if kpi == "FCF_Yield":
                val = val / 100
            return val
    except:
        pass
    return None

# ============================================
# DATENSTRUKTUR FÜR TICKER
# ============================================

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        st.session_state.datenbank[ticker] = {
            "daten":{
                "Ticker":ticker,
                "Name":NAMEN.get(ticker,ticker)
            },
            "audit":{},
            "status":"neu"
        }

# ============================================
# AUDIT SPEICHERN
# ============================================

def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={
        "Wert":value,
        "Quelle":quelle,
        "Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Version":VERSION
    }

# ============================================
# YAHOO DATEN LADEN
# ============================================

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_laden(ticker):
    try:
        time.sleep(1)
        aktie = yf.Ticker(ticker)
        info = aktie.info or {}
        if not info:
            return None

        # Bewertung
        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv):
            forward_kgv = safe_get(info, "trailingPE")
        peg = safe_get(info, "pegRatio")
        ev_ebitda = safe_get(info, "enterpriseToEbitda")

        # Cashflow
        fcf = safe_get(info, "freeCashflow")
        marketcap = safe_get(info, "marketCap")
        umsatz = safe_get(info, "totalRevenue")

        if not pd.isna(fcf) and not pd.isna(marketcap) and marketcap!= 0:
            fcf_yield = fcf / marketcap
        else:
            fcf_yield = np.nan

        if not pd.isna(fcf) and not pd.isna(umsatz) and umsatz!= 0:
            fcf_marge = fcf / umsatz
        else:
            fcf_marge = np.nan

        # Wachstum und Margen
        umsatz_wachstum = safe_get(info, "revenueGrowth")
        op_marge = safe_get(info, "operatingMargins")
        performance = safe_get(info, "52WeekChange")

        # Fallback Kursentwicklung
        if pd.isna(performance):
            try:
                hist = aktie.history(period="1y")
                if len(hist)>5:
                    performance = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] -1)
            except:
                pass

        daten = {
            "Forward_KGV":forward_kgv,
            "PEG":peg,
            "EV_EBITDA":ev_ebitda,
            "FCF_Yield":fcf_yield,
            "Umsatz_Wachstum":umsatz_wachstum,
            "OpMarge":op_marge,
            "FCF_Marge":fcf_marge,
            "Performance_52W":performance
        }
        return daten

    except Exception as e:
        return None

# ============================================
# YAHOO DATEN IN DATENBANK ÜBERNEHMEN
# ============================================

def ticker_laden(ticker):
    init_ticker(ticker)
    obj = st.session_state.datenbank[ticker]

    # schon geladen?
    if obj["status"]!= "neu":
        return

    daten = yahoo_laden(ticker)

    if daten is None:
        obj["status"]="fehler"
        return

    for kpi, wert in daten.items():
        obj["daten"][kpi]=wert
        if pd.isna(wert):
            quelle="Fehlt"
        else:
            quelle="Yahoo"
        obj["audit"][kpi]={
            "Wert":wert,
            "Quelle":quelle,
            "Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Version":VERSION
        }
    obj["status"]="pruefen"

# ============================================
# FEHLENDE KPI ERMITTELN
# ============================================

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    fehlen=[]
    for kpi in PFLICHT_KPIS:
        if pd.isna(daten.get(kpi,np.nan)):
            fehlen.append(kpi)
    return fehlen

# ============================================
# TICKER FERTIG?
# ============================================

def ticker_vollstaendig(ticker):
    return len(fehlende_kpis(ticker)) == 0

# ============================================
# NÄCHSTER TICKER
# ============================================

def naechster_ticker():
    st.session_state.ticker_index += 1

# ============================================
# STATUSANZEIGE
# ============================================

def status_text(ticker):
    obj = st.session_state.datenbank.get(ticker)
    if obj is None:
        return "⏳"
    if obj["status"]=="fehler":
        return "❌"
    if obj["status"]=="übersprungen":
        return "⏭️" # NEU
    if ticker_vollstaendig(ticker):
        return "✅"
    return "⚠️"

# ============================================
# KPI ASSISTENT
# ============================================

def kpi_assistent(ticker):
    obj = st.session_state.datenbank[ticker]
    fehlend = fehlende_kpis(ticker)

    # Alle KPIs vorhanden
    if len(fehlend) == 0:
        obj["status"] = "fertig"
        st.success(f"✅ {ticker} vollständig")
        return True

    # Nur ERSTER fehlender KPI
    kpi = fehlend[0]

    st.error(f"❗ {ticker} - {NAMEN.get(ticker,ticker)}")
    st.warning(f"Fehlender Wert: {KPI_LABELS[kpi]}")
    st.caption(f"Noch {len(fehlend)} KPI(s) offen")
    st.divider()

    st.write(f"### {KPI_LABELS[kpi]}")
    st.info(KPI_HINTS[kpi])

    # Websuche Vorschlag anzeigen
    if (ticker,kpi) in st.session_state.web_vorschlaege:
        vorschlag = st.session_state.web_vorschlaege[(ticker,kpi)]
        st.success(f"Vorschlag gefunden: {vorschlag}")
        if st.button("Übernehmen", key=f"apply_web_{ticker}_{kpi}"):
            save_kpi(ticker, kpi, vorschlag, "Internet")
            del st.session_state.web_vorschlaege[(ticker,kpi)]
            st.rerun()

    eingabe = st.text_input(
        "Wert eingeben",
        key=f"input_{ticker}_{kpi}",
        placeholder="z.B. 0.08"
    )

    col1,col2,col3 = st.columns(3)

    with col1:
        if st.button("💾 Speichern", key=f"save_{ticker}_{kpi}"):
            try:
                wert = parse_number(eingabe)
                if pd.isna(wert):
                    st.error("Bitte Zahl eingeben")
                    return False
                # Plausibilität
                if kpi in ["Umsatz_Wachstum","OpMarge","FCF_Marge","Performance_52W"] and wert > 2:
                    st.warning("Wert > 200%. Meintest du 0.15 statt 15?")
                save_kpi(ticker, kpi, wert, "Manuell")
                st.success(f"{KPI_LABELS[kpi]} gespeichert: {wert}")
                st.rerun()
            except:
                st.error("Keine gültige Zahl")

    with col2:
        if st.button("🔍 Websuche", key=f"web_{ticker}_{kpi}"):
            with st.spinner("Suche..."):
                vorschlag = web_suche_kpi(ticker, kpi)
                if vorschlag:
                    st.session_state.web_vorschlaege[(ticker,kpi)] = vorschlag
                    st.rerun()
                else:
                    st.error("Nichts gefunden")

    with col3:
        if st.button("⏭️ Überspringen", key=f"skip_{ticker}"):
            obj["status"]="übersprungen"
            naechster_ticker()
            st.rerun()

    return False

# ============================================
# HAUPTSTEUERUNG ASSISTENT
# ============================================

def assistenten_lauf():
    if st.session_state.ticker_index >= len(st.session_state.aktien_liste):
        st.session_state.ranking_start=True
        return

    ticker = st.session_state.aktien_liste[st.session_state.ticker_index]
    ticker_laden(ticker)
    obj = st.session_state.datenbank[ticker]

    if obj["status"]=="fehler":
        st.error(f"{ticker}: Keine Yahoo Daten")
        if st.button("Weiter"):
            naechster_ticker()
            st.rerun()
        return

    fertig = kpi_assistent(ticker)
    if fertig:
        naechster_ticker()
        st.rerun()

# ============================================
# FORTSCHRITT
# ============================================

def fortschritt():
    gesamt=len(st.session_state.aktien_liste)
    aktuell=st.session_state.ticker_index
    if gesamt>0:
        st.progress(aktuell/gesamt, text=f"{aktuell}/{gesamt} Aktien geprüft")
        # Status Liste
        cols = st.columns(4)
        for i, t in enumerate(st.session_state.aktien_liste):
            with cols[i%4]:
                st.write(f"{status_text(t)} {t}")

# ============================================
# SCORE BERECHNUNG
# ============================================

def percentile_score(series, higher_better=True):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if len(valid)<2:
        return pd.Series(50, index=s.index)
    rank = valid.rank(pct=True)
    if not higher_better:
        rank = 1-rank
    result=pd.Series(50, index=s.index, dtype=float)
    result.loc[valid.index]=rank*100
    return result

def momentum_score(value):
    # 6er Skala wie v13.6
    if pd.isna(value):
        return np.nan
    if value <= -0.20: return 0
    elif value <= -0.10: return 33.3
    elif value <= 0.10: return 50.0
    elif value <= 0.50: return 66.7
    elif value <= 1.00: return 83.3
    else: return 100.0

def berechne_ranking(df):
    # Gewinnhebel
    df["AI_Gewinnhebel"] = df["Performance_52W"].apply(momentum_score)
    # Bewertung
    kgv = percentile_score(df["Forward_KGV"], False)
    peg = percentile_score(df["PEG"], False)
    ev = percentile_score(df["EV_EBITDA"], False)
    fcf = percentile_score(df["FCF_Yield"], True)
    df["Bewertung_Score"]=(kgv*0.15+peg*0.15+ev*0.05+fcf*0.05)
    # Qualität
    growth=percentile_score(df["Umsatz_Wachstum"], True)
    marge=percentile_score(df["OpMarge"], True)
    fcfm=percentile_score(df["FCF_Marge"], True)
    df["Gewinnqualitaet_Score"]=(growth*0.4+marge*0.4+fcfm*0.2)
    df["Gesamtscore"]=(df["AI_Gewinnhebel"]*0.35+df["Bewertung_Score"]*0.40+df["Gewinnqualitaet_Score"]*0.20+5).round(1)
    df=df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    ratings=[]
    for i in range(len(df)):
        if i < len(df)*0.2:
            ratings.append("STRONG BUY")
        elif i < len(df)*0.5:
            ratings.append("BUY")
        else:
            ratings.append("HOLD")
    df["Rating"]=ratings
    return df

# ============================================
# APP START
# ============================================

st.title(f"AI Infrastructure Return Ranking {VERSION}")

# SIDEBAR
with st.sidebar:
    st.header("Steuerung")
    if st.button("🔄 Alle Daten aktualisieren"):
        st.session_state.datenbank = {}
        st.session_state.ticker_index = 0
        st.session_state.ranking_start = False
        st.session_state.web_vorschlaege = {}
        st.rerun()

fortschritt()

# ============================================
# ASSISTENT AUSFÜHREN
# ============================================

if not st.session_state.ranking_start:
    assistenten_lauf()
    st.stop()

# ============================================
# RANKING NUR NACH ABSCHLUSS
# ============================================

st.success("Alle Daten vollständig. Ranking wird berechnet.")

liste=[]
audit=[]
for ticker,obj in st.session_state.datenbank.items():
    if obj["status"]=="fertig":
        liste.append(obj["daten"])
        audit.append(obj["audit"])

if len(liste)<2:
    st.error("Zu wenige vollständige Aktien")
    st.stop()

df=pd.DataFrame(liste)
df=berechne_ranking(df)
df.insert(0,"Datum",datetime.now().strftime("%Y-%m-%d"))

# ============================================
# AUDIT SPALTEN
# ============================================

for kpi in PFLICHT_KPIS:
    df[f"{kpi}_Quelle"]=[a.get(kpi,{}).get("Quelle","") for a in audit]
    df[f"{kpi}_Zeit"]=[a.get(kpi,{}).get("Zeit","") for a in audit]

st.subheader("Ranking")
st.dataframe(df[["Ticker","Name","Gesamtscore","Rating","AI_Gewinnhebel","Bewertung_Score","Gewinnqualitaet_Score"]], use_container_width=True, hide_index=True)

# ============================================
# AUDIT
# ============================================

with st.expander("KPI Audit Trail"):
    st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================
# EXCEL EXPORT
# ============================================

output=io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="AI_Ranking_v15.1")

st.download_button(
    "📥 Excel herunterladen",
    output.getvalue(),
    file_name=f"AI_Ranking_v15.1_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
)
