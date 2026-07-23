# ============================================
# AI Infrastructure Bottleneck Ranking v12.1
# Axiom: KI-Capex-Zyklus intakt bis Q4 2027
# Frage: Wer liefert die knappen Bausteine?
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import io
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AI Bottleneck Ranking v12.1", layout="wide")
VERSION = "v12.1"

st.warning("Modell-Annahme: KI-Capex-Zyklus intakt bis Q4 2027. Gesucht: Engpaesslieferanten, nicht AI-Purity.")

if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = [
        "NVDA", "000660.KS", "005930.KS", "TSM", "MU", "AVGO", "ASML",
        "AMD", "AMAT", "LRCX", "KLAC", "285A.T", "SNDK", "MSFT", "GOOGL", "AMZN"
    ]

NAMEN = {
    "NVDA": "Nvidia", "000660.KS": "SK Hynix", "005930.KS": "Samsung", "TSM": "TSMC", "MU": "Micron", "AVGO": "Broadcom", "ASML": "ASML",
    "AMD": "AMD", "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA",
    "285A.T": "Kioxia", "SNDK": "SanDisk", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon"
}

SEKTOR = {
    "NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "TSM": "Foundry",
    "MU": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher", "SNDK": "Speicher",
    "MSFT": "Hyperscaler", "GOOGL": "Hyperscaler", "AMZN": "Hyperscaler"
}

# NEU v12.1: AI INFRASTRUKTUR HEBEL - nicht Purity
# Frage: Ohne wen geht AI-Capex nicht?
AI_INFRA_HEBEL = {
    "000660.KS": 100, # SK Hynix: HBM3E/4 Leader. Ohne HBM keine GPU
    "005930.KS": 95, # Samsung: HBM + DRAM + NAND + Foundry + Packaging. Breiter Hebel
    "NVDA": 95, # Nvidia: GPU. Aber nur 1 Baustein
    "TSM": 95, # TSMC: Fertigt 90% der AI Chips. Foundry Engpass
    "MU": 92, # Micron: HBM2e + DRAM. Zweiter nach SK Hynix
    "AVGO": 90, # Broadcom: Custom ASIC + Networking. Kein Memory aber kritisch
    "ASML": 90, # ASML: EUV. Ohne EUV keine 3nm/2nm
    "AMAT": 88, "LRCX": 88, "KLAC": 88, # Equipment: Jeder Fab Ausbau braucht die 3
    "AMD": 85, # AMD: MI300 Alternative zu NVDA
    "285A.T": 82, # Kioxia: NAND fuer AI Storage
    "SNDK": 78, # SanDisk: Enterprise SSD fuer AI Storage
    "MSFT": 65, "GOOGL": 65, "AMZN": 65 # Hyperscaler: Nachfrager, nicht Engpass
}

# Zyklusdaempfung bleibt: Langfristvertraege dämpfen
ZYKLUSDAEMPFUNG = {
    "NVDA": 30, "AVGO": 40, "TSM": 50, "ASML": 45, "AMD": 35, "MSFT": 80, "GOOGL": 80, "AMZN": 75,
    "MU": 85, "000660.KS": 90, "005930.KS": 80, "SNDK": 75, "285A.T": 70, # Memory hat LTAs
    "AMAT": 50, "LRCX": 50, "KLAC": 50
}

def safe_get(d, key, default=np.nan):
    try:
        if isinstance(d, dict): return d.get(key, default) if d.get(key, default) is not None else default
        return default
    except: return default

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
            umsatz_wachstum = safe_get(info, "revenueGrowth")
            op_marge = safe_get(info, "operatingMargins")
            kurs = safe_get(info, "currentPrice")
            ath = safe_get(info, "fiftyTwoWeekHigh")
            ath_abstand = (ath - kurs) / ath * 100 if pd.notna(ath) and pd.notna(kurs) and ath > 0 else np.nan
            total_debt = safe_get(info, "totalDebt")
            cash = safe_get(info, "totalCash")
            ebitda = safe_get(info, "ebitda")
            net_debt_ebitda = (total_debt - cash) / ebitda if pd.notna(total_debt) and pd.notna(cash) and pd.notna(ebitda) and ebitda > 0 else np.nan

            daten = {
                "Ticker": symbol, "Name": NAMEN.get(symbol, symbol), "Sektor": SEKTOR.get(symbol, "Unbekannt"),
                "Forward_KGV": forward_kgv, "Umsatz_Wachstum": umsatz_wachstum, "OpMarge": op_marge,
                "ATH_Abstand_%": ath_abstand, "NetDebt_EBITDA": net_debt_ebitda
            }
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def normalize_sektor(df, spalte, higher_better=True):
    scores = []
    for idx, row in df.iterrows():
        sektor = row["Sektor"]
        if sektor == "Foundry": sektor = "Equipment"
        sektor_df = df[df["Sektor"]==sektor]
        if len(sektor_df) < 2: sektor_df = df
        wert = row[spalte]
        if pd.isna(wert): scores.append(50); continue
        median = sektor_df[spalte].median()
        if pd.isna(median) or median == 0: scores.append(50); continue
        ratio = wert / median
        if not higher_better: ratio = 1/ratio if ratio > 0 else 1.0
        mean, std = np.log(sektor_df[spalte].dropna()).mean(), np.log(sektor_df[spalte].dropna()).std()
        if std == 0: scores.append(50)
        else:
            z = (np.log(wert) - mean) / (std * 2) if pd.notna(wert) and wert > 0 else 0
            score = (z.clip(-1,1) + 1) * 50
            scores.append(score)
    return pd.Series(scores, index=df.index)

def berechne_scores(df, horizont):
    if horizont == "6M": w_fund, w_these, w_mod = 0.35, 0.40, 0.25
    else: w_fund, w_these, w_mod = 0.40, 0.45, 0.15

    # SAEUlE 1 FUNDAMENTAL
    kgv_score = normalize_sektor(df, "Forward_KGV", higher_better=False)
    wachstum_score = normalize_sektor(df, "Umsatz_Wachstum", higher_better=True)
    qualitaet_score = normalize_sektor(df, "OpMarge", higher_better=True)
    df["Fundamental_Score"] = (kgv_score*0.4 + wachstum_score*0.3 + qualitaet_score*0.3).round(1)

    # SAEUlE 2 THESE - NEU: Infrastruktur Hebel
    df["AI_Infra_Hebel"] = df["Ticker"].map(AI_INFRA_HEBEL).fillna(50)
    df["Zyklusdaempfung"] = df["Ticker"].map(ZYKLUSDAEMPFUNG).fillna(50)
    these_raw = df["AI_Infra_Hebel"]*0.75 + df["Zyklusdaempfung"]*0.25 # Hebel wichtiger als Daempfung
    df["These_Score"] = these_raw.clip(0,100).round(1)

    # MODIFIKATOR
    mod = 1.0 + (df["ATH_Abstand_%"].fillna(0) / 100) * 0.3
    df["ATH_Modifikator"] = np.where(df["Fundamental_Score"] > 50, mod, 1.0).round(2)

    df["Gesamtscore_Roh"] = (df["Fundamental_Score"] * w_fund + df["These_Score"] * w_these) * df["ATH_Modifikator"]

    def get_rating(row):
        score = row["Gesamtscore_Roh"]
        if row["NetDebt_EBITDA"] > 3:
            if score >= 75: return "BUY"
        if score >= 75: return "STRONG BUY"
        elif score >= 60: return "BUY"
        elif score >= 45: return "HOLD"
        else: return "SELL"
    df["Rating"] = df.apply(get_rating, axis=1)
    df["Gesamtscore"] = df["Gesamtscore_Roh"].round(1)
    return df

st.title(f"AI Infrastructure Bottleneck Ranking {VERSION}")
st.caption("Axiom: KI-Capex intakt. Gesucht: Engpaesslieferanten")

horizont = st.radio("Anlagehorizont", ["6M", "12M"], horizontal=True)

with st.sidebar:
    st.header("AI Infrastruktur Hebel v12.1")
    st.table(pd.DataFrame.from_dict(AI_INFRA_HEBEL, orient='index', columns=['Hebel']).sort_values('Hebel', ascending=False))

col1,col2 = st.columns([1,2])
with col1:
    st.info(
        """
        Gewichtung: Fundamental 40% | These 45% | ATH 15%

        These = AI Infrastruktur Hebel 75% + Zyklusdaempfung 25%

        Kernthese:
        Ohne HBM, Foundry, EUV, Equipment
        gibt es keinen AI-Capex.
        """
    )
with col2:
    such_ticker = st.text_input("Ticker hinzufuegen")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Hinzufuegen") and such_ticker.upper():
            if such_ticker.upper() not in st.session_state.aktien_liste: st.session_state.aktien_liste.append(such_ticker.upper())
            st.rerun()
    with c2:
        if st.button("Liste leeren"): st.session_state.aktien_liste=[]; st.rerun()

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0); daten=[]; fehler=[]; status = st.empty()
    for i,symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol} {i+1}/{len(st.session_state.aktien_liste)}")
        data,error = get_yahoo_data(symbol)
        if data: daten.append(data)
        else: fehler.append(error)
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        time.sleep(1.5)

    if len(daten)<2: st.error("Zu wenige Daten"); st.stop()

    df=pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "Sektor"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, horizont).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))
    df["Umsatz_Wachstum"] = (df["Umsatz_Wachstum"]*100).round(1)
    df["OpMarge"] = (df["OpMarge"]*100).round(1)

    tab1,tab2 = st.tabs(["Transparenz", "Ranking"])
    with tab1:
        st.dataframe(df[["Ticker","Name","Fundamental_Score","These_Score","AI_Infra_Hebel","Gesamtscore","Rating"]], use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Rating","Fundamental_Score","These_Score","Forward_KGV","Umsatz_Wachstum"]], use_container_width=True, hide_index=True)
