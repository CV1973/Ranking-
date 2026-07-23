# ============================================
# Halbleiter & KI Aktien Ranking v10.6a
# 12 Monate Focus | Fundamental Cycle Adjusted
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

st.set_page_config(page_title="Halbleiter Ranking v10.6a", layout="wide")
VERSION = "v10.6a"

if "aktien_liste" not in st.session_state:
    st.session_state.aktien_liste = [
        "MU", "SNDK", "NVDA", "AMD", "AVGO", "TSM",
        "005930.KS", "000660.KS", "285A.T", "ASML",
        "AMAT", "LRCX", "KLAC", "MSFT", "GOOGL"
    ]

NAMEN = {
    "MU": "Micron", "SNDK": "SanDisk", "NVDA": "Nvidia", "AMD": "AMD", "AVGO": "Broadcom", "TSM": "TSMC",
    "005930.KS": "Samsung", "000660.KS": "SK Hynix", "285A.T": "Kioxia",
    "ASML": "ASML", "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA",
    "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon"
}

SEKTOR = {
    "NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "TSM": "Foundry",
    "MU": "Speicher", "SNDK": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher",
    "MSFT": "Hyperscaler", "GOOGL": "Hyperscaler", "AMZN": "Hyperscaler"
}

SEKTOR_FALLBACK = {
    "Foundry": "Equipment", "KI_Chip": "Equipment",
    "Speicher": "Equipment", "Equipment": "Gesamtmarkt", "Hyperscaler": "Gesamtmarkt"
}

AI_INFRA_BASIS = {
    "KI_Chip": 1.25, "Speicher": 1.25, "Equipment": 1.20, "Foundry": 1.20, "Hyperscaler": 0.92
}
AI_CAP = 1.35

AI_INFRA_INFO = """
### AI-Infrastruktur Narrativ Faktor

**1.20 AI-Boom**: Hyperscaler Capex ↑↑, HBM/GPU Engpass
**1.00 Neutral**: Capex stabil, normale Nachfrage
**0.80 Abkühlung**: Capex ↓, ROI-Fragen

Gewichtung:
KI Chip 1.25 | Speicher 1.25 | Equipment 1.20 | Foundry 1.20 | Hyperscaler 0.92
Max-Effekt gecappt bei 1.35
"""

KPIS = ["Forward KGV", "EV/EBITDA", "Umsatztrend", "Gewinntrend", "Bruttomarge", "Operating Margin", "FCF-Marge"]

KPI_QUALITAETS_GEWICHT = {
    "Forward KGV": 0.15, "EV/EBITDA": 0.15, "Umsatztrend": 0.20,
    "Gewinntrend": 0.20, "Bruttomarge": 0.10, "Operating Margin": 0.10, "FCF-Marge": 0.10
}

def get_gewichte():
    # 12 Monate Chance-Risiko
    base = {
        "Bewertung": 0.20,
        "Wachstum": 0.35, # Haupttreiber in 12M
        "Qualität": 0.30,
        "AI_Narrativ": 0.15 # Nicht hoeher
    }
    return {
        "Forward KGV": base["Bewertung"] * 0.5, "EV/EBITDA": base["Bewertung"] * 0.5,
        "Umsatztrend": base["Wachstum"] * 0.5, "Gewinntrend": base["Wachstum"] * 0.5,
        "Bruttomarge": base["Qualität"] * 0.33, "Operating Margin": base["Qualität"] * 0.33, "FCF-Marge": base["Qualität"] * 0.34,
        "AI_Infrastruktur": base["AI_Narrativ"]
    }

def safe_get(d, key, default=np.nan):
    try:
        if isinstance(d, dict): return d.get(key, default) if d.get(key, default) is not None else default
        return default
    except: return default

def get_row_safe(df, keys):
    if df is None or df.empty: return pd.Series(dtype=float)
    for key in keys:
        if key in df.index:
            values = df.loc[key].dropna()
            if len(values) > 0: return values
    return pd.Series(dtype=float)

def berechne_cagr(series):
    try:
        if len(series) < 2: return np.nan
        start, ende = series.iloc[-1], series.iloc[0]
        if start > 0 and ende > 0:
            jahre = len(series)-1
            return (ende/start)**(1/jahre)-1
        if len(series) >= 2:
            return (series.iloc[0] / series.iloc[1]) - 1 if series.iloc[1]!= 0 else np.nan
        return np.nan
    except: return np.nan

def get_rating(score, daten_qualitaet, fehlende_anzahl):
    if score >= 78 and daten_qualitaet >= 80 and fehlende_anzahl < 2:
        return "STRONG BUY"
    elif score >= 65: return "BUY"
    elif score >= 48: return "HOLD"
    else: return "SELL"

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol, max_retries=2):
    fehlende = []
    for attempt in range(max_retries):
        try:
            time.sleep(1.5 + attempt * 2)
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            if not info:
                if attempt < max_retries - 1: time.sleep(10)
                continue

            financials = ticker.financials
            cashflow = ticker.cashflow
            history = ticker.history(period="5d")
            sektor = SEKTOR.get(symbol, "Unbekannt")

            kurs = safe_get(info, "currentPrice")
            if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
            if pd.isna(kurs): return None, f"{symbol}: Kein Kurs"

            marketcap = safe_get(info, "marketCap")
            if pd.isna(marketcap): return None, f"{symbol}: Keine Marketcap"

            kgv = safe_get(info, "forwardPE")
            if pd.isna(kgv): kgv = safe_get(info, "trailingPE")
            if pd.notna(kgv) and kgv <= 0: kgv = np.nan
            if pd.isna(kgv): fehlende.append("KGV")

            ev_ebitda = safe_get(info, "enterpriseToEbitda")
            if pd.isna(ev_ebitda): fehlende.append("EV/EBITDA")

            revenue_series = get_row_safe(financials, ["Total Revenue", "Revenue"])
            umsatztrend = safe_get(info, "revenueGrowth")
            if pd.isna(umsatztrend): umsatztrend = berechne_cagr(revenue_series)
            if pd.isna(umsatztrend): fehlende.append("Umsatz")

            eps_series = get_row_safe(financials, ["Diluted EPS", "Basic EPS"])
            gewinntrend = safe_get(info, "earningsGrowth")
            if pd.isna(gewinntrend): gewinntrend = berechne_cagr(eps_series)
            if pd.isna(gewinntrend): fehlende.append("Gewinn")

            gross_margin = safe_get(info, "grossMargins")
            if pd.isna(gross_margin): fehlende.append("GM")

            operating_margin = safe_get(info, "operatingMargins")
            if pd.isna(operating_margin): fehlende.append("OM")

            # FCF 3-Jahres-Durchschnitt
            fcf_series = get_row_safe(cashflow, ["Free Cash Flow", "FreeCashFlow"])
            revenue_series_hist = get_row_safe(financials, ["Total Revenue", "Revenue"])
            fcf_margins = []
            for i in range(min(3, len(fcf_series))):
                if i < len(revenue_series_hist):
                    fcf = fcf_series.iloc[i]
                    rev = revenue_series_hist.iloc[i]
                    if pd.notna(fcf) and pd.notna(rev) and rev!= 0:
                        fcf_margins.append(fcf / rev)
            fcf_margin = np.mean(fcf_margins) if fcf_margins else np.nan
            if pd.isna(fcf_margin): fehlende.append("FCF")

            daten = {
                "Ticker": symbol, "Name": NAMEN.get(symbol, symbol), "Sektor": sektor,
                "Kurs": round(kurs,2), "Marktkapitalisierung Mrd": round(marketcap/1e9, 1),
                "Forward KGV": kgv, "EV/EBITDA": ev_ebitda, "Umsatztrend": umsatztrend, "Gewinntrend": gewinntrend,
                "Bruttomarge": gross_margin, "Operating Margin": operating_margin, "FCF-Marge": fcf_margin,
                "Fehlt": ", ".join(fehlende) if fehlende else "vollstaendig"
            }
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def calc_sector_medians(df):
    medians = {}; gesamt_median = {kpi: df[kpi].median() for kpi in KPIS}
    for sektor in df["Sektor"].unique():
        sektor_df = df[df["Sektor"] == sektor]
        if len(sektor_df) >= 2: medians[sektor] = {kpi: sektor_df[kpi].median() for kpi in KPIS}
        else:
            fallback = SEKTOR_FALLBACK.get(sektor, "Gesamtmarkt")
            if fallback in df["Sektor"].values and len(df[df["Sektor"]==fallback]) >= 2:
                medians[sektor] = {kpi: df[df["Sektor"]==fallback][kpi].median() for kpi in KPIS}
            else: medians[sektor] = gesamt_median
    return medians

def normalize_kpi(df, spalte, medians, typ="log"):
    werte = []
    for idx, row in df.iterrows():
        wert, sektor = row[spalte], row["Sektor"]
        median = medians.get(sektor,{}).get(spalte,np.nan)
        if pd.isna(wert) or pd.isna(median) or median == 0:
            rel = 0.0
        else:
            ratio = wert / median
            if typ == "log":
                ratio = 1 / ratio if spalte in ["Forward KGV", "EV/EBITDA"] and ratio > 0 else ratio
                rel = np.log(ratio) if ratio > 0 else -1.0
            else: # linear fuer Wachstum
                rel = ratio - 1.0
        werte.append(rel)

    s = pd.Series(werte, index=df.index)
    mean, std = s.mean(), s.std()
    if std == 0: return pd.Series(50, index=df.index)
    z = (s - mean) / (std * 2)
    return (z.clip(-1, 1) + 1) * 50

def get_ai_infrastruktur_score(df, global_faktor):
    scores = []
    for idx,row in df.iterrows():
        basis = AI_INFRA_BASIS.get(row["Sektor"], 1.0)
        faktor = min(basis * global_faktor, AI_CAP)
        score = (faktor - 0.72) / (AI_CAP - 0.72) * 100
        scores.append(max(0, min(100, score)))
    return pd.Series(scores, index=df.index)

def berechne_scores(df, global_ai_faktor):
    medians = calc_sector_medians(df)

    # Datenqualitaet VOR Imputation
    df_copy_vor_imputation = df.copy()
    qualitaet_score = 0
    for kpi, gewicht in KPI_QUALITAETS_GEWICHT.items():
        hat_daten = (~df_copy_vor_imputation[kpi].isna()).astype(int)
        qualitaet_score += hat_daten * gewicht
    df["Datenqualitaet"] = (qualitaet_score * 100).round(0)
    df["Fehlende Anzahl"] = df_copy_vor_imputation.isna().sum(axis=1)

    # ERST DANN Imputation
    for kpi in KPIS:
        for idx,row in df.iterrows():
            if pd.isna(row[kpi]):
                median = medians.get(row["Sektor"],{}).get(kpi,np.nan)
                if pd.notna(median): df.loc[idx,kpi]=median

    norm = pd.DataFrame(index=df.index)
    norm["Forward KGV"] = normalize_kpi(df, "Forward KGV", medians, typ="log")
    norm["EV/EBITDA"] = normalize_kpi(df, "EV/EBITDA", medians, typ="log")
    norm["Umsatztrend"] = normalize_kpi(df, "Umsatztrend", medians, typ="linear")
    norm["Gewinntrend"] = normalize_kpi(df, "Gewinntrend", medians, typ="linear")
    norm["Bruttomarge"] = normalize_kpi(df, "Bruttomarge", medians, typ="log")
    norm["Operating Margin"] = normalize_kpi(df, "Operating Margin", medians, typ="log")
    norm["FCF-Marge"] = normalize_kpi(df, "FCF-Marge", medians, typ="log")
    norm["AI_Infrastruktur"] = get_ai_infrastruktur_score(df, global_ai_faktor)
    df["AI_Infrastruktur"] = norm["AI_Infrastruktur"].round(1)

    gewichte = get_gewichte()
    scores = [sum(norm.loc[idx,kpi]*w for kpi,w in gewichte.items() if kpi in norm.columns) for idx in df.index]
    df["Gesamtscore"] = pd.Series(scores, index=df.index).round(1)

    # Datenqualitaet-Strafe erhoeht: 0.6 + 0.4*DQ
    df["Bereinigter Score"] = (df["Gesamtscore"] * (0.6 + 0.4 * df["Datenqualitaet"]/100)).round(1)
    df["Rating"] = df.apply(lambda x: get_rating(x["Bereinigter Score"], x["Datenqualitaet"], x["Fehlende Anzahl"]), axis=1)
    return df

# ========== UI ==========
st.title(f"Halbleiter & KI Aktien Ranking {VERSION}")
st.caption("12 Monate Focus | Fundamental Cycle Adjusted")

with st.sidebar:
    st.header("AI-Infrastruktur Narrativ")
    st.info(AI_INFRA_INFO)
    faktor_auswahl = st.selectbox("Regime-Faktor", [1.20, 1.10, 1.00, 0.90, 0.80], index=2,
                                  format_func=lambda x: f"{x} - {'Boom' if x>=1.1 else 'Neutral' if x==1.0 else 'Abkuehlung'}")

col1,col2 = st.columns([1,2])
with col1:
    st.info(
        """
        **Anlagehorizont: 12 Monate**
        **Review: Quartalsweise**

        Dieses Ranking bewertet das Chance-Risiko-Verhaeltnis
        im aktuellen AI-Infrastrukturzyklus.

        Fokus 12M:
        - Gewinn- und Umsatzrevisionen 35%
        - Margenqualitaet + FCF 30%
        - Bewertung 20%
        - AI-Capex Rueckenwind 15%

        Kein Momentum-Faktor.
        Keine Trading-Signale.
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

st.write(f"**Aktuelle Liste:** {', '.join(st.session_state.aktien_liste)}")

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0); daten=[]; fehler=[]; status = st.empty()
    for i,symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol} {i+1}/{len(st.session_state.aktien_liste)}")
        data,error = get_yahoo_data(symbol)
        if data: daten.append(data)
        else: fehler.append(error)
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        time.sleep(1.5)
        if (i + 1) % 5 == 0: time.sleep(5)

    if fehler:
        with st.expander(f"Fehler ({len(fehler)})"):
            for f in fehler: st.write(f)

    if len(daten)<2: st.error("Zu wenige Daten"); st.stop()

    df=pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "Sektor", "Fehlt"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, faktor_auswahl).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["Umsatztrend", "Gewinntrend", "Bruttomarge", "Operating Margin", "FCF-Marge"]:
        if c in df.columns: df[c]=(df[c]*100).round(2)

    st.success(f"{len(df)} Aktien bewertet fuer 12 Monate")

    a,b,c,d = st.columns(4)
    with a: st.metric("STRONG BUY", len(df[df["Rating"]=="STRONG BUY"]))
    with b: st.metric("BUY", len(df[df["Rating"]=="BUY"]))
    with c: st.metric("HOLD", len(df[df["Rating"]=="HOLD"]))
    with d: st.metric("SELL", len(df[df["Rating"]=="SELL"]))

    tab1,tab2,tab3 = st.tabs(["Ranking", "Details", "Export"])
    with tab1:
        st.dataframe(df[["Datum","Ticker","Name","Sektor","Gesamtscore","Bereinigter Score","Rating","AI_Infrastruktur","Datenqualitaet","Forward KGV","EV/EBITDA","Umsatztrend","Gewinntrend","Fehlt"]], use_container_width=True, hide_index=True)
    with tab2: st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output=io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v10.6a")
        st.download_button("Excel herunterladen", output.getvalue(), f"KI_Ranking_v10.6a_{datetime.now().strftime('%Y-%m-%d')}_12M.xlsx")
