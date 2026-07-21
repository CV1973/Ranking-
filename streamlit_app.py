# ============================================
# Halbleiter & KI Aktien Ranking v7.42
# Fix: Cache + Ticker Objekt entfernt
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import traceback
from datetime import datetime
import io
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Halbleiter Ranking v7.42", layout="wide")

VERSION = "v7.42"
aktien_default = [
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

AI_EXPOSURE = {
    "NVDA":100, "AVGO":95, "000660.KS":90, "TSM":90,
    "MU":85, "AMD":80, "005930.KS":80, "ASML":80,
    "KLAC":75, "LRCX":75, "AMAT":75, "SNDK":70, "285A.T":60
}

STRAT_BEDEUTUNG = {
    "ASML":100, "TSM":100, "NVDA":95, "AMAT":90, "LRCX":90, "KLAC":90,
    "AVGO":85, "000660.KS":80, "MU":80, "AMD":75, "005930.KS":75, "SNDK":70, "285A.T":60
}

SPEICHER_AKTIEN = ["MU", "SNDK", "000660.KS", "285A.T", "005930.KS"]
KI_INFRA = ["NVDA", "AVGO", "ASML", "TSM", "AMAT", "LRCX", "KLAC"]

BASE_KURZ = {"Bewertung":0.30, "Zyklus":0.25, "Wachstum":0.20, "Qualität":0.15, "Moat":0.10}
BASE_LANG = {"Bewertung":0.20, "Zyklus":0.10, "Wachstum":0.20, "Qualität":0.30, "Moat":0.40}

def get_gewichte_interpoliert(horizont):
    t = np.clip((horizont - 3) / (120 - 3), 0, 1)
    gew = {}
    for k in BASE_KURZ:
        gew[k] = BASE_KURZ[k] * (1-t) + BASE_LANG[k] * t
    return {
        "Forward KGV": gew["Bewertung"] * 0.4, "EV/EBITDA": gew["Bewertung"] * 0.4, "PEG": gew["Bewertung"] * 0.2,
        "Zykluswirkung": gew["Zyklus"],
        "Umsatz CAGR 5Y": gew["Wachstum"] * 0.5, "EPS CAGR 5Y": gew["Wachstum"] * 0.3, "EPS Revision 3M": gew["Wachstum"] * 0.2,
        "Bruttomarge": gew["Qualität"] * 0.25, "Operating Margin": gew["Qualität"] * 0.25, "FCF Marge": gew["Qualität"] * 0.25,
        "FCF Positiv": gew["Qualität"] * 0.15, "Net Debt/EBITDA": gew["Qualität"] * 0.10,
        "Moat Score": gew["Moat"] * 0.5, "AI Exposure": gew["Moat"] * 0.3, "Strategische Bedeutung": gew["Moat"] * 0.2
    }

def get_cagr(financials, metric_name):
    try:
        series = financials.loc[metric_name].dropna()
        if len(series) < 3: return np.nan
        start = series.iloc[-1]
        ende = series.iloc[0]
        jahre = len(series) - 1
        if start <= 0: return np.nan
        return (ende / start) ** (1/jahre) - 1
    except:
        return np.nan

def get_eps_revision(revisions):
    try:
        if revisions is None or revisions.empty: return 50
        rev_3m = revisions.tail(3)["earningsEstimate"].pct_change().mean() * 100
        return np.clip(50 + rev_3m * 5, 0, 100)
    except:
        return 50

def calc_moat_score_semiconductor(info, financials):
    try:
        gm = info.get("grossMargins", 0) * 100
        om = info.get("operatingMargins", 0) * 100
        cagr = get_cagr(financials, "Total Revenue") * 100
        marketcap = info.get("marketCap", 1e9)
        market_score = np.clip(np.log10(marketcap) * 10, 0, 100)
        tech_score = gm * 0.6 + om * 0.4
        margin_score = gm * 0.5 + om * 0.5
        retention_score = np.clip((cagr + 10) * 2, 0, 100)
        pricing_score = gm
        return market_score*0.3 + tech_score*0.25 + margin_score*0.2 + retention_score*0.15 + pricing_score*0.1
    except:
        return 50

def get_zyklus_score(symbol, data, info, financials, horizont):
    eps_growth = data.get("EPS CAGR 5Y", 0)
    eps_score = np.clip((eps_growth * 100 + 20) * 2, 0, 100)

    gm_aktuell = info.get("grossMargins", 0)
    margin_trend_score = 50
    try:
        gm_series = (financials.loc["Gross Profit"] / financials.loc["Total Revenue"]).dropna()
        if len(gm_series) >= 3:
            avg_3y = gm_series.iloc[:3].mean()
            diff = (gm_aktuell - avg_3y) * 100
            margin_trend_score = np.clip(50 + diff * 10, 0, 100)
    except: pass

    nachfrage = 80 if symbol in KI_INFRA else 70 if symbol in SPEICHER_AKTIEN else 50
    fwd_pe = info.get("forwardPE", 20)
    bewertung_score = np.clip((30 - fwd_pe) * 5, 0, 100)
    zyklus = eps_score*0.4 + margin_trend_score*0.3 + nachfrage*0.2 + bewertung_score*0.1
    if horizont > 60: zyklus = zyklus * 0.7 + 50 * 0.3
    return zyklus

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol):
    for attempt in range(3):
        try:
            time.sleep(2)
            ticker = yf.Ticker(symbol)

            # FIX 3: Robuster fast_info
            try:
                fast = ticker.fast_info
                kurs = fast.get("lastPrice")
                marketcap = fast.get("marketCap")
            except:
                fast = {}
                kurs = None
                marketcap = None

            info = ticker.info or {}
            financials = ticker.financials
            cashflow = ticker.cashflow
            revisions = ticker.revisions

            if kurs is None or pd.isna(kurs):
                hist = ticker.history(period="1d")
                kurs = hist["Close"].iloc[-1] if not hist.empty else None
            if kurs is None or pd.isna(kurs):
                time.sleep(3)
                continue

            forward_kgv = info.get("forwardPE")
            peg = info.get("pegRatio")
            growth = info.get("earningsGrowth")
            if peg is None and forward_kgv and growth and growth > 0:
                peg = forward_kgv / (growth * 100)

            fcf, revenue = None, None
            try:
                fcf = cashflow.loc["Free Cash Flow"].iloc[0]
                revenue = financials.loc["Total Revenue"].iloc[0]
            except:
                fcf = info.get("freeCashflow")
                revenue = info.get("totalRevenue")
            fcf_marge = (fcf / revenue) if (fcf and revenue and revenue!= 0) else np.nan
            fcf_positiv = 100 if pd.notna(fcf) and fcf > 0 else 0

            debt = info.get("totalDebt") or 0
            cash = info.get("totalCash") or 0
            ebitda = info.get("ebitda")
            net_debt_ebitda = np.nan
            if ebitda and ebitda!= 0:
                net_debt_ebitda = np.clip((debt - cash) / ebitda, -5, 10)

            # FIX 1+2: Kein Ticker Objekt mehr. Nur dicts speichern
            return {
                "Ticker": symbol,
                "Name": info.get("shortName") or namen.get(symbol, symbol),
                "info": info, # statt _ticker
                "financials": financials, # statt _ticker
                "revisions": revisions,
                "Marktkapitalisierung Mrd": (marketcap / 1e9).round(1) if marketcap else np.nan,
                "Kurs": kurs,
                "Forward KGV": forward_kgv,
                "EV/EBITDA": info.get("enterpriseToEbitda"),
                "PEG": peg,
                "Umsatz CAGR 5Y": get_cagr(financials, "Total Revenue"),
                "EPS CAGR 5Y": get_cagr(financials, "Diluted EPS"),
                "EPS Revision 3M": get_eps_revision(revisions),
                "Bruttomarge": info.get("grossMargins"),
                "Operating Margin": info.get("operatingMargins"),
                "FCF Marge": fcf_marge,
                "FCF Positiv": fcf_positiv,
                "Net Debt/EBITDA": net_debt_ebitda,
                "Moat Score": calc_moat_score_semiconductor(info, financials),
                "AI Exposure": AI_EXPOSURE.get(symbol, 50),
                "Strategische Bedeutung": STRAT_BEDEUTUNG.get(symbol, 50)
            }
        except Exception as e: # FIX: Fehler anzeigen
            st.error(f"Fehler bei {symbol}: {e}")
            st.code(traceback.format_exc())
            time.sleep(4)
    return None

def berechne_scores(df, horizont):
    gewichte = get_gewichte_interpoliert(horizont)
    niedrig = ["Forward KGV", "EV/EBITDA", "PEG", "Net Debt/EBITDA"]

    def niedrig_besser(x):
        if x.notna().sum() < 2: return pd.Series(50.0, index=x.index)
        lo, hi = x.quantile(0.05), x.quantile(0.95)
        if pd.isna(lo) or pd.isna(hi) or hi == lo: return pd.Series(50.0, index=x.index)
        return (1 - ((x.clip(lo, hi) - lo) / (hi - lo))) * 100

    def hoch_besser(x):
        if x.notna().sum() < 2: return pd.Series(50.0, index=x.index)
        lo, hi = x.quantile(0.05), x.quantile(0.95)
        if pd.isna(lo) or pd.isna(hi) or hi == lo: return pd.Series(50.0, index=x.index)
        return ((x.clip(lo, hi) - lo) / (hi - lo)) * 100

    score = pd.Series(0.0, index=df.index)
    for k, w in gewichte.items():
        if k in df.columns:
            einzel = niedrig_besser(df[k]) if k in niedrig else hoch_besser(df[k])
            score += einzel.fillna(50) * w
    df["Gesamtscore"] = score.round(1)
    df["Bewertung"] = df["Gesamtscore"].apply(
        lambda x: "🟢 attraktiv" if x >= 75 else "🟡 fair" if x >= 50 else "🔴 teuer"
    )
    return df

# ========== UI ==========
st.title(f"Halbleiter & KI Aktien Ranking {VERSION}")
st.caption("Cycle Adjusted Quality Model - Bugfix Cache")

col1, col2 = st.columns([2,1])
with col1:
    horizont = st.slider("Anlagehorizont in Monaten", 3, 120, 24, 1)
    st.write(f"**{horizont} Monate:** {'Taktisch' if horizont <= 12 else 'Balanced' if horizont <= 36 else 'Strategisch'}")

with col2:
    aktien_input = st.text_area("Ticker, Komma getrennt", ", ".join(aktien_default), height=100)
    aktien_liste = [x.strip().upper() for x in aktien_input.split(",") if x.strip()]

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0)
    status = st.empty()
    fehler_liste = []

    daten = []
    for i, symbol in enumerate(aktien_liste):
        status.text(f"Lade {symbol}... {i+1}/{len(aktien_liste)}")
        data = get_yahoo_data(symbol)
        if data:
            # FIX: Kein data[_ticker].info mehr
            data["Zykluswirkung"] = get_zyklus_score(symbol, data, data["info"], data["financials"], horizont)
            daten.append(data)
        else:
            fehler_liste.append(symbol)
        progress.progress((i+1)/len(aktien_liste))

    if len(daten) < 3:
        st.error(f"Zu wenige Daten geladen. Erfolgreich: {len(daten)}. Fehler: {', '.join(fehler_liste)}")
        st.stop()

    if fehler_liste:
        st.warning(f"Übersprungen: {', '.join(fehler_liste)}")

    df = pd.DataFrame(daten)
    df = df.drop(columns=["info", "financials", "revisions"]) # nicht in Excel
    for c in df.columns:
        if c not in ["Ticker", "Name"]: df[c] = pd.to_numeric(df[c], errors="coerce")

    for col in ["Forward KGV", "EV/EBITDA", "PEG"]:
        if col in df.columns: df[col] = df[col].apply(lambda x: np.nan if (pd.notna(x) and x <= 0) else x)

    df = berechne_scores(df, horizont)
    df = df.sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    df["Kurs"] = df["Kurs"].round(2)
    df["Forward KGV"] = df["Forward KGV"].round(1)
    df["EV/EBITDA"] = df["EV/EBITDA"].round(1)
    df["PEG"] = df["PEG"].round(2)
    for c in ["Umsatz CAGR 5Y", "EPS CAGR 5Y", "Bruttomarge", "Operating Margin", "FCF Marge"]:
        df[c] = (df[c] * 100).round(2)

    st.success(f"Fertig! {len(df)} von {len(aktien_liste)} Aktien gerankt")

    tab1, tab2, tab3 = st.tabs(["Ranking", "Details", "Export"])
    with tab1:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Bewertung","Zykluswirkung","Forward KGV","Moat Score"]],
                     use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ranking')
        st.download_button(
            label="Excel herunterladen",
            data=output.getvalue(),
            file_name=f"Halbleiter_Ranking_{datetime.now().strftime('%Y-%m-%d')}_{horizont}M.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Horizont wählen und auf 'Ranking starten' klicken")
