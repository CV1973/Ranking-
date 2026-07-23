# ============================================
# AI Infrastructure Cycle Ranking v11.0
# Frage: Wer profitiert am meisten vom AI-Capex bis Jahresende?
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

st.set_page_config(page_title="AI Cycle Ranking v11.0", layout="wide")
VERSION = "v11.0"

if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = [
        "NVDA", "000660.KS", "AVGO", "TSM", "MU", "ASML",
        "005930.KS", "AMD", "AMAT", "LRCX", "KLAC",
        "285A.T", "SNDK", "MSFT", "GOOGL", "AMZN"
    ]

NAMEN = {
    "NVDA": "Nvidia", "000660.KS": "SK Hynix", "AVGO": "Broadcom", "TSM": "TSMC", "MU": "Micron", "ASML": "ASML",
    "005930.KS": "Samsung", "AMD": "AMD", "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA",
    "285A.T": "Kioxia", "SNDK": "SanDisk", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon"
}

# FAKTOR 1: AI EXPOSURE FIX - 40%
AI_EXPOSURE_BASE = {
    "NVDA": 100, "000660.KS": 100, # GPU + HBM Leader
    "AVGO": 95, "TSM": 95, # ASIC + Foundry
    "MU": 90, "ASML": 90, # HBM + EUV
    "005930.KS": 85, "AMD": 85, # Samsung HBM + AMD MI300
    "AMAT": 80, "LRCX": 80, "KLAC": 80, # Equipment
    "285A.T": 70, "SNDK": 65, # NAND + AI Storage
    "MSFT": 60, "GOOGL": 60, "AMZN": 60 # Hyperscaler
}

AI_BONUS_REGIME = {
    1.20: { # BOOM: Memory + Equipment + Foundry
        "HBM_DRAM": ["MU", "000660.KS", "005930.KS"],
        "EQUIPMENT": ["ASML", "AMAT", "LRCX", "KLAC"],
        "FOUNDRY": ["TSM"]
    },
    1.00: { # NORMAL: alle gleich
    },
    0.80: { # ABKUEHLUNG: Qualitaet + Monetarisierung
        "QUALITY": ["NVDA", "AVGO", "MSFT", "GOOGL", "AMZN"]
    }
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

            financials = ticker.financials
            history = ticker.history(period="5d")

            kurs = safe_get(info, "currentPrice")
            if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
            if pd.isna(kurs): return None, f"{symbol}: Kein Kurs"

            marketcap = safe_get(info, "marketCap")
            if pd.isna(marketcap): return None, f"{symbol}: Keine Marketcap"

            # FAKTOR 2: EARNINGS MOMENTUM 25%
            eps_wachstum = safe_get(info, "earningsGrowth") # yoy
            umsatz_wachstum = safe_get(info, "revenueGrowth") # yoy
            operating_margin = safe_get(info, "operatingMargins")

            # FAKTOR 3: BEWERTUNG 20%
            forward_kgv = safe_get(info, "forwardPE")
            peg = safe_get(info, "pegRatio")
            ev_ebitda = safe_get(info, "enterpriseToEbitda")

            # FAKTOR 4: BILANZ 15%
            total_debt = safe_get(info, "totalDebt")
            cash = safe_get(info, "totalCash")
            ebitda = safe_get(info, "ebitda")
            net_debt_ebitda = (total_debt - cash) / ebitda if pd.notna(total_debt) and pd.notna(cash) and pd.notna(ebitda) and ebitda > 0 else np.nan

            daten = {
                "Ticker": symbol, "Name": NAMEN.get(symbol, symbol), "Kurs": round(kurs,2),
                "EPS_Wachstum": eps_wachstum, "Umsatz_Wachstum": umsatz_wachstum, "OpMarge": operating_margin,
                "Forward_KGV": forward_kgv, "PEG": peg, "EV_EBITDA": ev_ebitda,
                "NetDebt_EBITDA": net_debt_ebitda
            }
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def normalize_0_100(series, higher_better=True):
    s = series.copy()
    s = s.fillna(s.median())
    min_val, max_val = s.min(), s.max()
    if max_val == min_val: return pd.Series(50, index=s.index)
    if higher_better:
        return (s - min_val) / (max_val - min_val) * 100
    else: # lower better
        return (max_val - s) / (max_val - min_val) * 100

def berechne_scores(df, regime):
    # FAKTOR 1: AI EXPOSURE 40%
    df["AI_Exposure"] = df["Ticker"].map(AI_EXPOSURE_BASE).fillna(50)

    # Regime Bonus
    if regime == 1.20:
        for t in AI_BONUS_REGIME[1.20]["HBM_DRAM"] + AI_BONUS_REGIME[1.20]["EQUIPMENT"] + AI_BONUS_REGIME[1.20]["FOUNDRY"]:
            df.loc[df["Ticker"]==t, "AI_Exposure"] += 10
    elif regime == 0.80:
        for t in AI_BONUS_REGIME[0.80]["QUALITY"]:
            df.loc[df["Ticker"]==t, "AI_Exposure"] += 10
    df["AI_Exposure"] = df["AI_Exposure"].clip(0, 100)

    # FAKTOR 2: EARNINGS MOMENTUM 25%
    eps_score = normalize_0_100(df["EPS_Wachstum"], higher_better=True)
    umsatz_score = normalize_0_100(df["Umsatz_Wachstum"], higher_better=True)
    margen_score = normalize_0_100(df["OpMarge"], higher_better=True)
    df["Earnings_Momentum"] = (eps_score*0.5 + umsatz_score*0.3 + margen_score*0.2).round(1)

    # FAKTOR 3: BEWERTUNG 20% = Wachstum / Bewertung
    # Idee: Niedriges KGV + hohes Wachstum = gut. Hohes KGV + sehr hohes Wachstum = auch gut
    kgv_score = normalize_0_100(df["Forward_KGV"], higher_better=False)
    peg_score = normalize_0_100(df["PEG"], higher_better=False)
    ev_score = normalize_0_100(df["EV_EBITDA"], higher_better=False)
    bewertung_base = (kgv_score*0.4 + peg_score*0.3 + ev_score*0.3)

    # Multiplikator: Wachstum macht teure Bewertung ok
    wachstum_mult = normalize_0_100(df["EPS_Wachstum"], higher_better=True) / 100 + 0.5
    df["Bewertung"] = (bewertung_base * wachstum_mult).clip(0,100).round(1)

    # FAKTOR 4: BILANZ 15%
    bilanz_score = normalize_0_100(df["NetDebt_EBITDA"], higher_better=False) # weniger Schulden = besser
    df["Bilanz"] = bilanz_score.round(1)

    # GESAMTSCORE
    df["Gesamtscore"] = (
        df["AI_Exposure"] * 0.40 +
        df["Earnings_Momentum"] * 0.25 +
        df["Bewertung"] * 0.20 +
        df["Bilanz"] * 0.15
    ).round(1)

    def get_rating(s):
        if s >= 75: return "STRONG BUY"
        elif s >= 60: return "BUY"
        elif s >= 45: return "HOLD"
        else: return "SELL"
    df["Rating"] = df["Gesamtscore"].apply(get_rating)
    return df

# ========== UI ==========
st.title(f"AI Infrastructure Cycle Ranking {VERSION}")
st.caption("Frage: Wer profitiert am staerksten vom AI-Capex bis Jahresende?")

with st.sidebar:
    st.header("AI Capex Szenario")
    regime = st.selectbox(
        "Regime",
        [1.20, 1.00, 0.80],
        index=0,
        format_func=lambda x: f"{x} - {'Boom' if x==1.20 else 'Normal' if x==1.00 else 'Abkuehlung'}"
    )
    st.info("Boom: +10 Punkte fuer HBM, Equipment, Foundry\nAbkuehlung: +10 Punkte fuer NVDA, MSFT, GOOGL, AVGO")

col1,col2 = st.columns([1,2])
with col1:
    st.info(
        """
        Gewichtung:
        - AI Exposure 40%
        - Earnings Momentum 25%
        - Bewertung 20%
        - Bilanz 15%

        Entfernt: Historie, FCF, Sektor-Median
        Fokus: Nur Hebel auf AI-Capex
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

st.write(f"Aktuelle Liste: {', '.join(st.session_state.aktien_liste)}")

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0); daten=[]; fehler=[]; status = st.empty()
    for i,symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol} {i+1}/{len(st.session_state.aktien_liste)}")
        data,error = get_yahoo_data(symbol)
        if data: daten.append(data)
        else: fehler.append(error)
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        time.sleep(1.5)

    if fehler:
        with st.expander(f"Fehler ({len(fehler)})"):
            for f in fehler: st.write(f)

    if len(daten)<2: st.error("Zu wenige Daten"); st.stop()

    df=pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, regime).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["EPS_Wachstum", "Umsatz_Wachstum", "OpMarge"]:
        if c in df.columns: df[c]=(df[c]*100).round(1)

    st.success(f"{len(df)} Aktien bewertet fuer AI-Capex Szenario")

    tab1,tab2 = st.tabs(["Ranking", "Details"])
    with tab1:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Rating","AI_Exposure","Earnings_Momentum","Bewertung","Bilanz","Forward_KGV","EPS_Wachstum"]], use_container_width=True, hide_index=True)
    with tab2: st.dataframe(df, use_container_width=True, hide_index=True)

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v11")
    st.download_button("Excel herunterladen", output.getvalue(), f"AI_Cycle_Ranking_v11_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
