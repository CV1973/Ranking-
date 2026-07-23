# ============================================
# AI Infrastructure Cycle Ranking v12.0
# 3 Säulen + 1 Modifikator + 1 Filter
# Prämisse: KI-Capex-Zyklus intakt bis Q4 2027
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

st.set_page_config(page_title="AI Cycle Ranking v12.0", layout="wide")
VERSION = "v12.0"

st.warning("Modell-Annahme: KI-Capex-Zyklus intakt bis Q4 2027. Dieses Ranking ist bedingt auf diese These.")

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

SEKTOR = {
    "NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "TSM": "Foundry",
    "MU": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher", "SNDK": "Speicher",
    "MSFT": "Hyperscaler", "GOOGL": "Hyperscaler", "AMZN": "Hyperscaler"
}

# SAEUlE 2: THESE - Manuelle Felder
AI_EXPOSURE = {
    "NVDA": 100, "000660.KS": 100, "AVGO": 95, "TSM": 95, "MU": 90, "ASML": 90,
    "005930.KS": 85, "AMD": 85, "AMAT": 80, "LRCX": 80, "KLAC": 80,
    "285A.T": 70, "SNDK": 65, "MSFT": 60, "GOOGL": 60, "AMZN": 60
}

# Zyklusdaempfung: 100 = kein Boom-Bust, 0 = extrem zyklisch
ZYKLUSDAEMPFUNG = {
    "NVDA": 30, "AVGO": 40, "TSM": 50, "ASML": 45, "AMD": 35, "MSFT": 80, "GOOGL": 80, "AMZN": 75,
    "MU": 85, "000660.KS": 90, "005930.KS": 80, "SNDK": 75, "285A.T": 70, # Memory hat Langfristvertraege
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

            # SAEUlE 1: FUNDAMENTAL - nur 3 KPIs
            forward_kgv = safe_get(info, "forwardPE")
            umsatz_wachstum = safe_get(info, "revenueGrowth") # KEIN EPS CAGR mehr
            op_marge = safe_get(info, "operatingMargins")

            # MODIFIKATOR: ATH Abstand
            kurs = safe_get(info, "currentPrice")
            ath = safe_get(info, "fiftyTwoWeekHigh")
            ath_abstand = (ath - kurs) / ath * 100 if pd.notna(ath) and pd.notna(kurs) and ath > 0 else np.nan

            # FILTER: BILANZ
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
    # BUGFIX 2: TSM nicht mit sich selbst vergleichen. Foundry -> Equipment
    scores = []
    for idx, row in df.iterrows():
        sektor = row["Sektor"]
        if sektor == "Foundry": sektor = "Equipment" # TSM Vergleichsgruppe

        sektor_df = df[df["Sektor"]==sektor]
        if len(sektor_df) < 2: sektor_df = df # Fallback global

        wert = row[spalte]
        if pd.isna(wert): scores.append(50); continue

        median = sektor_df[spalte].median()
        if pd.isna(median) or median == 0: scores.append(50); continue

        ratio = wert / median
        if not higher_better: ratio = 1/ratio if ratio > 0 else 1.0

        # Z-Score auf 0-100
        mean, std = np.log(sektor_df[spalte].dropna()).mean(), np.log(sektor_df[spalte].dropna()).std()
        if std == 0: scores.append(50)
        else:
            z = (np.log(wert) - mean) / (std * 2) if pd.notna(wert) and wert > 0 else 0
            score = (z.clip(-1,1) + 1) * 50
            scores.append(score)
    return pd.Series(scores, index=df.index)

def berechne_scores(df, horizont):
    # GEWICHTE HORIZONTABHAENGIG - BUGFIX 1
    if horizont == "6M":
        w_fund, w_these, w_mod = 0.35, 0.40, 0.25 # Kurz: mehr Momentum/ATH
    else: # 12M
        w_fund, w_these, w_mod = 0.40, 0.45, 0.15 # Lang: mehr Fundamental/These

    # SAEUlE 1: FUNDAMENTAL 40%
    kgv_score = normalize_sektor(df, "Forward_KGV", higher_better=False)
    wachstum_score = normalize_sektor(df, "Umsatz_Wachstum", higher_better=True)
    qualitaet_score = normalize_sektor(df, "OpMarge", higher_better=True)
    df["Fundamental_Score"] = (kgv_score*0.4 + wachstum_score*0.3 + qualitaet_score*0.3).round(1)

    # SAEUlE 2: THESE 45%
    df["AI_Exposure"] = df["Ticker"].map(AI_EXPOSURE).fillna(50)
    df["Zyklusdaempfung"] = df["Ticker"].map(ZYKLUSDAEMPFUNG).fillna(50)
    these_raw = df["AI_Exposure"]*0.7 + df["Zyklusdaempfung"]*0.3
    # BUGFIX 3: Regime Multiplikator VOR clip
    these_raw = these_raw * 1.1 # Kopfraum fuer Bonus
    df["These_Score"] = these_raw.clip(0,100).round(1)

    # MODIFIKATOR: ATH ABSTAND
    mod = 1.0 + (df["ATH_Abstand_%"].fillna(0) / 100) * 0.3
    df["ATH_Modifikator"] = np.where(df["Fundamental_Score"] > 50, mod, 1.0).round(2)

    # GESAMTSCORE
    df["Gesamtscore_Roh"] = (
        df["Fundamental_Score"] * w_fund +
        df["These_Score"] * w_these
    ) * df["ATH_Modifikator"]

    # FILTER: BILANZ DECKEL
    def get_rating(row):
        score = row["Gesamtscore_Roh"]
        if row["NetDebt_EBITDA"] > 3: # Sicherheitsbremse
            if score >= 75: return "BUY" # Deckel
        if score >= 75: return "STRONG BUY"
        elif score >= 60: return "BUY"
        elif score >= 45: return "HOLD"
        else: return "SELL"
    df["Rating"] = df.apply(get_rating, axis=1)
    df["Gesamtscore"] = df["Gesamtscore_Roh"].round(1)
    return df

# ========== UI ==========
st.title(f"AI Infrastructure Cycle Ranking {VERSION}")
st.caption("3 Saeulen + 1 Modifikator + 1 Filter")

horizont = st.radio("Anlagehorizont", ["6M", "12M"], horizontal=True)

with st.sidebar:
    st.header("These Gewichte")
    st.write("Fundamental: 40% | These: 45% | ATH Mod: 15% bei 12M")
    st.write("Fundamental: 35% | These: 40% | ATH Mod: 25% bei 6M")

col1,col2 = st.columns([1,2])
with col1:
    st.info(
        """
        Saeule 1 Fundamental 40%:
        - Forward KGV sektor-relativ
        - Umsatzwachstum yoy
        - Operating Margin

        Saeule 2 These 45%:
        - AI Exposure manuell
        - Zyklusdaempfung manuell

        Modifikator: ATH Abstand
        Filter: NetDebt/EBITDA > 3 = kein STRONG BUY
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
        if c not in ["Ticker", "Name", "Sektor"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, horizont).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    df["Umsatz_Wachstum"] = (df["Umsatz_Wachstum"]*100).round(1)
    df["OpMarge"] = (df["OpMarge"]*100).round(1)
    df["ATH_Abstand_%"] = df["ATH_Abstand_%"].round(1)

    st.success(f"{len(df)} Aktien bewertet")

    tab1,tab2,tab3 = st.tabs(["Transparenz", "Ranking", "Details"])
    with tab1: # TRANSPARENZ-ANFORDERUNG
        st.dataframe(df[["Ticker","Name","Fundamental_Score","These_Score","ATH_Modifikator","Gesamtscore","Rating","NetDebt_EBITDA"]], use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Rating","Fundamental_Score","These_Score","ATH_Abstand_%","Forward_KGV","Umsatz_Wachstum"]], use_container_width=True, hide_index=True)
    with tab3: st.dataframe(df, use_container_width=True, hide_index=True)

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v12")
    st.download_button("Excel herunterladen", output.getvalue(), f"AI_Cycle_Ranking_v12_{horizont}_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
