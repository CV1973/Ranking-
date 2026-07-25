import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import io
import warnings
import fear_and_greed
warnings.filterwarnings("ignore")

def check_password():
    def password_entered():
        if st.session_state["password"] == "Dicker":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.text_input("Passwort", type="password", on_change=password_entered, key="password"); st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Passwort", type="password", on_change=password_entered, key="password")
        st.error("😞 Passwort falsch"); st.stop()
    else: return True
check_password()

st.set_page_config(page_title="AI Infrastructure Ranking v7.45.10", layout="wide")
VERSION = "v7.45.10"
AI_CYCLE_ASSUMPTION = "CAPEX BOOM BIS Q4 2027 - EMPFAENGER GEWINNEN"

DEFAULTS = {"aktien_liste": [], "datenbank": {}, "modus": "sammeln", "abfrage_queue": [], "version_loaded": ""}
for key, val in DEFAULTS.items():
    if key not in st.session_state: st.session_state[key] = val
if st.session_state.version_loaded!= VERSION:
    for key, val in DEFAULTS.items(): st.session_state[key] = val
    st.session_state.version_loaded = VERSION

STOCK_UNIVERSE = [
{"ticker":"A000660.KS", "name":"SK Hynix", "country":"South Korea", "flag":"🇰🇷", "segment":"Memory / HBM", "typ":"Empfaenger"},
{"ticker":"A005930.KS", "name":"Samsung Electronics", "country":"South Korea", "flag":"🇰🇷", "segment":"Memory / HBM", "typ":"Empfaenger"},
{"ticker":"2353.TWO", "name":"Quanta Computer", "country":"Taiwan", "flag":"🇹🇼", "segment":"Server / DC Hardware", "typ":"Empfaenger"},
{"ticker":"2303.TWO", "name":"UMC", "country":"Taiwan", "flag":"🇹🇼", "segment":"Foundry", "typ":"Empfaenger"},
{"ticker":"2392.TWO", "name":"Wiwynn", "country":"Taiwan", "flag":"🇹🇼", "segment":"Server / DC Hardware", "typ":"Empfaenger"},
{"ticker":"ASMI.AS", "name":"ASM International", "country":"Netherlands", "flag":"🇳🇱", "segment":"Semi Equipment", "typ":"Empfaenger"},
{"ticker":"SCHN.PA", "name":"Schneider Electric", "country":"France", "flag":"🇫🇷", "segment":"Power / Cooling", "typ":"Empfaenger"},
{"ticker":"BE.AS", "name":"Besi", "country":"Netherlands", "flag":"🇳🇱", "segment":"Semi Equipment", "typ":"Empfaenger"},
{"ticker":"6967.T", "name":"Fujikura", "country":"Japan", "flag":"🇯🇵", "segment":"Networking / Optical", "typ":"Empfaenger"},
{"ticker":"ANSS", "name":"Ansys", "country":"USA", "flag":"🇺🇸", "segment":"AI Infrastructure Software", "typ":"Neutral"},
{"ticker":"NVDA", "name":"Nvidia", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfaenger"},
{"ticker":"MSFT", "name":"Microsoft", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
]

if len(st.session_state.aktien_liste) == 0: st.session_state.aktien_liste = [s["ticker"] for s in STOCK_UNIVERSE]
CAPEX_BIAS = {"Empfaenger": 10, "Spender": -10, "Neutral": 0}
WEIGHTS = {
    "Empfaenger": {'Forward_KGV':0.10, 'EV_EBITDA':0.05, 'Umsatz_Wachstum':0.30, 'Bruttomarge':0.10, 'Operating_Margin':0.30, 'FCF_Marge':0.05},
    "Spender": {'Forward_KGV':0.15, 'EV_EBITDA':0.10, 'Umsatz_Wachstum':0.05, 'Bruttomarge':0.15, 'Operating_Margin':0.30, 'FCF_Marge':0.25},
    "Neutral": {'Forward_KGV':0.15, 'EV_EBITDA':0.15, 'Umsatz_Wachstum':0.15, 'Bruttomarge':0.15, 'Operating_Margin':0.20, 'FCF_Marge':0.20}
}

PFLICHT_KPIS = ["Forward_KGV","EV_EBITDA","Umsatz_Wachstum","Bruttomarge","Operating_Margin","FCF_Marge"]
KPI_LABELS = {"Forward_KGV":"Forward KGV","EV_EBITDA":"EV/EBITDA","Umsatz_Wachstum":"Umsatzwachstum","Bruttomarge":"Bruttomarge","Operating_Margin":"Operating Margin","FCF_Marge":"FCF Marge","Aktueller_Kurs":"Aktueller Kurs"}

@st.cache_data(ttl=1800)
def get_fear_greed():
    try: return round(fear_and_greed.get().value)
    except: return 50
def parse_number(text):
    if text is None: return np.nan
    text = str(text).strip().replace(",", ".")
    try: return float(text)
    except: return np.nan
def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        meta = next((s for s in STOCK_UNIVERSE if s["ticker"]==ticker), {"ticker":ticker,"name":ticker})
        st.session_state.datenbank[ticker] = {"daten":{"Ticker":ticker, **meta},"audit":{},"status":"neu"}
def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={"Wert":value,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}

def yahoo_laden(ticker, retry=3): # KEIN CACHE
    result = {k: np.nan for k in ["Aktueller_Kurs","Forward_KGV","EV_EBITDA","Umsatz_Wachstum","Bruttomarge","Operating_Margin","FCF_Marge"]}
    delay = 8.0 if any(x in ticker for x in ['.KS','.T','.AS','.PA','.SW','.TW','.DE']) else 2.0

    for attempt in range(retry):
        try:
            time.sleep(delay)
            tk = yf.Ticker(ticker)

            result["Aktueller_Kurs"] = tk.info.get("currentPrice") or tk.info.get("regularMarketPrice", np.nan)
            time.sleep(0.5)
            result["Forward_KGV"] = tk.info.get("forwardPE", np.nan)
            time.sleep(0.5)
            result["EV_EBITDA"] = tk.info.get("enterpriseToEbitda", np.nan)
            time.sleep(0.5)
            result["Umsatz_Wachstum"] = tk.info.get("revenueGrowth", np.nan)
            time.sleep(0.5)
            result["Bruttomarge"] = tk.info.get("grossMargins", np.nan)
            time.sleep(0.5)
            result["Operating_Margin"] = tk.info.get("operatingMargins", np.nan)
            time.sleep(0.5)

            fcf = tk.info.get("freeCashflow", np.nan); revenue = tk.info.get("totalRevenue", np.nan)
            if not pd.isna(fcf) and not pd.isna(revenue) and revenue!= 0: result["FCF_Marge"] = fcf / revenue

            if not all(pd.isna(v) for v in result.values()):
                return result
        except:
            time.sleep(10)
    return None

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    return [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]

def baue_abfrage_queue():
    queue = []
    progress = st.progress(0)
    status_text = st.empty()
    for i, ticker in enumerate(st.session_state.aktien_liste):
        init_ticker(ticker); obj = st.session_state.datenbank[ticker]
        status_text.text(f"Lade {i+1}/{len(st.session_state.aktien_liste)}: {ticker}")
        if obj["status"] == "neu":
            daten = yahoo_laden(ticker)
            if daten:
                for kpi, wert in daten.items():
                    if not pd.isna(wert): save_kpi(ticker, kpi, wert, "Yahoo")
            obj["status"] = "geladen"
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        for kpi in fehlende_kpis(ticker): queue.append((ticker, kpi))
    status_text.empty()
    st.session_state.abfrage_queue = queue

def normalize_global(df, col, higher_better=True):
    s = pd.to_numeric(df[col], errors="coerce")
    valid = s.dropna()
    if len(valid) < 2: return pd.Series(np.nan, index=s.index)
    x = s.copy()
    if not higher_better: x = -x
    return x.rank(pct=True)

def calculate_scores(df):
    df['Datenpunkte'] = df[PFLICHT_KPIS].notna().sum(axis=1)
    df['Vollstaendig'] = df['Datenpunkte'] == len(PFLICHT_KPIS)
    df['Datenqualitaet'] = df['Datenpunkte'] / len(PFLICHT_KPIS)
    df['Capex_Bias'] = df['typ'].map(CAPEX_BIAS)
    for col in PFLICHT_KPIS:
        lower_better = col in ['Forward_KGV','EV_EBITDA']
        df[f'Norm_{col}'] = normalize_global(df, col, not lower_better)
    df['Finanzscore'] = 0.0
    for idx, row in df.iterrows():
        weights = WEIGHTS[row['typ']]
        score = 0
        for col, w in weights.items():
            norm_val = row[f'Norm_{col}']
            if not pd.isna(norm_val): score += norm_val * w
        df.at[idx, 'Finanzscore'] = score * 100
    df['Gesamtscore_Roh'] = df['Finanzscore'] * 0.9
    df['Gesamtscore'] = (df['Gesamtscore_Roh'] * (0.3 + 0.7 * df['Datenqualitaet']) + df['Capex_Bias']).round(1)
    df = df.sort_values("Gesamtscore", ascending=False, na_position='last').reset_index(drop=True)
    df["Rang"] = df.index + 1
    return df

def get_investment_rating(score, vollstaendig):
    if pd.isna(score): return "N/A"
    if not vollstaendig: return "N/A - Daten fehlen"
    if score >= 80: return "Strong Buy"
    elif score >= 65: return "Buy"
    elif score >= 45: return "Hold"
    else: return "Sell"

def highlight_na(val):
    return 'background-color: #FFF9C4' if pd.isna(val) else ''

def screen_sammeln():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    fear_greed = get_fear_greed()
    st.info(f"**Axiom:** {AI_CYCLE_ASSUMPTION} | Fear&Greed: {fear_greed}")
    df_meta = pd.DataFrame([s for s in STOCK_UNIVERSE if s["ticker"] in st.session_state.aktien_liste])
    st.table(df_meta[['ticker','name','flag','segment','typ']])
    if st.button("✅ Auswertung starten", type="primary"):
        with st.spinner("Lade Yahoo Daten... 8s Delay fuer Asien/EU"):
            baue_abfrage_queue()
        st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
        st.rerun()

def screen_abfrage():
    if len(st.session_state.abfrage_queue) == 0:
        st.session_state.modus = "ranking"
        st.rerun()
        return
    ticker, kpi = st.session_state.abfrage_queue[0]
    st.error(f"Fehlender Wert: {ticker} - {KPI_LABELS[kpi]}")
    eingabe = st.text_input("Wert eingeben")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern"):
            wert = parse_number(eingabe)
            if pd.isna(wert): st.error("Keine gueltige Zahl"); return
            save_kpi(ticker, kpi, wert, "Manuell")
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col2:
        if st.button("⏭️ Ueberspringen"):
            save_kpi(ticker, kpi, np.nan, "Uebersprungen")
            st.session_state.abfrage_queue.pop(0); st.rerun()
    with col3:
        if st.button("⏭️⏭️ Alle ueberspringen"):
            for t, k in st.session_state.abfrage_queue: save_kpi(t, k, np.nan, "Bulk")
            st.session_state.abfrage_queue = []; st.session_state.modus = "ranking"; st.rerun()

def screen_ranking():
    st.title(f"AI Infrastructure Ranking {VERSION}")
    liste=[st.session_state.datenbank[ticker]["daten"] for ticker in st.session_state.aktien_liste]
    df=pd.DataFrame(liste)
    if len(df)<2: st.error("Zu wenige Aktien"); return
    df = calculate_scores(df)
    df["Investment_Rating"] = df.apply(lambda x: get_investment_rating(x["Gesamtscore"], x["Vollstaendig"]), axis=1)
    st.subheader("Globales Ranking")
    show_cols = ['Rang','Ticker','name','flag','typ','Capex_Bias','Gesamtscore','Investment_Rating'] + PFLICHT_KPIS
    df_show = df[show_cols]
    st.table(df_show.style.map(highlight_na))
    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False)
    st.download_button("📥 Excel", output.getvalue(), file_name=f"AI_Ranking_{datetime.now().strftime('%Y-%m-%d')}.xlsx")

if st.session_state.modus == "sammeln": screen_sammeln()
elif st.session_state.modus == "abfrage": screen_abfrage()
elif st.session_state.modus == "ranking": screen_ranking()
