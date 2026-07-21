# ============================================
# Halbleiter & KI Aktien Ranking v7.50
# Hard Fail bei fehlenden KPIs + Manuelle Suche
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

st.set_page_config(page_title="Halbleiter Ranking v7.50", layout="wide")

VERSION = "v7.50"

# Session State für manuelle Liste
if 'aktien_liste' not in st.session_state:
    st.session_state.aktien_liste = [
        "MU", "SNDK", "NVDA", "AMD", "AVGO", "TSM",
        "005930.KS", "000660.KS", "285A.T", "ASML",
        "AMAT", "LRCX", "KLAC"
    ]

namen = {
    "MU": "Micron", "SNDK": "SanDisk", "NVDA": "Nvidia", "AMD": "AMD",
    "AVGO": "Broadcom", "TSM": "TSMC", "005930.KS": "Samsung",
    "000660.KS": "SK Hynix", "285A.T": "Kioxia", "ASML": "ASML",
    "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA"
}

SEKTOR = {
    "NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "TSM": "Foundry",
    "MU": "Speicher", "SNDK": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher"
}

AI_EXPOSURE = {"NVDA":100, "AVGO":95, "000660.KS":90, "TSM":90, "MU":85, "AMD":80, "005930.KS":80, "ASML":80, "KLAC":75, "LRCX":75, "AMAT":75, "SNDK":70, "285A.T":60}
STRAT_BEDEUTUNG = {"ASML":100, "TSM":100, "NVDA":95, "AMAT":90, "LRCX":90, "KLAC":90, "AVGO":85, "000660.KS":80, "MU":80, "AMD":75, "005930.KS":75, "SNDK":70, "285A.T":60}
SPEICHER_AKTIEN = ["MU", "SNDK", "000660.KS", "285A.T", "005930.KS"]
KI_INFRA = ["NVDA", "AVGO", "ASML", "TSM", "AMAT", "LRCX", "KLAC"]

# WICHTIGE KPIs die vorhanden sein müssen
REQUIRED_KPIS = ["Forward KGV", "EV/EBITDA", "Umsatz CAGR 5Y", "EPS CAGR 5Y", "Bruttomarge", "Operating Margin"]

def get_gewichte_sektor(horizont, sektor):
    if horizont == 6:
        if sektor == "Equipment": base = {"Bewertung":0.20, "Zyklus":0.30, "Wachstum":0.10, "Qualität":0.20, "Moat":0.20}
        elif sektor == "Speicher": base = {"Bewertung":0.40, "Zyklus":0.40, "Wachstum":0.05, "Qualität":0.05, "Moat":0.10}
        elif sektor == "KI_Chip": base = {"Bewertung":0.20, "Zyklus":0.20, "Wachstum":0.25, "Qualität":0.15, "Moat":0.30}
        else: base = {"Bewertung":0.25, "Zyklus":0.30, "Wachstum":0.15, "Qualität":0.15, "Moat":0.25}
    elif horizont == 12:
        if sektor == "Equipment": base = {"Bewertung":0.15, "Zyklus":0.20, "Wachstum":0.15, "Qualität":0.25, "Moat":0.35}
        elif sektor == "Speicher": base = {"Bewertung":0.35, "Zyklus":0.30, "Wachstum":0.10, "Qualität":0.10, "Moat":0.15}
        elif sektor == "KI_Chip": base = {"Bewertung":0.15, "Zyklus":0.15, "Wachstum":0.30, "Qualität":0.20, "Moat":0.40}
        else: base = {"Bewertung":0.20, "Zyklus":0.25, "Wachstum":0.20, "Qualität":0.20, "Moat":0.35}
    else: # 36M
        if sektor == "Equipment": base = {"Bewertung":0.10, "Zyklus":0.10, "Wachstum":0.20, "Qualität":0.30, "Moat":0.50}
        elif sektor == "Speicher": base = {"Bewertung":0.20, "Zyklus":0.20, "Wachstum":0.20, "Qualität":0.20, "Moat":0.20}
        elif sektor == "KI_Chip": base = {"Bewertung":0.10, "Zyklus":0.10, "Wachstum":0.30, "Qualität":0.20, "Moat":0.50}
        else: base = {"Bewertung":0.15, "Zyklus":0.15, "Wachstum":0.25, "Qualität":0.25, "Moat":0.45}

    summe = sum(base.values())
    base = {k: v/summe for k,v in base.items()}
    return {
        "Forward KGV": base["Bewertung"] * 0.4, "EV/EBITDA": base["Bewertung"] * 0.4, "PEG": base["Bewertung"] * 0.2,
        "Zykluswirkung": base["Zyklus"],
        "Umsatz CAGR 5Y": base["Wachstum"] * 0.5, "EPS CAGR 5Y": base["Wachstum"] * 0.3, "EPS Revision 3M": base["Wachstum"] * 0.2,
        "Bruttomarge": base["Qualität"] * 0.25, "Operating Margin": base["Qualität"] * 0.25, "FCF Marge": base["Qualität"] * 0.25,
        "FCF Positiv": base["Qualität"] * 0.15, "Net Debt/EBITDA": base["Qualität"] * 0.10,
        "Moat Score": base["Moat"] * 0.5, "AI Exposure": base["Moat"] * 0.3, "Strategische Bedeutung": base["Moat"] * 0.2
    }

def safe_get(d, key, default=np.nan):
    try: return d.get(key, default)
    except: return default

def get_cagr(financials, metric_name):
    try:
        if financials is None or financials.empty: return np.nan
        series = financials.loc[metric_name].dropna()
        if len(series) < 3: return np.nan
        start = series.iloc[-1]
        ende = series.iloc[0]
        jahre = len(series) - 1
        if start <= 0: return np.nan
        return (ende / start) ** (1/jahre) - 1
    except:
        return np.nan

def calc_moat(info, financials, symbol):
    gm = safe_get(info, "grossMargins", np.nan) * 100
    om = safe_get(info, "operatingMargins", np.nan) * 100
    marketcap = safe_get(info, "marketCap", np.nan)
    if pd.isna(gm) or pd.isna(om) or pd.isna(marketcap): return np.nan

    market_score = np.clip(np.log10(marketcap) * 8, 0, 100)
    tech_score = gm * 0.6 + om * 0.4
    margin_score = gm * 0.5 + om * 0.5
    base_score = market_score*0.4 + tech_score*0.3 + margin_score*0.3
    return np.clip(base_score * 0.7 + STRAT_BEDEUTUNG.get(symbol, 50) * 0.3, 0, 100)

def get_zyklus_score(symbol, info, financials):
    sektor = SEKTOR.get(symbol, "Foundry")
    eps_growth = get_cagr(financials, "Diluted EPS")
    if pd.isna(eps_growth): return np.nan
    eps_score = np.clip((eps_growth * 100 + 20) * 2, 0, 100)

    fwd_pe = safe_get(info, "forwardPE", np.nan)
    if pd.isna(fwd_pe): return np.nan

    if sektor == "Equipment": bewertung_score = np.clip((40 - fwd_pe) * 3, 0, 100)
    elif sektor == "Speicher": bewertung_score = np.clip((12 - fwd_pe) * 8, 0, 100)
    else: bewertung_score = np.clip((30 - fwd_pe) * 5, 0, 100)

    nachfrage = 80 if symbol in KI_INFRA else 70 if symbol in SPEICHER_AKTIEN else 50
    zyklus = eps_score*0.4 + 50*0.3 + nachfrage*0.2 + bewertung_score*0.1
    return np.clip(zyklus, 0, 100)

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol):
    try:
        time.sleep(1)
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        financials = ticker.financials
        cashflow = ticker.cashflow
        history = ticker.history(period="1d")

        kurs = safe_get(info, "currentPrice")
        if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
        marketcap = safe_get(info, "marketCap")
        if pd.isna(kurs) or pd.isna(marketcap): return None, f"{symbol}: Kurs oder Marketcap fehlt"

        forward_kgv = safe_get(info, "forwardPE")
        ev_ebitda = safe_get(info, "enterpriseToEbitda")
        if pd.isna(forward_kgv) or pd.isna(ev_ebitda): return None, f"{symbol}: Bewertung fehlt"

        cagr_rev = get_cagr(financials, "Total Revenue")
        cagr_eps = get_cagr(financials, "Diluted EPS")
        if pd.isna(cagr_rev) or pd.isna(cagr_eps): return None, f"{symbol}: Wachstum fehlt"

        gm = safe_get(info, "grossMargins")
        om = safe_get(info, "operatingMargins")
        if pd.isna(gm) or pd.isna(om): return None, f"{symbol}: Margen fehlen"

        fcf, revenue = np.nan, np.nan
        try:
            if cashflow is not None and not cashflow.empty: fcf = cashflow.loc["Free Cash Flow"].iloc[0]
            if financials is not None and not financials.empty: revenue = financials.loc["Total Revenue"].iloc[0]
        except: pass
        fcf_marge = (fcf / revenue) if (pd.notna(fcf) and pd.notna(revenue) and revenue!= 0) else np.nan

        debt = safe_get(info, "totalDebt", 0)
        cash = safe_get(info, "totalCash", 0)
        ebitda = safe_get(info, "ebitda")
        net_debt_ebitda = (debt - cash) / ebitda if pd.notna(ebitda) and ebitda!= 0 else np.nan

        moat = calc_moat(info, financials, symbol)
        if pd.isna(moat): return None, f"{symbol}: Moat Score fehlt"

        data = {
            "Ticker": symbol, "Sektor": SEKTOR.get(symbol, "Other"),
            "Name": safe_get(info, "shortName", namen.get(symbol, symbol)),
            "Marktkapitalisierung Mrd": round(marketcap / 1e9, 1),
            "Kurs": round(kurs, 2),
            "Forward KGV": forward_kgv, "EV/EBITDA": ev_ebitda, "PEG": safe_get(info, "pegRatio"),
            "Umsatz CAGR 5Y": cagr_rev, "EPS CAGR 5Y": cagr_eps, "EPS Revision 3M": 50.0,
            "Bruttomarge": gm, "Operating Margin": om, "FCF Marge": fcf_marge,
            "FCF Positiv": 100 if pd.notna(fcf) and fcf > 0 else 0,
            "Net Debt/EBITDA": net_debt_ebitda,
            "Moat Score": moat, "AI Exposure": AI_EXPOSURE.get(symbol, 50),
            "Strategische Bedeutung": STRAT_BEDEUTUNG.get(symbol, 50)
        }
        return data, None
    except Exception as e:
        return None, f"{symbol}: {str(e)}"

def berechne_scores(df, horizont):
    scores = []
    for idx, row in df.iterrows():
        gewichte = get_gewichte_sektor(horizont, row["Sektor"])
        niedrig = ["Forward KGV", "EV/EBITDA", "PEG", "Net Debt/EBITDA"]
        def norm(x, besser="hoch"):
            x = pd.to_numeric(x, errors='coerce')
            if x.notna().sum() < 2: return pd.Series(50.0, index=x.index)
            lo, hi = x.quantile(0.10), x.quantile(0.90)
            if pd.isna(lo) or pd.isna(hi) or hi == lo: return pd.Series(50.0, index=x.index)
            if besser == "niedrig": return (1 - ((x.clip(lo, hi) - lo) / (hi - lo))) * 100
            else: return ((x.clip(lo, hi) - lo) / (hi - lo)) * 100
        score = 0.0
        for k, w in gewichte.items():
            if k in df.columns:
                einzel = norm(df[k], "niedrig" if k in niedrig else "hoch")
                score += einzel.loc[idx] * w
        scores.append(score)
    df["Gesamtscore"] = pd.Series(scores).round(1)
    df["Bewertung"] = df["Gesamtscore"].apply(lambda x: "🟢 attraktiv" if x >= 75 else "🟡 fair" if x >= 50 else "🔴 teuer")
    return df

# ========== UI ==========
st.title(f"Halbleiter & KI Aktien Ranking {VERSION}")
st.caption("Nur Aktien mit vollständigen Daten werden gerankt")

# FIX: Dropdown statt Slider
col1, col2 = st.columns([1,2])
with col1:
    horizont = st.selectbox("Anlagehorizont", [6, 12, 36], format_func=lambda x: f"{x} Monate")

with col2:
    # FIX: Manuelle Suche wieder drin
    such_ticker = st.text_input("Ticker hinzufügen", placeholder="z.B. AMD, INTC, QCOM")
    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("Hinzufügen"):
            if such_ticker.upper() not in st.session_state.aktien_liste:
                st.session_state.aktien_liste.append(such_ticker.upper())
                st.rerun()
    with col_clear:
        if st.button("Liste leeren"):
            st.session_state.aktien_liste = []
            st.rerun()

st.write(f"**Aktuelle Liste:** {', '.join(st.session_state.aktien_liste)}")

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0)
    daten = []
    fehler_log = []

    for i, symbol in enumerate(st.session_state.aktien_liste):
        st.text(f"Lade {symbol}... {i+1}/{len(st.session_state.aktien_liste)}")
        data, fehler = get_yahoo_data(symbol)
        if data:
            zyklus = get_zyklus_score(symbol, data, None)
            if pd.isna(zyklus):
                fehler_log.append(f"{symbol}: Zyklus Score fehlt")
            else:
                data["Zykluswirkung"] = zyklus
                daten.append(data)
        else:
            fehler_log.append(fehler)
        progress.progress((i+1)/len(st.session_state.aktien_liste))

    if fehler_log:
        with st.expander(f"Übersprungen wegen fehlender Daten: {len(fehler_log)}"):
            for f in fehler_log: st.write(f"- {f}")

    if len(daten) < 2:
        st.error("Zu wenige Aktien mit vollständigen Daten zum Ranken")
        st.stop()

    df = pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "Sektor", "Datum", "Bewertung"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, horizont).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["Umsatz CAGR 5Y", "EPS CAGR 5Y", "Bruttomarge", "Operating Margin", "FCF Marge"]:
        if c in df.columns: df[c] = (df[c] * 100).round(2)

    st.success(f"Fertig! {len(df)} von {len(st.session_state.aktien_liste)} Aktien mit vollständigen Daten")

    tab1, tab2, tab3 = st.tabs(["Ranking", "Details", "Export"])
    with tab1:
        st.dataframe(df[["Datum","Ticker","Name","Sektor","Gesamtscore","Bewertung","Zykluswirkung","Forward KGV","Moat Score"]], use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ranking')
        st.download_button("Excel herunterladen", output.getvalue(), f"Halbleiter_Ranking_{datetime.now().strftime('%Y-%m-%d')}_{horizont}M.xlsx")
