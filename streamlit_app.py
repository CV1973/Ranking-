# ============================================
# AI Infrastructure Return Ranking v13.6
# Aenderung ggue. v13.5: KGV Quelle wird mitgeloggt
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

st.set_page_config(page_title="AI Return Ranking v13.6", layout="wide")
VERSION = "v13.6"

st.warning("Axiom: KI-Capex-Zyklus intakt bis Q4 2027. Frage: Wer hat Gewinnhebel + ist nicht ueberteuert?")

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

AI_GEWINNHEBEL_SEED = {
    "000660.KS": 100, "MU": 100, "005930.KS": 95,
    "SNDK": 90, "AVGO": 90, "TSM": 90, "ASML": 90,
    "NVDA": 85, "AMD": 80, "285A.T": 80,
    "AMAT": 75, "LRCX": 75, "KLAC": 75,
    "MSFT": 60, "GOOGL": 60, "AMZN": 60
}

if "ai_gewinnhebel" not in st.session_state:
    st.session_state.ai_gewinnhebel = dict(AI_GEWINNHEBEL_SEED)

def safe_get(d, key, default=np.nan):
    try:
        if isinstance(d, dict): return d.get(key, default) if d.get(key, default) is not None else default
        return default
    except: return default

def percentile_score(series, higher_better=True):
    s = pd.to_numeric(series, errors='coerce')
    valid = s.dropna()
    if len(valid) < 2: return pd.Series(50.0, index=s.index, dtype=float)
    rank = valid.rank(pct=True)
    if not higher_better: rank = 1 - rank
    result = pd.Series(50.0, index=s.index, dtype=float)
    result[valid.index] = rank * 100.0
    return result

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol, max_retries=2):
    fehlende = 0
    for attempt in range(max_retries):
        try:
            time.sleep(1.5 + attempt * 2)
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            if not info:
                if attempt < max_retries - 1: time.sleep(10)
                continue

            # NUR DIESER BLOCK GEAENDERT
            forward_kgv = safe_get(info, "forwardPE")
            kgv_quelle = "forward"
            if pd.isna(forward_kgv) or forward_kgv <= 0:
                forward_kgv = safe_get(info, "trailingPE")
                kgv_quelle = "trailing (Fallback)"

            peg = safe_get(info, "pegRatio")
            ev_ebitda = safe_get(info, "enterpriseToEbitda")
            fcf_yield = safe_get(info, "freeCashflow") / safe_get(info, "marketCap") if safe_get(info, "marketCap") else np.nan

            umsatz_wachstum = safe_get(info, "revenueGrowth")
            op_marge = safe_get(info, "operatingMargins")
            fcf_marge = safe_get(info, "freeCashflow") / safe_get(info, "totalRevenue") if safe_get(info, "totalRevenue") else np.nan

            for v in [forward_kgv, peg, ev_ebitda, umsatz_wachstum]:
                if pd.isna(v): fehlende += 1

            daten = {
                "Ticker": symbol, "Name": NAMEN.get(symbol, symbol),
                "Forward_KGV": forward_kgv, "KGV_Quelle": kgv_quelle, "PEG": peg, "EV_EBITDA": ev_ebitda, "FCF_Yield": fcf_yield,
                "Umsatz_Wachstum": umsatz_wachstum, "OpMarge": op_marge, "FCF_Marge": fcf_marge,
                "Datenluecken": fehlende
            }
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def berechne_scores(df):
    df["AI_Gewinnhebel"] = df["Ticker"].map(st.session_state.ai_gewinnhebel)
    if df["AI_Gewinnhebel"].isna().any():
        fehlend = df.loc[df["AI_Gewinnhebel"].isna(), "Ticker"].tolist()
        st.error(f"Interner Fehler: Kein AI_Gewinnhebel fuer {fehlend} gesetzt. Ranking abgebrochen.")
        st.stop()

    kgv_score = percentile_score(df["Forward_KGV"], higher_better=False)
    peg_score = percentile_score(df["PEG"], higher_better=False)
    ev_score = percentile_score(df["EV_EBITDA"], higher_better=False)
    fcf_score = percentile_score(df["FCF_Yield"], higher_better=True)

    df["Bewertung_Score"] = (
        kgv_score*0.15 + peg_score*0.15 + ev_score*0.05 + fcf_score*0.05
    ).round(1)

    umsatz_score = percentile_score(df["Umsatz_Wachstum"], higher_better=True)
    marge_score = percentile_score(df["OpMarge"], higher_better=True)
    fcfm_score = percentile_score(df["FCF_Marge"], higher_better=True)

    df["Gewinnqualitaet_Score"] = (
        umsatz_score*0.40 + marge_score*0.40 + fcfm_score*0.20
    ).round(1)

    df["Daten_Score"] = (100 - df["Datenluecken"] * 25).clip(0,100)

    df["Gesamtscore"] = (
        df["AI_Gewinnhebel"]*0.35 +
        df["Bewertung_Score"]*0.40 +
        df["Gewinnqualitaet_Score"]*0.20 +
        df["Daten_Score"]*0.05
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

st.info(
    "⚠️ **AI_Gewinnhebel (35% Gewicht) ist eine manuell gepflegte, subjektive Einstufung – "
    "keine aus Marktdaten berechnete Kennzahl.** Alle anderen Faktoren (Bewertung, "
    "Gewinnqualitaet, Daten) sind datengetrieben aus Yahoo Finance."
)

with st.sidebar:
    st.header("AI Gewinnhebel")
    st.caption("⚠️ Subjektiv, nicht datenbasiert – siehe Disclaimer oben.")
    hebel_df = pd.DataFrame.from_dict(
        st.session_state.ai_gewinnhebel, orient='index', columns=['Hebel']
    ).sort_values('Hebel', ascending=False)
    st.table(hebel_df)

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
        if st.button("Liste leeren"): st.session_state.aktien_liste=[]; st.rerun()

fehlende_hebel = [t for t in st.session_state.aktien_liste if t not in st.session_state.ai_gewinnhebel]

if fehlende_hebel:
    st.warning(
        f"⚠️ {len(fehlende_hebel)} Ticker ohne AI-Gewinnhebel-Einstufung: "
        f"{', '.join(fehlende_hebel)}. Bitte jeweils zuweisen, bevor das Ranking "
        f"gestartet werden kann."
    )
    for t in fehlende_hebel:
        c1, c2, c3 = st.columns([2,3,1])
        with c1:
            st.write(f"**{NAMEN.get(t, t)}** ({t})")
        with c2:
            wert = st.selectbox(
                f"AI-Gewinnhebel fuer {t}",
                options=list(range(0,101,5)),
                index=10,
                key=f"hebel_select_{t}",
                label_visibility="collapsed"
            )
        with c3:
            if st.button("Setzen", key=f"hebel_confirm_{t}"):
                st.session_state.ai_gewinnhebel[t] = wert
                st.rerun()

ranking_gesperrt = len(fehlende_hebel) > 0

if st.button("Ranking starten", type="primary", disabled=ranking_gesperrt):
    progress = st.progress(0); daten=[]; fehler=[]; status = st.empty()
    for i,symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol} {i+1}/{len(st.session_state.aktien_liste)}")
        data,error = get_yahoo_data(symbol)
        if data: daten.append(data)
        else:
            fehler.append(error)
            st.error(f"Ticker nicht gefunden: {symbol}")
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        time.sleep(1.5)

    if len(daten)<2: st.error("Zu wenige gueltige Daten zum Ranking"); st.stop()

    df=pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "KGV_Quelle"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))
    df["Umsatz_Wachstum"] = (df["Umsatz_Wachstum"]*100).round(1)
    df["OpMarge"] = (df["OpMarge"]*100).round(1)
    df["FCF_Yield"] = (df["FCF_Yield"]*100).round(1)
    df["FCF_Marge"] = (df["FCF_Marge"]*100).round(1)

    st.success(f"{len(df)} Aktien bewertet")

    tab1,tab2,tab3 = st.tabs(["Transparenz", "Ranking", "Export"])
    with tab1:
        anzeige_df1 = df.rename(columns={"AI_Gewinnhebel": "AI_Gewinnhebel (subjektiv)"})
        st.dataframe(
            anzeige_df1[["Ticker","Name","Gesamtscore","Rating","AI_Gewinnhebel (subjektiv)","Bewertung_Score","Gewinnqualitaet_Score","Daten_Score","KGV_Quelle","Datenluecken"]],
            use_container_width=True, hide_index=True
        )
    with tab2:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Rating","Forward_KGV","KGV_Quelle","PEG","EV_EBITDA","Umsatz_Wachstum"]], use_container_width=True, hide_index=True)
    with tab3:
        output=io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v13.6")
        st.download_button("Excel herunterladen", output.getvalue(), f"AI_Return_Ranking_v13.6_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
