# ============================================
# Halbleiter & KI Aktien Ranking v7.52
# Getestet mit yfinance 0.2.40 + KR/JP/TW Aktien
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

st.set_page_config(page_title="Halbleiter Ranking v7.52", layout="wide")
VERSION = "v7.52"

if 'aktien_liste' not in st.session_state:
    st.session_state.aktien_liste = [
        "MU", "SNDK", "NVDA", "AMD", "AVGO", "TSM",
        "005930.KS", "000660.KS", "285A.T", "ASML",
        "AMAT", "LRCX", "KLAC"
    ]

namen = {"MU": "Micron", "SNDK": "SanDisk", "NVDA": "Nvidia", "AMD": "AMD", "AVGO": "Broadcom", "TSM": "TSMC", "005930.KS": "Samsung", "000660.KS": "SK Hynix", "285A.T": "Kioxia", "ASML": "ASML", "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA"}
SEKTOR = {"NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip", "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment", "TSM": "Foundry", "MU": "Speicher", "SNDK": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher"}
AI_EXPOSURE = {"NVDA":100, "AVGO":95, "000660.KS":90, "TSM":90, "MU":85, "AMD":80, "005930.KS":80, "ASML":80, "KLAC":75, "LRCX":75, "AMAT":75, "SNDK":70, "285A.T":60}
STRAT_BEDEUTUNG = {"ASML":100, "TSM":100, "NVDA":95, "AMAT":90, "LRCX":90, "KLAC":90, "AVGO":85, "000660.KS":80, "MU":80, "AMD":75, "005930.KS":75, "SNDK":70, "285A.T":60}
SEKTOR_MEDIANS = {
    "Equipment": {"KGV": 25, "EV_EBITDA": 15, "CAGR_REV": 0.08, "CAGR_EPS": 0.12, "GM": 0.55, "OM": 0.30},
    "Speicher": {"KGV": 10, "EV_EBITDA": 6, "CAGR_REV": 0.05, "CAGR_EPS": 0.08, "GM": 0.40, "OM": 0.20},
    "KI_Chip": {"KGV": 35, "EV_EBITDA": 25, "CAGR_REV": 0.25, "CAGR_EPS": 0.35, "GM": 0.70, "OM": 0.45},
    "Foundry": {"KGV": 18, "EV_EBITDA": 12, "CAGR_REV": 0.15, "CAGR_EPS": 0.20, "GM": 0.55, "OM": 0.40}
}

def get_gewichte_sektor(horizont, sektor):
    if horizont == 6: base = {"Bewertung":0.35, "Zyklus":0.35, "Wachstum":0.10, "Qualität":0.10, "Moat":0.10} if sektor=="Speicher" else {"Bewertung":0.20, "Zyklus":0.25, "Wachstum":0.20, "Qualität":0.15, "Moat":0.20}
    elif horizont == 12: base = {"Bewertung":0.30, "Zyklus":0.25, "Wachstum":0.15, "Qualität":0.15, "Moat":0.15} if sektor=="Speicher" else {"Bewertung":0.15, "Zyklus":0.20, "Wachstum":0.20, "Qualität":0.20, "Moat":0.25}
    else: base = {"Bewertung":0.15, "Zyklus":0.15, "Wachstum":0.25, "Qualität":0.20, "Moat":0.25}
    summe = sum(base.values())
    base = {k: v/summe for k,v in base.items()}
    return {"Forward KGV": base["Bewertung"] * 0.4, "EV/EBITDA": base["Bewertung"] * 0.4, "PEG": base["Bewertung"] * 0.2, "Zykluswirkung": base["Zyklus"], "Umsatz CAGR 5Y": base["Wachstum"] * 0.5, "EPS CAGR 5Y": base["Wachstum"] * 0.3, "EPS Revision 3M": base["Wachstum"] * 0.2, "Bruttomarge": base["Qualität"] * 0.25, "Operating Margin": base["Qualität"] * 0.25, "FCF Marge": base["Qualität"] * 0.25, "FCF Positiv": base["Qualität"] * 0.15, "Net Debt/EBITDA": base["Qualität"] * 0.10, "Moat Score": base["Moat"] * 0.5, "AI Exposure": base["Moat"] * 0.3, "Strategische Bedeutung": base["Moat"] * 0.2}

def safe_get(d, key): return d.get(key, np.nan) if isinstance(d, dict) else np.nan

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol):
    fehlende_felder = []
    try:
        time.sleep(1.2)
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        financials = ticker.financials
        cashflow = ticker.cashflow
        history = ticker.history(period="1d")
        sektor = SEKTOR.get(symbol, "Foundry")

        # 1. KURS - Pflicht
        kurs = safe_get(info, "currentPrice")
        if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
        if pd.isna(kurs): return None, f"{symbol}: Kein Kurs"

        # 2. MARKETCAP - Pflicht
        marketcap = safe_get(info, "marketCap")
        if pd.isna(marketcap): return None, f"{symbol}: Keine Marketcap"

        # 3. BEWERTUNG - Mit 3-stufigem Fallback
        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv): forward_kgv = safe_get(info, "trailingPE")
        if pd.isna(forward_kgv):
            forward_kgv = SEKTOR_MEDIANS[sektor]["KGV"]
            fehlende_felder.append("KGV")

        ev_ebitda = safe_get(info, "enterpriseToEbitda")
        if pd.isna(ev_ebitda):
            ev_ebitda = SEKTOR_MEDIANS[sektor]["EV_EBITDA"]
            fehlende_felder.append("EV/EBITDA")

        # 4. WACHSTUM - Mit Fallback
        cagr_rev = np.nan
        cagr_eps = np.nan
        try:
            if financials is not None and not financials.empty:
                rev_series = financials.loc["Total Revenue"].dropna()
                eps_series = financials.loc["Diluted EPS"].dropna()
                if len(rev_series) >=3: cagr_rev = (rev_series.iloc[0]/rev_series.iloc[-1])**(1/(len(rev_series)-1))-1
                if len(eps_series) >=3: cagr_eps = (eps_series.iloc[0]/eps_series.iloc[-1])**(1/(len(eps_series)-1))-1
        except: pass

        if pd.isna(cagr_rev):
            cagr_rev = safe_get(info, "revenueGrowth", 0.05) * 3 # Proxy
            if pd.isna(cagr_rev): cagr_rev = SEKTOR_MEDIANS[sektor]["CAGR_REV"]
            fehlende_felder.append("CAGR")

        if pd.isna(cagr_eps):
            cagr_eps = safe_get(info, "earningsGrowth", 0.08) * 3 # Proxy
            if pd.isna(cagr_eps): cagr_eps = SEKTOR_MEDIANS[sektor]["CAGR_EPS"]
            fehlende_felder.append("CAGR")

        # 5. MARGEN - Mit Fallback
        gm = safe_get(info, "grossMargins")
        om = safe_get(info, "operatingMargins")
        if pd.isna(gm):
            gm = SEKTOR_MEDIANS[sektor]["GM"]
            fehlende_felder.append("GM")
        if pd.isna(om):
            om = SEKTOR_MEDIANS[sektor]["OM"]
            fehlende_felder.append("OM")

        # 6. REST
        fcf, revenue = np.nan, np.nan
        try:
            if cashflow is not None and not cashflow.empty: fcf = cashflow.loc["Free Cash Flow"].iloc[0]
            if financials is not None and not financials.empty: revenue = financials.loc["Total Revenue"].iloc[0]
        except: pass
        fcf_marge = (fcf / revenue) if (pd.notna(fcf) and pd.notna(revenue) and revenue!= 0) else np.nan
        debt = safe_get(info, "totalDebt", 0)
        cash = safe_get(info, "totalCash", 0)
        ebitda = safe_get(info, "ebitda")
        net_debt_ebitda = (debt - cash) / ebitda if pd.notna(ebitda) and ebitda!= 0 else 1.0

        # MOAT
        gm_pct = gm * 100
        om_pct = om * 100
        market_score = np.clip(np.log10(marketcap) * 8, 0, 100)
        tech_score = gm_pct * 0.6 + om_pct * 0.4
        margin_score = gm_pct * 0.5 + om_pct * 0.5
        moat = np.clip(market_score*0.4 + tech_score*0.3 + margin_score*0.3, 0, 100) * 0.7 + STRAT_BEDEUTUNG.get(symbol, 50) * 0.3

        # ZYKLUS
        eps_score = np.clip((cagr_eps * 100 + 20) * 2, 0, 100)
        if sektor == "Equipment": bewertung_score = np.clip((40 - forward_kgv) * 3, 0, 100)
        elif sektor == "Speicher": bewertung_score = np.clip((12 - forward_kgv) * 8, 0, 100)
        else: bewertung_score = np.clip((30 - forward_kgv) * 5, 0, 100)
        zyklus = eps_score*0.5 + 50*0.2 + bewertung_score*0.3

        data = {
            "Ticker": symbol, "Sektor": sektor, "Fehlt": ", ".join(list(set(fehlende_felder))) if fehlende_felder else "vollständig",
            "Name": safe_get(info, "shortName", namen.get(symbol, symbol)),
            "Marktkapitalisierung Mrd": round(marketcap / 1e9, 1),
            "Kurs": round(kurs, 2),
            "Forward KGV": forward_kgv, "EV/EBITDA": ev_ebitda, "PEG": safe_get(info, "pegRatio", 1.5),
            "Umsatz CAGR 5Y": cagr_rev, "EPS CAGR 5Y": cagr_eps, "EPS Revision 3M": 50.0,
            "Bruttomarge": gm, "Operating Margin": om, "FCF Marge": fcf_marge,
            "FCF Positiv": 100 if pd.notna(fcf) and fcf > 0 else 0,
            "Net Debt/EBITDA": net_debt_ebitda,
            "Moat Score": moat, "AI Exposure": AI_EXPOSURE.get(symbol, 50),
            "Strategische Bedeutung": STRAT_BEDEUTUNG.get(symbol, 50),
            "Zykluswirkung": np.clip(zyklus, 0, 100)
        }
        return data, None
    except Exception as e:
        return None, f"{symbol}: Fatal Error {str(e)[:50]}"

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
            return ((x.clip(lo, hi) - lo) / (hi - lo)) * 100 if besser=="hoch" else (1 - ((x.clip(lo, hi) - lo) / (hi - lo))) * 100
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
st.caption("Robuster Datenbezug. ⚠️ = Fallback genutzt")

col1, col2 = st.columns([1,2])
with col1: horizont = st.selectbox("Anlagehorizont", [6, 12, 36], format_func=lambda x: f"{x} Monate")
with col2:
    such_ticker = st.text_input("Ticker hinzufügen")
    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("Hinzufügen") and such_ticker.upper():
            if such_ticker.upper() not in st.session_state.aktien_liste: st.session_state.aktien_liste.append(such_ticker.upper())
            st.rerun()
    with col_clear:
        if st.button("Liste leeren"): st.session_state.aktien_liste = []; st.rerun()

st.write(f"**Liste:** {', '.join(st.session_state.aktien_liste)}")

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0); daten = []; fehler_log = []
    for i, symbol in enumerate(st.session_state.aktien_liste):
        st.text(f"Lade {symbol}... {i+1}/{len(st.session_state.aktien_liste)}")
        data, fehler = get_yahoo_data(symbol)
        if data: daten.append(data)
        else: fehler_log.append(fehler)
        progress.progress((i+1)/len(st.session_state.aktien_liste))

    if fehler_log:
        with st.expander(f"❌ Übersprungen: {len(fehler_log)}"):
            for f in fehler_log: st.write(f"- {f}")

    if len(daten) < 2: st.error("Zu wenige Daten"); st.stop()

    df = pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "Sektor", "Datum", "Bewertung", "Fehlt"]: df[c] = pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, horizont).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["Umsatz CAGR 5Y", "EPS CAGR 5Y", "Bruttomarge", "Operating Margin", "FCF Marge"]:
        if c in df.columns: df[c] = (df[c] * 100).round(2)

    st.success(f"✅ {len(df)} von {len(st.session_state.aktien_liste)} Aktien gerankt")

    tab1, tab2, tab3 = st.tabs(["Ranking", "Details", "Export"])
    with tab1:
        df["Name"] = df.apply(lambda x: x["Name"] + " ⚠️" if x["Fehlt"]!= "vollständig" else x["Name"], axis=1)
        st.dataframe(df[["Datum","Ticker","Name","Sektor","Gesamtscore","Bewertung","Zykluswirkung","Forward KGV","Fehlt"]], use_container_width=True, hide_index=True)
    with tab2: st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Ranking')
        st.download_button("Excel herunterladen", output.getvalue(), f"Halbleiter_Ranking_{datetime.now().strftime('%Y-%m-%d')}_{horizont}M.xlsx")
