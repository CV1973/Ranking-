# ============================================
# Halbleiter & KI Aktien Ranking v10.8
# Memory Cycle Adjusted | 12 Monate Focus
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

st.set_page_config(page_title="Halbleiter Ranking v10.8", layout="wide")
VERSION = "v10.8"

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

# AENDERUNG B: Granularer AI Exposure
AI_EXPOSURE_DETAILED = {
    "000660.KS": {"HBM":1.5, "DRAM":1.4, "NAND":1.0, "AI_Server":1.4, "Packaging":1.2}, # SK Hynix
    "005930.KS": {"HBM":1.25,"DRAM":1.3, "NAND":1.1, "AI_Server":1.2, "Packaging":1.3}, # Samsung
    "MU": {"HBM":1.3, "DRAM":1.35,"NAND":0.9, "AI_Server":1.3, "Packaging":1.1}, # Micron
    "SNDK": {"HBM":0, "DRAM":0, "NAND":1.4, "AI_Server":1.3, "Packaging":1.0}, # SanDisk
    "285A.T": {"HBM":0, "DRAM":0, "NAND":1.35,"AI_Server":1.2, "Packaging":1.0}, # Kioxia
    "NVDA": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.5, "Packaging":1.3}, # Nvidia
    "AVGO": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.4, "Packaging":1.2}, # Broadcom ASIC
    "TSM": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.4, "Packaging":1.4}, # TSMC CoWoS
    "ASML": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.25,"Packaging":1.0}, # EUV
    "AMAT": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.2, "Packaging":1.1},
    "LRCX": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.2, "Packaging":1.1},
    "KLAC": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.2, "Packaging":1.1},
    "AMD": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.3, "Packaging":1.1},
    "MSFT": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.1, "Packaging":0},
    "GOOGL": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.1, "Packaging":0},
    "AMZN": {"HBM":0, "DRAM":0, "NAND":0, "AI_Server":1.1, "Packaging":0},
}
AI_WEIGHTS = {"HBM":0.40, "DRAM":0.25, "NAND":0.25, "AI_Server":0.05, "Packaging":0.05} # Storage = NAND

KPIS = ["Forward KGV", "PEG", "EV/EBITDA", "Umsatztrend", "Gewinntrend", "Bruttomarge", "Operating Margin", "FCF-Marge", "Gewinnzyklus", "MemoryCycle", "Bilanz"]

KPI_QUALITAETS_GEWICHT = {
    "Forward KGV": 0.15, "PEG": 0.15, "EV/EBITDA": 0.15, "Umsatztrend": 0.10,
    "Gewinntrend": 0.10, "Bruttomarge": 0.08, "Operating Margin": 0.08, "FCF-Marge": 0.09
}

# AENDERUNG A: Neue Gewichtung
def get_gewichte():
    base = {
        "Gewinnzyklus": 0.30,
        "Bewertung": 0.25, # PEG + KGV + EV/EBITDA
        "AI_Narrativ": 0.20,
        "Qualitaet": 0.15,
        "Bilanz": 0.10
    }
    return {
        "Forward KGV": base["Bewertung"] * 0.4, "PEG": base["Bewertung"] * 0.4, "EV/EBITDA": base["Bewertung"] * 0.2,
        "Gewinnzyklus": base["Gewinnzyklus"],
        "AI_Infrastruktur": base["AI_Narrativ"],
        "Bruttomarge": base["Qualitaet"] * 0.33, "Operating Margin": base["Qualitaet"] * 0.33, "FCF-Marge": base["Qualitaet"] * 0.34,
        "Bilanz": base["Bilanz"]
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

# AENDERUNG C: Gewinnzyklus ohne Basiseffekt-Bonus
def berechne_gewinnzyklus(row):
    eps_score = 0
    if row["Gewinntrend"] > 0.5: eps_score = 100
    elif row["Gewinntrend"] > 0.2: eps_score = 75
    elif row["Gewinntrend"] > 0: eps_score = 50
    elif row["Gewinntrend"] > -0.2: eps_score = 25
    else: eps_score = 0

    margen_score = 0
    if row["Operating Margin"] > 0.25: margen_score = 100
    elif row["Operating Margin"] > 0.15: margen_score = 75
    elif row["Operating Margin"] > 0.05: margen_score = 50
    else: margen_score = 25

    umsatz_score = 0
    if row["Umsatztrend"] > 0.2: umsatz_score = 100
    elif row["Umsatztrend"] > 0.05: umsatz_score = 75
    elif row["Umsatztrend"] > -0.05: umsatz_score = 50
    else: umsatz_score = 25

    score = 0.5*eps_score + 0.3*margen_score + 0.2*umsatz_score
    return score

# AENDERUNG D: Memory Cycle Score
def berechne_memory_cycle(ticker, df_row):
    if ticker not in ["MU", "000660.KS", "005930.KS", "SNDK", "285A.T"]:
        return 50 # Neutral fuer Nicht-Speicher

    score = 50
    # 1. Bewertung: Niedriges KGV/PEG im Zyklus = gut
    if df_row["Forward KGV"] < 8: score += 20
    elif df_row["Forward KGV"] < 12: score += 10
    if df_row["PEG"] < 0.5: score += 15

    # 2. Turnaround Signal
    if df_row["Gewinntrend"] > 0.2: score += 15
    if df_row["Umsatztrend"] > 0.1: score += 10

    return max(0, min(100, score))

def get_rating(score, daten_qualitaet, fehlende_anzahl):
    if score >= 72 and daten_qualitaet >= 65 and fehlende_anzahl < 3:
        return "STRONG BUY"
    elif score >= 58: return "BUY"
    elif score >= 45: return "HOLD"
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

            kurs = safe_get(info, "currentPrice")
            if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
            if pd.isna(kurs): return None, f"{symbol}: Kein Kurs"

            marketcap = safe_get(info, "marketCap")
            if pd.isna(marketcap): return None, f"{symbol}: Keine Marketcap"

            # AENDERUNG 4: Forward PE priorisieren
            kgv = safe_get(info, "forwardPE")
            if pd.isna(kgv) or kgv <= 0: kgv = safe_get(info, "trailingPE")
            if pd.notna(kgv) and kgv <= 0: kgv = np.nan
            if pd.isna(kgv): fehlende.append("KGV")

            # PEG Forward
            peg = safe_get(info, "pegRatio")
            if pd.isna(peg): fehlende.append("PEG")

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

            # Bilanz: Net Debt / Marketcap
            total_debt = safe_get(info, "totalDebt")
            cash = safe_get(info, "totalCash")
            net_debt_ratio = (total_debt - cash) / marketcap if pd.notna(total_debt) and pd.notna(cash) and marketcap > 0 else np.nan
            if pd.isna(net_debt_ratio): fehlende.append("Bilanz")

            daten = {
                "Ticker": symbol, "Name": NAMEN.get(symbol, symbol),
                "Kurs": round(kurs,2), "Marktkapitalisierung Mrd": round(marketcap/1e9, 1),
                "Forward KGV": kgv, "PEG": peg, "EV/EBITDA": ev_ebitda,
                "Umsatztrend": umsatztrend, "Gewinntrend": gewinntrend,
                "Bruttomarge": gross_margin, "Operating Margin": operating_margin, "FCF-Marge": fcf_margin,
                "Bilanz": net_debt_ratio, "Fehlt": ", ".join(fehlende) if fehlende else "vollstaendig"
            }
            return daten, None
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1: time.sleep(10)
            else: return None, f"{symbol}: {str(e)[:80]}"
    return None, f"{symbol}: Rate Limit"

def normalize_kpi_global(df, spalte, typ="log"):
    werte = df[spalte].copy()
    if spalte == "Bilanz": # Niedriger ist besser
        werte = -werte
    if typ == "log":
        werte = 1/werte.where(werte>0)
    mean, std = werte.mean(), werte.std()
    if std == 0: return pd.Series(50, index=df.index)
    z = (werte - mean) / (std * 1.5)
    return (z.clip(-2, 2) + 2) * 25

# AENDERUNG B: Granularer AI Score
def get_ai_exposure_score(df):
    scores = []
    for idx,row in df.iterrows():
        ticker = row["Ticker"]
        if ticker not in AI_EXPOSURE_DETAILED:
            scores.append(50)
            continue
        factors = AI_EXPOSURE_DETAILED[ticker]
        score = sum(factors[k] * AI_WEIGHTS[k] for k in AI_WEIGHTS.keys())
        score_norm = (score - 0.5) / (1.5 - 0.5) * 100
        scores.append(max(0, min(100, score_norm)))
    return pd.Series(scores, index=df.index)

def berechne_scores(df):
    df["Gewinnzyklus"] = df.apply(berechne_gewinnzyklus, axis=1)
    df["MemoryCycle"] = [berechne_memory_cycle(t, df.loc[i]) for i,t in enumerate(df["Ticker"])]

    df_copy = df.copy()
    qualitaet_score = 0
    for kpi, gewicht in KPI_QUALITAETS_GEWICHT.items():
        hat_daten = (~df_copy[kpi].isna()).astype(int)
        qualitaet_score += hat_daten * gewicht
    df["Datenqualitaet"] = (qualitaet_score * 100).round(0)
    df["Fehlende Anzahl"] = df_copy.isna().sum(axis=1)

    for kpi in KPIS:
        median = df[kpi].median()
        df[kpi] = df[kpi].fillna(median)

    norm = pd.DataFrame(index=df.index)
    norm["Forward KGV"] = normalize_kpi_global(df, "Forward KGV", typ="log")
    norm["PEG"] = normalize_kpi_global(df, "PEG", typ="log")
    norm["EV/EBITDA"] = normalize_kpi_global(df, "EV/EBITDA", typ="log")
    norm["Umsatztrend"] = normalize_kpi_global(df, "Umsatztrend", typ="linear")
    norm["Gewinntrend"] = normalize_kpi_global(df, "Gewinntrend", typ="linear")
    norm["Gewinnzyklus"] = df["Gewinnzyklus"]
    norm["MemoryCycle"] = df["MemoryCycle"]
    norm["Bruttomarge"] = normalize_kpi_global(df, "Bruttomarge", typ="log")
    norm["Operating Margin"] = normalize_kpi_global(df, "Operating Margin", typ="log")
    norm["FCF-Marge"] = normalize_kpi_global(df, "FCF-Marge", typ="log")
    norm["Bilanz"] = normalize_kpi_global(df, "Bilanz", typ="linear")
    norm["AI_Infrastruktur"] = get_ai_exposure_score(df)
    df["AI_Infrastruktur"] = norm["AI_Infrastruktur"].round(1)

    gewichte = get_gewichte()
    # MemoryCycle mit in Gewinnzyklus einrechnen: 70% Gewinnzyklus + 30% Memory
    norm["Gewinnzyklus"] = norm["Gewinnzyklus"]*0.7 + norm["MemoryCycle"]*0.3

    scores = [sum(norm.loc[idx,kpi]*w for kpi,w in gewichte.items() if kpi in norm.columns) for idx in df.index]
    df["Gesamtscore"] = pd.Series(scores, index=df.index).round(1)

    df["Bereinigter Score"] = (df["Gesamtscore"] * (0.75 + 0.25 * df["Datenqualitaet"]/100)).round(1)
    df["Rating"] = df.apply(lambda x: get_rating(x["Bereinigter Score"], x["Datenqualitaet"], x["Fehlende Anzahl"]), axis=1)
    return df

st.title(f"Halbleiter & KI Aktien Ranking {VERSION}")
st.caption("Memory Cycle Adjusted | 12 Monate Focus")

with st.sidebar:
    st.header("AI Exposure Gewichtung")
    st.info("HBM 40% | DRAM 25% | Storage 25% | Server 5% | Packaging 5%")

col1,col2 = st.columns([1,2])
with col1:
    st.info(
        """
        Anlagehorizont: 12 Monate
        Methode: Memory Cycle Adjusted

        Gewichtung:
        - Gewinnzyklus 30%
        - Bewertung 25%
        - AI Exposure 20%
        - Qualitaet 15%
        - Bilanz 10%
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
        if c not in ["Ticker", "Name", "Fehlt"]: df[c]=pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["Umsatztrend", "Gewinntrend", "Bruttomarge", "Operating Margin", "FCF-Marge"]:
        if c in df.columns: df[c]=(df[c]*100).round(2)

    st.success(f"{len(df)} Aktien bewertet")

    a,b,c,d = st.columns(4)
    with a: st.metric("STRONG BUY", len(df[df["Rating"]=="STRONG BUY"]))
    with b: st.metric("BUY", len(df[df["Rating"]=="BUY"]))
    with c: st.metric("HOLD", len(df[df["Rating"]=="HOLD"]))
    with d: st.metric("SELL", len(df[df["Rating"]=="SELL"]))

    tab1,tab2,tab3 = st.tabs(["Ranking", "Details", "Export"])
    with tab1:
        st.dataframe(df[["Datum","Ticker","Name","Gesamtscore","Bereinigter Score","Rating","AI_Infrastruktur","Gewinnzyklus","MemoryCycle","Datenqualitaet","Forward KGV","PEG","Fehlt"]], use_container_width=True, hide_index=True)
    with tab2: st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output=io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Ranking_v10.8")
        st.download_button("Excel herunterladen", output.getvalue(), f"KI_Ranking_v10.8_{datetime.now().strftime('%Y-%m-%d')}_12M.xlsx")
