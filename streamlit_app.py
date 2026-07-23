# ============================================
# Halbleiter & KI Aktien Ranking v9.11
# KISS: 9 KPIs, Gew. Datenqualität, Auto-Median
# FIX: Nur Pause gegen Rate Limit eingefügt
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

st.set_page_config(page_title="Halbleiter Ranking v9.11", layout="wide")
VERSION = "v9.11"

if 'aktien_liste' not in st.session_state:
    st.session_state.aktien_liste = [
        "MU", "SNDK", "NVDA", "AMD", "AVGO", "TSM",
        "005930.KS", "000660.KS", "285A.T", "ASML",
        "AMAT", "LRCX", "KLAC", "MSFT", "GOOGL"
    ]

namen = {
    "MU": "Micron", "SNDK": "SanDisk", "NVDA": "Nvidia", "AMD": "AMD",
    "AVGO": "Broadcom", "TSM": "TSMC", "005930.KS": "Samsung",
    "000660.KS": "SK Hynix", "285A.T": "Kioxia", "ASML": "ASML",
    "AMAT": "Applied Materials", "LRCX": "Lam Research", "KLAC": "KLA",
    "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon"
}

SEKTOR = {
    "NVDA": "KI_Chip", "AMD": "KI_Chip", "AVGO": "KI_Chip",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "TSM": "Foundry",
    "MU": "Speicher", "SNDK": "Speicher", "000660.KS": "Speicher", "285A.T": "Speicher", "005930.KS": "Speicher",
    "MSFT": "Hyperscaler_AI", "GOOGL": "Hyperscaler_AI", "AMZN": "Hyperscaler_AI"
}

AI_EXPOSURE = {
    "NVDA": 100, "AVGO": 95, "MSFT": 95, "GOOGL": 95, "000660.KS": 90, "TSM": 90,
    "AMZN": 90, "MU": 85, "SNDK": 85, "005930.KS": 85, "AMD": 80, "285A.T": 80,
    "ASML": 80, "KLAC": 75, "LRCX": 75, "AMAT": 75
}

STRAT_BEDEUTUNG = {
    "ASML": 100, "TSM": 100, "NVDA": 95, "MSFT": 95, "GOOGL": 95, "AMAT": 90,
    "LRCX": 90, "KLAC": 90, "AMZN": 90, "005930.KS": 88, "AVGO": 85, "000660.KS": 85,
    "MU": 82, "SNDK": 78, "AMD": 75, "285A.T": 75
}

SEKTOR_MEDIANS = {}

TOTAL_KPIS = 9
KPI_GEWICHTE_FEHLER = {
    "KGV": 3.0, "EV/EBITDA": 3.0, "Umsatztrend": 2.0, "Gewinntrend": 2.0,
    "GM": 1.5, "OM": 1.5, "FCF": 1.5, "AI": 1.0, "STRAT": 0.5
}
MAX_FEHLER_PUNKTE = sum(KPI_GEWICHTE_FEHLER.values())

def get_gewichte_sektor(horizont, sektor):
    if horizont == 6:
        base = {"Bewertung":0.25, "Wachstum":0.30, "Qualität":0.30, "Strategie":0.15}
    elif horizont == 12:
        base = {"Bewertung":0.25, "Wachstum":0.30, "Qualität":0.30, "Strategie":0.15}
    else:
        base = {"Bewertung":0.20, "Wachstum":0.35, "Qualität":0.30, "Strategie":0.15}

    return {
        "Forward KGV": base["Bewertung"] * 0.5,
        "EV/EBITDA": base["Bewertung"] * 0.5,
        "Umsatztrend": base["Wachstum"] * 0.5,
        "Gewinntrend": base["Wachstum"] * 0.5,
        "Bruttomarge": base["Qualität"] * 0.33,
        "Operating Margin": base["Qualität"] * 0.33,
        "FCF-Marge": base["Qualität"] * 0.34,
        "AI Exposure": base["Strategie"] * 0.5,
        "Strategische Bedeutung": base["Strategie"] * 0.5
    }

def safe_get(d, key, default=np.nan):
    try:
        if isinstance(d, dict): return d.get(key, default)
        return default
    except:
        return default

def get_row_safe(df, possible_keys):
    if df is None or df.empty: return pd.Series(dtype=float)
    for key in possible_keys:
        if key in df.index:
            series = df.loc[key].dropna()
            if len(series) > 0: return series
    return pd.Series(dtype=float)

def calc_sektor_medians(df):
    medians = {}
    for sektor in df["Sektor"].unique():
        sektor_df = df[df["Sektor"] == sektor]
        medians[sektor] = {
            "KGV": sektor_df["Forward KGV"].median(),
            "EV_EBITDA": sektor_df["EV/EBITDA"].median(),
            "CAGR_REV": sektor_df["Umsatztrend"].median(),
            "CAGR_EPS": sektor_df["Gewinntrend"].median(),
            "GM": sektor_df["Bruttomarge"].median(),
            "OM": sektor_df["Operating Margin"].median(),
            "FCF": sektor_df["FCF-Marge"].median(),
        }
    return medians

def get_rating(score, fehler_punkte):
    daten_qualitaet = 1.0 - (fehler_punkte / MAX_FEHLER_PUNKTE)
    if score >= 78 and daten_qualitaet > 0.8: return "🟢 STRONG BUY"
    elif score >= 65: return "🟢 BUY"
    elif score >= 48: return "🟡 HOLD"
    else: return "🔴 SELL"

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol):
    fehlende_felder = []
    fehler_punkte = 0.0
    try:
        time.sleep(1.0) # Basis-Pause aus v9.1 bleibt
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        financials = ticker.financials
        cashflow = ticker.cashflow
        history = ticker.history(period="1d")

        sektor = SEKTOR.get(symbol, "Foundry")

        kurs = safe_get(info, "currentPrice")
        if pd.isna(kurs) and not history.empty: kurs = history["Close"].iloc[-1]
        if pd.isna(kurs): return None, f"{symbol}: Kein Kurs"

        marketcap = safe_get(info, "marketCap")
        if pd.isna(marketcap): return None, f"{symbol}: Keine Marketcap"

        forward_kgv = safe_get(info, "forwardPE")
        if pd.isna(forward_kgv): forward_kgv = safe_get(info, "trailingPE")
        if pd.isna(forward_kgv) or forward_kgv < 0:
            forward_kgv = np.nan
            fehlende_felder.append("KGV")
            fehler_punkte += KPI_GEWICHTE_FEHLER["KGV"]

        ev_ebitda = safe_get(info, "enterpriseToEbitda")
        if pd.isna(ev_ebitda):
            ev_ebitda = np.nan
            fehlende_felder.append("EV/EBITDA")
            fehler_punkte += KPI_GEWICHTE_FEHLER["EV/EBITDA"]

        rev_series = get_row_safe(financials, ["Total Revenue", "Revenue"])
        umsatztrend = safe_get(info, "revenueGrowth")
        if pd.isna(umsatztrend) and len(rev_series) >= 2:
            umsatztrend = (rev_series.iloc[0]/rev_series.iloc[-1])**(1/max(1,len(rev_series)-1))-1
        if pd.isna(umsatztrend):
            fehlende_felder.append("Umsatztrend")
            fehler_punkte += KPI_GEWICHTE_FEHLER["Umsatztrend"]

        eps_series = get_row_safe(financials, ["Diluted EPS", "Diluted EPS (excl. Extra Items)", "Basic EPS"])
        gewinntrend = safe_get(info, "earningsGrowth")
        if pd.isna(gewinntrend) and len(eps_series) >= 2:
            gewinntrend = (eps_series.iloc[0]/eps_series.iloc[-1])**(1/max(1,len(eps_series)-1))-1
        if pd.isna(gewinntrend):
            fehlende_felder.append("Gewinntrend")
            fehler_punkte += KPI_GEWICHTE_FEHLER["Gewinntrend"]

        gm = safe_get(info, "grossMargins")
        if pd.isna(gm):
            fehlende_felder.append("GM")
            fehler_punkte += KPI_GEWICHTE_FEHLER["GM"]

        om = safe_get(info, "operatingMargins")
        if pd.isna(om):
            fehlende_felder.append("OM")
            fehler_punkte += KPI_GEWICHTE_FEHLER["OM"]

        fcf_series = get_row_safe(cashflow, ["Free Cash Flow", "FreeCashFlow"])
        fcf = fcf_series.iloc[0] if len(fcf_series) > 0 else np.nan
        revenue = rev_series.iloc[0] if len(rev_series) > 0 else np.nan
        fcf_marge = (fcf / revenue) if (pd.notna(fcf) and pd.notna(revenue) and revenue!= 0) else np.nan
        if pd.isna(fcf_marge):
            fehlende_felder.append("FCF")
            fehler_punkte += KPI_GEWICHTE_FEHLER["FCF"]

        ai_exp = AI_EXPOSURE.get(symbol, 50)
        strat = STRAT_BEDEUTUNG.get(symbol, 50)

        data = {
            "Ticker": symbol, "Sektor": sektor,
            "Fehlt": ", ".join(list(set(fehlende_felder))) if fehlende_felder else "vollständig",
            "Fehler_Punkte": fehler_punkte,
            "Name": safe_get(info, "shortName", namen.get(symbol, symbol)),
            "Marktkapitalisierung Mrd": round(marketcap / 1e9, 1),
            "Kurs": round(kurs, 2),
            "Forward KGV": forward_kgv, "EV/EBITDA": ev_ebitda,
            "Umsatztrend": umsatztrend, "Gewinntrend": gewinntrend,
            "Bruttomarge": gm, "Operating Margin": om, "FCF-Marge": fcf_marge,
            "AI Exposure": ai_exp, "Strategische Bedeutung": strat,
        }
        return data, None
    except Exception as e:
        return None, f"{symbol}: {str(e)[:60]}"

def norm_sektor_aware(df, col, besser="hoch", medians={}):
    key_map = {
        "Forward KGV": "KGV", "EV/EBITDA": "EV_EBITDA",
        "Umsatztrend": "CAGR_REV", "Gewinntrend": "CAGR_EPS",
        "Bruttomarge": "GM", "Operating Margin": "OM", "FCF-Marge": "FCF",
    }

    if col in ["AI Exposure", "Strategische Bedeutung"]:
        return pd.to_numeric(df[col], errors='coerce').fillna(50)

    rel_ratios = []
    for idx, row in df.iterrows():
        val = pd.to_numeric(row[col], errors='coerce')
        sektor = row["Sektor"]
        med_key = key_map.get(col, None)

        median_val = medians.get(sektor, {}).get(med_key, np.nan)
        if pd.isna(val) or pd.isna(median_val) or val == 0 or median_val == 0:
            rel_val = 1.0
        else:
            rel_val = (val / median_val) if besser == "hoch" else (median_val / val if val > 0 else 0.5)
        rel_ratios.append(rel_val)

    rel_s = pd.Series(rel_ratios, index=df.index)
    q = 0.10 if len(df) < 20 else 0.05
    lo, hi = rel_s.quantile(q), rel_s.quantile(1-q)
    if hi == lo: return pd.Series(50.0, index=df.index)

    clipped = rel_s.clip(lo, hi)
    return ((clipped - lo) / (hi - lo)) * 100

def berechne_scores(df, horizont):
    medians = calc_sektor_medians(df)

    for col, med_key in [("Forward KGV","KGV"), ("EV/EBITDA","EV_EBITDA"), ("Umsatztrend","CAGR_REV"), ("Gewinntrend","CAGR_EPS"), ("Bruttomarge","GM"), ("Operating Margin","OM"), ("FCF-Marge","FCF")]:
        for idx, row in df.iterrows():
            if pd.isna(row[col]):
                df.loc[idx, col] = medians[row["Sektor"]][med_key]

    scores = []
    niedrig = ["Forward KGV", "EV/EBITDA"]

    norm_df = pd.DataFrame(index=df.index)
    for col in df.columns:
        if col not in ["Ticker", "Name", "Sektor", "Datum", "Rating", "Fehlt", "Fehler_Punkte"]:
            norm_df[col] = norm_sektor_aware(df, col, besser="niedrig" if col in niedrig else "hoch", medians=medians)

    for idx, row in df.iterrows():
        gewichte = get_gewichte_sektor(horizont, row["Sektor"])
        score = sum(norm_df.loc[idx, k] * w for k, w in gewichte.items() if k in norm_df.columns)
        scores.append(score)

    df["Gesamtscore"] = pd.Series(scores, index=df.index).round(1)
    df["Rating"] = df.apply(lambda x: get_rating(x["Gesamtscore"], x["Fehler_Punkte"]), axis=1)
    return df

# ========== UI ==========
st.title(f"Halbleiter & KI Aktien Ranking {VERSION}")
st.caption("9 KPIs | Auto-Sektor-Median | Rating: STRONG BUY ≥78 | BUY ≥65 | HOLD ≥48 | SELL <48")

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

st.write(f"**Aktuelle Liste:** {', '.join(st.session_state.aktien_liste)}")

if st.button("Ranking starten", type="primary"):
    progress = st.progress(0); daten = []; fehler_log = []
    status = st.empty()

    for i, symbol in enumerate(st.session_state.aktien_liste):
        status.text(f"Lade {symbol}... {i+1}/{len(st.session_state.aktien_liste)}")

        data, fehler = get_yahoo_data(symbol)

        if data:
            daten.append(data)
        else:
            fehler_log.append(fehler)

        progress.progress((i+1)/len(st.session_state.aktien_liste))

        # kurze Pause
        time.sleep(1.5)

        # längere Pause nach jeweils 5 Aktien
        if (i + 1) % 5 == 0:
            time.sleep(5)

    if fehler_log:
        with st.expander(f"⚠️ Übersprungen ({len(fehler_log)})"):
            for f in fehler_log: st.write(f"- {f}")

    if len(daten) < 2: st.error("Zu wenige Daten"); st.stop()

    df = pd.DataFrame(daten)
    for c in df.columns:
        if c not in ["Ticker", "Name", "Sektor", "Datum", "Rating", "Fehlt"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = berechne_scores(df, horizont).sort_values("Gesamtscore", ascending=False)
    df.insert(0, "Datum", datetime.now().strftime("%Y-%m-%d"))

    for c in ["Umsatztrend", "Gewinntrend", "Bruttomarge", "Operating Margin", "FCF-Marge"]:
        if c in df.columns: df[c] = (df[c] * 100).round(2)

    st.success(f"✅ {len(df)} von {len(st.session_state.aktien_liste)} Aktien bewertet!")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("STRONG BUY", len(df[df["Rating"].str.contains("STRONG BUY")]))
    with col2: st.metric("BUY", len(df[df["Rating"].str.contains("BUY") & ~df["Rating"].str.contains("STRONG")]))
    with col3: st.metric("HOLD", len(df[df["Rating"].str.contains("HOLD")]))
    with col4: st.metric("SELL", len(df[df["Rating"].str.contains("SELL")]))

    tab1, tab2, tab3 = st.tabs(["Ranking 9 KPIs", "Alle Details", "Export"])

    with tab1:
        st.dataframe(df[["Datum", "Ticker", "Name", "Sektor", "Gesamtscore", "Rating", "Forward KGV", "EV/EBITDA", "Umsatztrend", "Gewinntrend", "Fehlt"]], use_container_width=True, hide_index=True)
    with tab2: st.dataframe(df, use_container_width=True, hide_index=True)
    with tab3:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Ranking_KISS')
        st.download_button("📊 Excel herunterladen", output.getvalue(), f"Halbleiter_Ranking_KISS_{datetime.now().strftime('%Y-%m-%d')}_{horizont}M.xlsx")
