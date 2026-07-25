# ============================================
# AI Infrastructure Ranking v7.42 KISS FINAL
# NEU: Capex Bonus/Malus + Manuelle Gewichte
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import io
import warnings
import requests
import fear_and_greed
warnings.filterwarnings("ignore")

# ============================================
# 0. LOGIN SCHUTZ v7.42
# ============================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "Dicker":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Passwort", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Passwort", type="password", on_change=password_entered, key="password")
        st.error("😞 Passwort falsch")
        st.stop()
    else:
        return True

check_password()

st.set_page_config(page_title="AI Infrastructure Ranking v7.42", layout="wide")
VERSION = "v7.42"
AI_CYCLE_ASSUMPTION = "INTAKT BIS Q4 2027"
MIN_SEGMENT_SIZE = 5

# ============================================
# 1. SESSION STATE
# ============================================
DEFAULTS = {
    "aktien_liste": [],
    "datenbank": {},
    "modus": "sammeln",
    "abfrage_queue": [],
    "version_loaded": "",
    "segment_weights": {}
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if st.session_state.version_loaded!= VERSION:
    for key, val in DEFAULTS.items():
        st.session_state[key] = val
    st.session_state.version_loaded = VERSION

# ============================================
# 2. STOCK_UNIVERSE v7.42 - 62 WERTE
# ============================================
STOCK_UNIVERSE = [
{"ticker":"NVDA", "name":"Nvidia", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"AMD", "name":"AMD", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"AVGO", "name":"Broadcom", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"MRVL", "name":"Marvell", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"NASDAQ 100"},
{"ticker":"ARM", "name":"Arm Holdings", "country":"UK", "flag":"🇬🇧", "region":"Europe", "segment":"AI Compute", "index":"NASDAQ"},
{"ticker":"INTC", "name":"Intel", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Compute", "index":"Dow Jones"},
{"ticker":"MU", "name":"Micron", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"A000660.KS", "name":"SK Hynix", "country":"South Korea", "flag":"🇰🇷", "region":"Asia", "segment":"Memory / HBM", "index":"KOSPI"},
{"ticker":"A005930.KS", "name":"Samsung Electronics", "country":"South Korea", "flag":"🇰🇷", "region":"Asia", "segment":"Memory / HBM", "index":"KOSPI"},
{"ticker":"WDC", "name":"Western Digital", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"STX", "name":"Seagate", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Memory / HBM", "index":"NASDAQ 100"},
{"ticker":"4449.T", "name":"Kioxia", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Memory / HBM", "index":"TSE Prime"},
{"ticker":"ASML", "name":"ASML", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"AMAT", "name":"Applied Materials", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"LRCX", "name":"Lam Research", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"KLAC", "name":"KLA", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"8035.T", "name":"Tokyo Electron", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Semi Equipment", "index":"Nikkei 225"},
{"ticker":"ASMI.AS", "name":"ASM International", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"VATN.SW", "name":"VAT Group", "country":"Switzerland", "flag":"🇨🇭", "region":"Europe", "segment":"Semi Equipment", "index":"SMI"},
{"ticker":"BE.AS", "name":"Besi", "country":"Netherlands", "flag":"🇳🇱", "region":"Europe", "segment":"Semi Equipment", "index":"AEX"},
{"ticker":"6857.T", "name":"Advantest", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Semi Equipment", "index":"Nikkei 225"},
{"ticker":"TER", "name":"Teradyne", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Semi Equipment", "index":"NASDAQ 100"},
{"ticker":"TSM", "name":"TSMC", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Foundry", "index":"Taiwan Weighted"},
{"ticker":"GFS", "name":"GlobalFoundries", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Foundry", "index":"NASDAQ 100"},
{"ticker":"2303.TWO", "name":"UMC", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Foundry", "index":"Taiwan Weighted"},
{"ticker":"IFNNY", "name":"Infineon ADR", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Automotive Semiconductor / Power Semiconductor", "index":"DAX"},
{"ticker":"ANET", "name":"Arista Networks", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"CRDO", "name":"Credo", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ"},
{"ticker":"COHR", "name":"Coherent", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"LITE", "name":"Lumentum", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"NASDAQ 100"},
{"ticker":"6967.T", "name":"Fujikura", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"Networking / Optical", "index":"Nikkei 225"},
{"ticker":"CSCO", "name":"Cisco", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Networking / Optical", "index":"Dow Jones"},
{"ticker":"NOK", "name":"Nokia", "country":"Finland", "flag":"🇫🇮", "region":"Europe", "segment":"Networking / Optical", "index":"OMX Helsinki"},
{"ticker":"DELL", "name":"Dell", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Server / DC Hardware", "index":"S&P 500"},
{"ticker":"SMCI", "name":"Super Micro Computer", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Server / DC Hardware", "index":"NASDAQ 100"},
{"ticker":"2353.TWO", "name":"Quanta Computer", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Server / DC Hardware", "index":"Taiwan Weighted"},
{"ticker":"2392.TWO", "name":"Wiwynn", "country":"Taiwan", "flag":"🇹🇼", "region":"Asia", "segment":"Server / DC Hardware", "index":"Taiwan Weighted"},
{"ticker":"SCHN.PA", "name":"Schneider Electric", "country":"France", "flag":"🇫🇷", "region":"Europe", "segment":"Power / Cooling", "index":"CAC 40"},
{"ticker":"ETN", "name":"Eaton", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"VRT", "name":"Vertiv", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"SIE.DE", "name":"Siemens", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Power / Cooling", "index":"DAX"},
{"ticker":"ENR.DE", "name":"Siemens Energy", "country":"Germany", "flag":"🇩🇪", "region":"Europe", "segment":"Power / Cooling", "index":"MDAX"},
{"ticker":"ABBN.SW", "name":"ABB", "country":"Switzerland", "flag":"🇨🇭", "region":"Europe", "segment":"Power / Cooling", "index":"SMI"},
{"ticker":"BE", "name":"Bloom Energy", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"NASDAQ"},
{"ticker":"GEV", "name":"GE Vernova", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"CEG", "name":"Constellation Energy", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"S&P 500"},
{"ticker":"TXN", "name":"Texas Instruments", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Power / Cooling", "index":"NASDAQ 100"},
{"ticker":"MSFT", "name":"Microsoft", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"AMZN", "name":"Amazon", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"GOOGL", "name":"Alphabet", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"META", "name":"Meta", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"ORCL", "name":"Oracle", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"NOW", "name":"ServiceNow", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"EQIX", "name":"Equinix", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"NASDAQ 100"},
{"ticker":"DLR", "name":"Digital Realty", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Cloud / AI Platform", "index":"S&P 500"},
{"ticker":"CCJ", "name":"Cameco", "country":"Canada", "flag":"🇨🇦", "region":"North America", "segment":"Nuclear Energy Supply", "index":"NYSE"},
{"ticker":"BWXT", "name":"BWX Technologies", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"Nuclear Technology", "index":"NYSE"},
{"ticker":"MUFG", "name":"MUFG", "country":"Japan", "flag":"🇯🇵", "region":"Asia", "segment":"AI Infrastructure Financing", "index":"Nikkei 225"},
{"ticker":"ANSS", "name":"Ansys", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Infrastructure Software", "index":"NASDAQ 100"},
{"ticker":"PLTR", "name":"Palantir", "country":"USA", "flag":"🇺🇸", "region":"North America", "segment":"AI Infrastructure Software", "index":"NASDAQ 100"},
]

if len(st.session_state.aktien_liste) == 0:
    st.session_state.aktien_liste = [s["ticker"] for s in STOCK_UNIVERSE]

SEGMENT_SCORE = {
    "AI Compute": 90, "Memory / HBM": 88, "Semi Equipment": 85, "Foundry": 85,
    "Networking / Optical": 80, "Server / DC Hardware": 82, "Power / Cooling": 78,
    "Cloud / AI Platform": 85, "Automotive Semiconductor / Power Semiconductor": 78,
    "Nuclear Energy Supply": 70, "Nuclear Technology": 70, "AI Infrastructure Financing": 60,
    "AI Infrastructure Software": 83, "Sonstige AI Infrastructure": 75
}

# DEFAULT CAPEX BIAS
CAPEX_BIAS_DEFAULT = {
    "AI Compute": 5, "Memory / HBM": 5, "Semi Equipment": 5, "Foundry": 5,
    "Server / DC Hardware": 5, "Power / Cooling": 5,
    "Cloud / AI Platform": -5,
    "Networking / Optical": 0, "AI Infrastructure Software": 0,
    "Sonstige AI Infrastructure": 0, "Automotive Semiconductor / Power Semiconductor": 0,
    "Nuclear Energy Supply": 0, "Nuclear Technology": 0, "AI Infrastructure Financing": 0
}

# DEFAULT GEWICHTE
WEIGHTS_RECEIVER = {'Forward_KGV':0.10, 'EV_EBITDA':0.10, 'Umsatz_Wachstum':0.25, 'Bruttomarge':0.10, 'Operating_Margin':0.10, 'FCF_Marge':0.10, 'Strategic_Score':0.25}
WEIGHTS_SPENDER = {'Forward_KGV':0.25, 'EV_EBITDA':0.20, 'Umsatz_Wachstum':0.10, 'Bruttomarge':0.20, 'Operating_Margin':0.20, 'FCF_Marge':0.20, 'Strategic_Score':0.05}
WEIGHTS_NEUTRAL = {'Forward_KGV':0.20, 'EV_EBITDA':0.15, 'Umsatz_Wachstum':0.15, 'Bruttomarge':0.15, 'Operating_Margin':0.15, 'FCF_Marge':0.20, 'Strategic_Score':0.10}

# ============================================
# 3. PFLICHT_KPIS v7.42 KISS - 6 KPIs
# ============================================
PFLICHT_KPIS = [
    "Forward_KGV","EV_EBITDA","Umsatz_Wachstum","Bruttomarge",
    "Operating_Margin","FCF_Marge"
]

KPI_LABELS = {
    "Forward_KGV":"Forward KGV","EV_EBITDA":"EV/EBITDA","Umsatz_Wachstum":"Umsatzwachstum",
    "Bruttomarge":"Bruttomarge","Operating_Margin":"Operating Margin",
    "FCF_Marge":"FCF Marge","Strategic_Score":"Strategic Score", "Aktueller_Kurs":"Aktueller Kurs"
}

# ============================================
# 4. HELPER FUNKTIONEN
# ============================================
@st.cache_data(ttl=1800)
def get_fear_greed():
    try:
        fg = fear_and_greed.get()
        return round(fg.value)
    except:
        return 50

def safe_get(info, key):
    try: value = info.get(key); return np.nan if value is None else value
    except: return np.nan

def parse_number(text):
    if text is None: return np.nan
    text = str(text).strip().replace(",", ".")
    try: return float(text)
    except: return np.nan

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        meta = next((s for s in STOCK_UNIVERSE if s["ticker"]==ticker), {"ticker":ticker,"name":ticker})
        st.session_state.datenbank[ticker] = {
            "daten":{"Ticker":ticker, **meta},
            "audit":{},
            "status":"neu"
        }

def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={"Wert":value,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_laden(ticker):
    try:
        time.sleep(0.8)
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        fin = tk.financials
        cf = tk.cashflow

        price = safe_get(info,"currentPrice")
        if pd.isna(price): price = safe_get(info,"regularMarketPrice")
        if pd.isna(price): price = safe_get(info,"previousClose")
        currency = safe_get(info, "currency")

        forward_kgv = safe_get(info, "forwardPE")
        ev_ebitda = safe_get(info, "enterpriseToEbitda")
        umsatz_wachstum = safe_get(info, "revenueGrowth")
        brutto = safe_get(info, "grossMargins")
        op_marge = safe_get(info, "operatingMargins")

        fcf = safe_get(info,"freeCashflow")
        revenue = safe_get(info,"totalRevenue")

        if pd.isna(revenue) and not fin.empty:
            revenue = fin.iloc[0,0]
        if pd.isna(fcf) and not cf.empty and 'Free Cash Flow' in cf.index:
            fcf = cf.loc['Free Cash Flow'].iloc[0]

        if not pd.isna(fcf) and not pd.isna(revenue) and revenue!= 0:
            fcf_marge = fcf / revenue
        else:
            fcf_marge = np.nan

        if pd.isna(brutto) and not fin.empty and 'Gross Profit' in fin.index and 'Total Revenue' in fin.index:
            try: brutto = fin.loc['Gross Profit'].iloc[0] / fin.loc['Total Revenue'].iloc[0]
            except: pass
        if pd.isna(op_marge) and not fin.empty and 'Operating Income' in fin.index and 'Total Revenue' in fin.index:
            try: op_marge = fin.loc['Operating Income'].iloc[0] / fin.loc['Total Revenue'].iloc[0]
            except: pass

        return {
            "Aktueller_Kurs": price, "Waehrung": currency,
            "Forward_KGV":forward_kgv,"EV_EBITDA":ev_ebitda,"Umsatz_Wachstum":umsatz_wachstum,
            "Bruttomarge":brutto,"Operating_Margin":op_marge,"FCF_Marge":fcf_marge
        }
    except: return None

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    fehlend = [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]
    return fehlend

def baue_abfrage_queue():
    queue = []
    for ticker in st.session_state.aktien_liste:
        init_ticker(ticker)
        obj = st.session_state.datenbank[ticker]
        if obj["status"] == "neu":
            daten = yahoo_laden(ticker)
            if daten:
                for kpi, wert in daten.items():
                    if not pd.isna(wert):
                        save_kpi(ticker, kpi, wert, "Yahoo")
                segment = obj["daten"]["segment"]
                save_kpi(ticker, "Strategic_Score", SEGMENT_SCORE.get(segment, 70), "Segment")
            obj["status"] = "geladen"
        fehlend = fehlende_kpis(ticker)
        for kpi in fehlend:
            queue.append((ticker, kpi))
    st.session_state.abfrage_queue = queue

# ============================================
# 5. SCORING ENGINE v7.42 KISS - CAPEX BIAS
# ============================================
def get_segment_for_normalization(df):
    segment_counts = df['segment'].value_counts()
    small_segments = segment_counts[segment_counts < MIN_SEGMENT_SIZE].index.tolist()
    df['segment_norm'] = df['segment']
    if small_segments:
        df.loc[df['segment'].isin(small_segments), 'segment_norm'] = 'Sonstige AI Infrastructure'
    return df

def get_weights_for_segment(segment):
    if segment in ["AI Compute", "Memory / HBM", "Semi Equipment", "Foundry", "Server / DC Hardware", "Power / Cooling"]:
        return st.session_state.segment_weights.get(segment, WEIGHTS_RECEIVER)
    elif segment == "Cloud / AI Platform":
        return st.session_state.segment_weights.get(segment, WEIGHTS_SPENDER)
    else:
        return st.session_state.segment_weights.get(segment, WEIGHTS_NEUTRAL)

def normalize_segment(df_group, col, higher_better=True):
    s = pd.to_numeric(df_group[col], errors="coerce")
    valid = s.dropna()
    if len(valid) < 2: return pd.Series(np.nan, index=s.index)
    x = s.copy()
    if not higher_better: x = -x
    rank = x.rank(pct=True)
    return rank

def calculate_scores(df):
    df = get_segment_for_normalization(df)

    # Normalisierung pro segment_norm mit segment-spezifischen Gewichten
    for segment in df['segment_norm'].unique():
        seg_mask = df['segment_norm'] == segment
        orig_segment = df.loc[seg_mask, 'segment'].iloc[0]
        weights = get_weights_for_segment(orig_segment)
        finanz_gewichte = {k:v for k,v in weights.items() if k!= 'Strategic_Score'}

        for col, w in finanz_gewichte.items():
            lower_better = col in ['Forward_KGV','EV_EBITDA']
            df.loc[seg_mask, f'Norm_{col}'] = normalize_segment(df[seg_mask], col, not lower_better) * w

    df['Datenpunkte'] = df[PFLICHT_KPIS].notna().sum(axis=1)
    df['Vollständig'] = df['Datenpunkte'] == len(PFLICHT_KPIS)

    df['Finanzscore'] = np.nan
    norm_cols = [f'Norm_{c}' for c in PFLICHT_KPIS]
    df.loc[df['Vollständig'], 'Finanzscore'] = df.loc[df['Vollständig'], norm_cols].sum(axis=1, skipna=False) * 100

    df['Datenqualität'] = df['Datenpunkte'] / len(PFLICHT_KPIS)

    # Capex Bonus/Malus anwenden
    df['Capex_Bias'] = df['segment'].map(CAPEX_BIAS_DEFAULT).fillna(0)

    df['Gesamtscore_Roh'] = np.nan
    df.loc[df['Vollständig'], 'Gesamtscore_Roh'] = df.loc[df['Vollständig'], 'Finanzscore'] * 0.9 + df.loc[df['Vollständig'], 'Strategic_Score'] * 0.1
    df['Gesamtscore'] = np.nan
    df.loc[df['Vollständig'], 'Gesamtscore'] = (df.loc[df['Vollständig'], 'Gesamtscore_Roh'] * (0.3 + 0.7 * df.loc[df['Vollständig'], 'Datenqualität']) + df.loc[df['Vollständig'], 'Capex_Bias']).round(1)

    df = df.sort_values("Gesamtscore", ascending=False, na_position='last').reset_index(drop=True)
    df["Rang"] = np.where(df['Vollständig'], df.index + 1, np.nan)
    return df

def get_investment_rating(score):
    if pd.isna(score): return np.nan
    if score >= 80: return "Strong Buy"
    elif score >= 65: return "Buy"
    elif score >= 45: return "Hold"
    else: return "Sell"

def highlight_na(val):
    if pd.isna(val):
        return 'background-color: #FFF9C4'
    return ''

# ============================================
# 6. SCREENS
# ============================================
def screen_sammeln():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    fear_greed = get_fear_greed()
    st.info(f"**Investment Thesis:** AI Infrastructure Cycle: {AI_CYCLE_ASSUMPTION} | Fear&Greed: {fear_greed} | **Modus: Capex Bias Ranking**")

    st.subheader("1. Segment Gewichtung editieren - Capex Logik")
    st.warning("Empfänger +5P Bonus, Spender -5P Malus. Gewichte anpassen möglich.")

    segments = sorted(list(set([s['segment'] for s in STOCK_UNIVERSE])))
    weight_data = []
    for seg in segments:
        if seg in ["AI Compute", "Memory / HBM", "Semi Equipment", "Foundry", "Server / DC Hardware", "Power / Cooling"]:
            default_w = WEIGHTS_RECEIVER
            bias = 5
        elif seg == "Cloud / AI Platform":
            default_w = WEIGHTS_SPENDER
            bias = -5
        else:
            default_w = WEIGHTS_NEUTRAL
            bias = 0

        current_w = st.session_state.segment_weights.get(seg, default_w)
        weight_data.append({
            "Segment": seg, "Capex_Bias": bias,
            "Wachstum": current_w['Umsatz_Wachstum'],
            "Strategic": current_w['Strategic_Score'],
            "FCF": current_w['FCF_Marge'],
            "KGV": current_w['Forward_KGV']
        })

    df_weights = pd.DataFrame(weight_data)
    edited_df = st.data_editor(df_weights, num_rows="dynamic", use_container_width=True, key="weight_editor")

    if st.button("💾 Gewichte übernehmen"):
        for _, row in edited_df.iterrows():
            seg = row['Segment']
            st.session_state.segment_weights[seg] = {
                'Forward_KGV': row['KGV'], 'EV_EBITDA': row['KGV'],
                'Umsatz_Wachstum': row['Wachstum'], 'Bruttomarge': 0.15,
                'Operating_Margin': 0.15, 'FCF_Marge': row['FCF'],
                'Strategic_Score': row['Strategic']
            }
        st.success("Gewichte gespeichert")

    st.divider()
    st.subheader(f"Aktuelles Universum: {len(st.session_state.aktien_liste)} Werte")
    df_meta = pd.DataFrame([s for s in STOCK_UNIVERSE if s["ticker"] in st.session_state.aktien_liste])
    st.dataframe(df_meta[['ticker','name','flag','segment']], use_container_width=True, hide_index=True)

    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Lade Yahoo Daten..."):
            baue_abfrage_queue()
        if len(st.session_state.abfrage_queue) == 0:
            st.session_state.modus = "ranking"
        else:
            st.session_state.modus = "abfrage"
        st.rerun()

def screen_abfrage():
    if len(st.session_state.abfrage_queue) == 0: st.session_state.modus = "ranking"; st.rerun(); return
    ticker, kpi = st.session_state.abfrage_queue[0]
    st.error(f"Fehlender Wert: {ticker} - {KPI_LABELS[kpi]}")
    st.write(f"Noch {len(st.session_state.abfrage_queue)} fehlende KPIs")
    eingabe = st.text_input("Wert eingeben")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern"):
            wert = parse_number(eingabe)
            if pd.isna(wert): st.error("Keine gültige Zahl"); return
            save_kpi(ticker, kpi, wert, "Manuell")
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col2:
        if st.button("⏭️ Überspringen"):
            save_kpi(ticker, kpi, np.nan, "Übersprungen")
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col3:
        if st.button("⏭️⏭️ Alle überspringen"):
            for t, k in st.session_state.abfrage_queue:
                save_kpi(t, k, np.nan, "Bulk Übersprungen")
            st.session_state.abfrage_queue = []
            st.session_state.modus = "ranking"
            st.rerun()

def screen_ranking():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    liste=[]
    for ticker in st.session_state.aktien_liste:
        liste.append(st.session_state.datenbank[ticker]["daten"])
    df=pd.DataFrame(liste)
    if len(df)<2:
        st.error("Zu wenige Aktien")
        if st.button("⬅️ Zurück zur Liste"): st.session_state.modus = "sammeln"; st.rerun()
        return

    df = calculate_scores(df)
    df["Investment_Rating"] = df["Gesamtscore"].apply(get_investment_rating)

    st.subheader("Ranking v7.42 - Capex Bias")
    st.success(f"Axiom aktiv: {AI_CYCLE_ASSUMPTION}")
    small_segs = df[df['segment']!= df['segment_norm']]['segment'].unique()
    if len(small_segs) > 0:
        st.warning(f"Segmente <{MIN_SEGMENT_SIZE} zusammengefasst: {', '.join(small_segs)}")

    show_cols = ['Rang','Ticker','name','flag','segment','Capex_Bias',
                 'Aktueller_Kurs','Forward_KGV','EV_EBITDA','Umsatz_Wachstum',
                 'Bruttomarge','Operating_Margin','FCF_Marge',
                 'Strategic_Score','Finanzscore','Gesamtscore','Investment_Rating']
    show_cols = [c for c in show_cols if c in df.columns]
    df_show = df[show_cols].copy()

    format_dict = {c: lambda x: "N/A" if pd.isna(x) else f"{x:.2f}" for c in PFLICHT_KPIS + ['Finanzscore','Gesamtscore'] if c in df_show.columns}
    format_dict['Rang'] = lambda x: "N/A" if pd.isna(x) else f"{int(x)}"
    format_dict['Investment_Rating'] = lambda x: "N/A" if pd.isna(x) else x
    format_dict['Capex_Bias'] = lambda x: f"{int(x):+d}P"

    styled_df = df_show.style.map(highlight_na).format(format_dict)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranking_v7.42")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v7.42_{datetime.now().strftime('%Y-%m-%d')}.xlsx", use_container_width=True)
    if st.button("⬅️ Zurück zur Liste"): st.session_state.modus = "sammeln"; st.rerun()

# APP START / ROUTING
if st.session_state.modus == "sammeln": screen_sammeln()
elif st.session_state.modus == "abfrage": screen_abfrage()
elif st.session_state.modus == "ranking": screen_ranking()
