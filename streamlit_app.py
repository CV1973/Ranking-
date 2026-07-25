# ============================================
# AI Infrastructure Ranking v7.45.3 TEIL 1
# ============================================

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

# ============================================
# 0. LOGIN SCHUTZ
# ============================================
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

st.set_page_config(page_title="AI Infrastructure Ranking v7.45.3", layout="wide")
VERSION = "v7.45.3"
AI_CYCLE_ASSUMPTION = "CAPEX BOOM BIS Q4 2027 - EMPFÄNGER GEWINNEN"

# ============================================
# 1. SESSION STATE
# ============================================
DEFAULTS = {"aktien_liste": [], "datenbank": {}, "modus": "sammeln", "abfrage_queue": [], "version_loaded": ""}
for key, val in DEFAULTS.items():
    if key not in st.session_state: st.session_state[key] = val
if st.session_state.version_loaded!= VERSION:
    for key, val in DEFAULTS.items(): st.session_state[key] = val
    st.session_state.version_loaded = VERSION

# ============================================
# 2. STOCK_UNIVERSE - 58 WERTE
# ============================================
STOCK_UNIVERSE = [
{"ticker":"NVDA", "name":"Nvidia", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"AMD", "name":"AMD", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"AVGO", "name":"Broadcom", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"MRVL", "name":"Marvell", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"ARM", "name":"Arm Holdings", "country":"UK", "flag":"🇬🇧", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"INTC", "name":"Intel", "country":"USA", "flag":"🇺🇸", "segment":"AI Compute", "typ":"Empfänger"},
{"ticker":"MU", "name":"Micron", "country":"USA", "flag":"🇺🇸", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"A000660.KS", "name":"SK Hynix", "country":"South Korea", "flag":"🇰🇷", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"A005930.KS", "name":"Samsung Electronics", "country":"South Korea", "flag":"🇰🇷", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"WDC", "name":"Western Digital", "country":"USA", "flag":"🇺🇸", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"STX", "name":"Seagate", "country":"USA", "flag":"🇺🇸", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"4449.T", "name":"Kioxia", "country":"Japan", "flag":"🇯🇵", "segment":"Memory / HBM", "typ":"Empfänger"},
{"ticker":"ASML", "name":"ASML", "country":"Netherlands", "flag":"🇳🇱", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"AMAT", "name":"Applied Materials", "country":"USA", "flag":"🇺🇸", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"LRCX", "name":"Lam Research", "country":"USA", "flag":"🇺🇸", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"KLAC", "name":"KLA", "country":"USA", "flag":"🇺🇸", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"8035.T", "name":"Tokyo Electron", "country":"Japan", "flag":"🇯🇵", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"ASMI.AS", "name":"ASM International", "country":"Netherlands", "flag":"🇳🇱", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"VATN.SW", "name":"VAT Group", "country":"Switzerland", "flag":"🇨🇭", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"BE.AS", "name":"Besi", "country":"Netherlands", "flag":"🇳🇱", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"6857.T", "name":"Advantest", "country":"Japan", "flag":"🇯🇵", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"TER", "name":"Teradyne", "country":"USA", "flag":"🇺🇸", "segment":"Semi Equipment", "typ":"Empfänger"},
{"ticker":"TSM", "name":"TSMC", "country":"Taiwan", "flag":"🇹🇼", "segment":"Foundry", "typ":"Empfänger"},
{"ticker":"GFS", "name":"GlobalFoundries", "country":"USA", "flag":"🇺🇸", "segment":"Foundry", "typ":"Empfänger"},
{"ticker":"2303.TWO", "name":"UMC", "country":"Taiwan", "flag":"🇹🇼", "segment":"Foundry", "typ":"Empfänger"},
{"ticker":"DELL", "name":"Dell", "country":"USA", "flag":"🇺🇸", "segment":"Server / DC Hardware", "typ":"Empfänger"},
{"ticker":"SMCI", "name":"Super Micro Computer", "country":"USA", "flag":"🇺🇸", "segment":"Server / DC Hardware", "typ":"Empfänger"},
{"ticker":"2353.TWO", "name":"Quanta Computer", "country":"Taiwan", "flag":"🇹🇼", "segment":"Server / DC Hardware", "typ":"Empfänger"},
{"ticker":"2392.TWO", "name":"Wiwynn", "country":"Taiwan", "flag":"🇹🇼", "segment":"Server / DC Hardware", "typ":"Empfänger"},
{"ticker":"SCHN.PA", "name":"Schneider Electric", "country":"France", "flag":"🇫🇷", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"ETN", "name":"Eaton", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"VRT", "name":"Vertiv", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"SIE.DE", "name":"Siemens", "country":"Germany", "flag":"🇩🇪", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"ENR.DE", "name":"Siemens Energy", "country":"Germany", "flag":"🇩🇪", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"ABBN.SW", "name":"ABB", "country":"Switzerland", "flag":"🇨🇭", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"BE", "name":"Bloom Energy", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"GEV", "name":"GE Vernova", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"CEG", "name":"Constellation Energy", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"TXN", "name":"Texas Instruments", "country":"USA", "flag":"🇺🇸", "segment":"Power / Cooling", "typ":"Empfänger"},
{"ticker":"ANET", "name":"Arista Networks", "country":"USA", "flag":"🇺🇸", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"CRDO", "name":"Credo", "country":"USA", "flag":"🇺🇸", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"COHR", "name":"Coherent", "country":"USA", "flag":"🇺🇸", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"LITE", "name":"Lumentum", "country":"USA", "flag":"🇺🇸", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"6967.T", "name":"Fujikura", "country":"Japan", "flag":"🇯🇵", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"CSCO", "name":"Cisco", "country":"USA", "flag":"🇺🇸", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"NOK", "name":"Nokia", "country":"Finland", "flag":"🇫🇮", "segment":"Networking / Optical", "typ":"Empfänger"},
{"ticker":"MSFT", "name":"Microsoft", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"AMZN", "name":"Amazon", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"GOOGL", "name":"Alphabet", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"META", "name":"Meta", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"ORCL", "name":"Oracle", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"NOW", "name":"ServiceNow", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"EQIX", "name":"Equinix", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"DLR", "name":"Digital Realty", "country":"USA", "flag":"🇺🇸", "segment":"Cloud / AI Platform", "typ":"Spender"},
{"ticker":"IFNNY", "name":"Infineon ADR", "country":"Germany", "flag":"🇩🇪", "segment":"Automotive Semiconductor", "typ":"Neutral"},
{"ticker":"ANSS", "name":"Ansys", "country":"USA", "flag":"🇺🇸", "segment":"AI Infrastructure Software", "typ":"Neutral"},
{"ticker":"PLTR", "name":"Palantir", "country":"USA", "flag":"🇺🇸", "segment":"AI Infrastructure Software", "typ":"Neutral"},
{"ticker":"CCJ", "name":"Cameco", "country":"Canada", "flag":"🇨🇦", "segment":"Nuclear Energy Supply", "typ":"Neutral"},
{"ticker":"BWXT", "name":"BWX Technologies", "country":"USA", "flag":"🇺🇸", "segment":"Nuclear Technology", "typ":"Neutral"},
{"ticker":"MUFG", "name":"MUFG", "country":"Japan", "flag":"🇯🇵", "segment":"AI Infrastructure Financing", "typ":"Neutral"},
]

if len(st.session_state.aktien_liste) == 0: st.session_state.aktien_liste = [s["ticker"] for s in STOCK_UNIVERSE]
CAPEX_BIAS = {"Empfänger": 10, "Spender": -10, "Neutral": 0}
WEIGHTS = {
    "Empfänger": {'Forward_KGV':0.10, 'EV_EBITDA':0.05, 'Umsatz_Wachstum':0.30, 'Bruttomarge':0.10, 'Operating_Margin':0.30, 'FCF_Marge':0.05},
    "Spender": {'Forward_KGV':0.15, 'EV_EBITDA':0.10, 'Umsatz_Wachstum':0.05, 'Bruttomarge':0.15, 'Operating_Margin':0.30, 'FCF_Marge':0.25},
    "Neutral": {'Forward_KGV':0.15, 'EV_EBITDA':0.15, 'Umsatz_Wachstum':0.15, 'Bruttomarge':0.15, 'Operating_Margin':0.20, 'FCF_Marge':0.20}
}
PFLICHT_KPIS = ["Forward_KGV","EV_EBITDA","Umsatz_Wachstum","Bruttomarge","Operating_Margin","FCF_Marge"]
KPI_LABELS = {"Forward_KGV":"Forward KGV","EV_EBITDA":"EV/EBITDA","Umsatz_Wachstum":"Umsatzwachstum","Bruttomarge":"Bruttomarge","Operating_Margin":"Operating Margin","FCF_Marge":"FCF Marge","Aktueller_Kurs":"Aktueller Kurs"}

# ============================================
# 3. HELPER + YAHOO LOADER BUGFIX
# ============================================
@st.cache_data(ttl=1800)
def get_fear_greed():
    try: return round(fear_and_greed.get().value)
    except: return 50
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
        st.session_state.datenbank[ticker] = {"daten":{"Ticker":ticker, **meta},"audit":{},"status":"neu"}
def save_kpi(ticker,kpi,value,quelle):
    obj = st.session_state.datenbank[ticker]
    obj["daten"][kpi]=value
    obj["audit"][kpi]={"Wert":value,"Quelle":quelle,"Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),"Version":VERSION}

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_laden(ticker):
    result = {}
    try:
        if any(x in ticker for x in ['.KS','.T','.AS','.PA','.SW','.TW','.DE']):
            time.sleep(1.5)
        else:
            time.sleep(0.8)
        tk = yf.Ticker(ticker)
        result["Aktueller_Kurs"] = safe_get(tk.info, "currentPrice") or safe_get(tk.info, "regularMarketPrice")
        result["Waehrung"] = safe_get(tk.info, "currency")
        result["Forward_KGV"] = safe_get(tk.info, "forwardPE")
        result["EV_EBITDA"] = safe_get(tk.info, "enterpriseToEbitda")
        result["Umsatz_Wachstum"] = safe_get(tk.info, "revenueGrowth")
        result["Bruttomarge"] = safe_get(tk.info, "grossMargins")
        result["Operating_Margin"] = safe_get(tk.info, "operatingMargins")
        fin = tk.financials; cf = tk.cashflow
        fcf = safe_get(tk.info,"freeCashflow"); revenue = safe_get(tk.info,"totalRevenue")
        if pd.isna(revenue) and not fin.empty: revenue = fin.iloc[0,0]
        if pd.isna(fcf) and not cf.empty and 'Free Cash Flow' in cf.index: fcf = cf.loc['Free Cash Flow'].iloc[0]
        result["FCF_Marge"] = fcf / revenue if not pd.isna(fcf) and not pd.isna(revenue) and revenue!= 0 else np.nan
        if pd.isna(result["Bruttomarge"]) and not fin.empty and 'Gross Profit' in fin.index and 'Total Revenue' in fin.index:
            try: result["Bruttomarge"] = fin.loc['Gross Profit'].iloc[0] / fin.loc['Total Revenue'].iloc[0]
            except: pass
        if pd.isna(result["Operating_Margin"]) and not fin.empty and 'Operating Income' in fin.index and 'Total Revenue' in fin.index:
            try: result["Operating_Margin"] = fin.loc['Operating Income'].iloc[0] / fin.loc['Total Revenue'].iloc[0]
            except: pass
        return result
    except Exception as e:
        st.warning(f"Yahoo Fehler bei {ticker}: {str(e)[:50]}")
        return None

def fehlende_kpis(ticker):
    daten = st.session_state.datenbank[ticker]["daten"]
    return [kpi for kpi in PFLICHT_KPIS if pd.isna(daten.get(kpi,np.nan))]

def baue_abfrage_queue():
    queue = []
    progress = st.progress(0)
    for i, ticker in enumerate(st.session_state.aktien_liste):
        init_ticker(ticker); obj = st.session_state.datenbank[ticker]
        if obj["status"] == "neu":
            daten = yahoo_laden(ticker)
            if daten:
                for kpi, wert in daten.items():
                    if not pd.isna(wert): save_kpi(ticker, kpi, wert, "Yahoo")
            obj["status"] = "geladen"
        progress.progress((i+1)/len(st.session_state.aktien_liste))
        for kpi in fehlende_kpis(ticker): queue.append((ticker, kpi))
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
    df['Vollständig'] = df['Datenpunkte'] == len(PFLICHT_KPIS)
    df['Datenqualität'] = df['Datenpunkte'] / len(PFLICHT_KPIS)
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
    df['Gesamtscore'] = (df['Gesamtscore_Roh'] * (0.3 + 0.7 * df['Datenqualität']) + df['Capex_Bias']).round(1)
    df = df.sort_values("Gesamtscore", ascending=False, na_position='last').reset_index(drop=True)
    df["Rang"] = df.index + 1
    return df
 def get_investment_rating(score, vollstaendig):
    if pd.isna(score):
        return "N/A"
    if not vollstaendig:
        return "N/A - Daten fehlen"
    if score >= 80:
        return "Strong Buy"
    elif score >= 65:
        return "Buy"
    elif score >= 45:
        return "Hold"
    else:
        return "Sell"

def highlight_na(val):
    return 'background-color: #FFF9C4' if pd.isna(val) else ''

def screen_sammeln():
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');.stTable {font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;}</style>""", unsafe_allow_html=True)
    st.title(f"AI Infrastructure Ranking {VERSION}")
    fear_greed = get_fear_greed()
    st.info(f"**Axiom:** {AI_CYCLE_ASSUMPTION} | Fear&Greed: {fear_greed} | **OpMargin: 30%**")
    st.subheader(f"Universum: {len([s for s in STOCK_UNIVERSE if s['typ']=='Empfaenger'])} Empfaenger + {len([s for s in STOCK_UNIVERSE if s['typ']=='Spender'])} Spender + {len([s for s in STOCK_UNIVERSE if s['typ']=='Neutral'])} Neutral = {len(STOCK_UNIVERSE)} Werte")
    df_meta = pd.DataFrame([s for s in STOCK_UNIVERSE if s["ticker"] in st.session_state.aktien_liste])
    st.table(df_meta[['ticker','name','flag','segment','typ']])
    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Lade Yahoo Daten..."):
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
    st.write(f"Noch {len(st.session_state.abfrage_queue)} fehlende KPIs")
    eingabe = st.text_input("Wert eingeben")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("💾 Speichern"):
            wert = parse_number(eingabe)
            if pd.isna(wert):
                st.error("Keine gueltige Zahl")
                return
            save_kpi(ticker, kpi, wert, "Manuell")
            st.session_state.abfrage_queue.pop(0)
            st.rerun()
    with col2:
        if st.button("⏭️ Ueberspringen"):
            save_kpi(ticker, kpi, np.nan, "Uebersprungen")
            st.session_state.abfrage_queue.pop(0)
            st.rerun()
    with col3:
        if st.button("⏭️⏭️ Alle ueberspringen"):
            for t, k in st.session_state.abfrage_queue:
                save_kpi(t, k, np.nan, "Bulk Uebersprungen")
            st.session_state.abfrage_queue = []
            st.session_state.modus = "ranking"
            st.rerun()

def screen_ranking():
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');.stTable {font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;}</style>""", unsafe_allow_html=True)
    st.title(f"AI Infrastructure Ranking {VERSION}")
    liste=[st.session_state.datenbank[ticker]["daten"] for ticker in st.session_state.aktien_liste]
    df=pd.DataFrame(liste)
    if len(df)<2:
        st.error("Zu wenige Aktien")
        if st.button("⬅️ Zurueck zur Liste"):
            st.session_state.modus = "sammeln"
            st.rerun()
        return
    df = calculate_scores(df)
    df["Investment_Rating"] = df.apply(lambda x: get_investment_rating(x["Gesamtscore"], x["Vollstaendig"]), axis=1)
    fehlende = df[df['Vollstaendig'] == False]
    if len(fehlende) > 0:
        st.error(f"⚠️ {len(fehlende)} Werte haben fehlende Daten:")
        st.table(fehlende[['Ticker','name','flag','Datenpunkte']])
    st.subheader("Globales Ranking v7.45.3")
    st.success(f"Axiom aktiv: {AI_CYCLE_ASSUMPTION}")
    seg_filter = st.selectbox("Segment Filter", ["Alle"] + sorted(df['segment'].unique()))
    if seg_filter!= "Alle":
        df_show = df[df['segment']==seg_filter].copy()
    else:
        df_show = df.copy()
    show_cols = ['Rang','Ticker','name','flag','segment','typ','Capex_Bias','Aktueller_Kurs','Forward_KGV','EV_EBITDA','Umsatz_Wachstum','Bruttomarge','Operating_Margin','FCF_Marge','Finanzscore','Gesamtscore','Investment_Rating']
    df_show = df_show[show_cols]
    format_dict = {c: lambda x: "N/A" if pd.isna(x) else f"{x:.2f}" for c in PFLICHT_KPIS + ['Finanzscore','Gesamtscore']}
    format_dict['Rang'] = lambda x: f"{int(x)}"
    format_dict['Capex_Bias'] = lambda x: f"{int(x):+d}P"
    styled_df = df_show.style.map(highlight_na).format(format_dict)
    st.table(styled_df)
    output=io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranking_v7.45.3")
    st.download_button("📥 Excel herunterladen", output.getvalue(), file_name=f"AI_Ranking_v7.45.3_{datetime.now().strftime('%Y-%m-%d')}.xlsx", use_container_width=True)
    if st.button("⬅️ Zurueck zur Liste"):
        st.session_state.modus = "sammeln"
        st.rerun()

# ============================================
# 6. APP START
# ============================================
if st.session_state.modus == "sammeln":
    screen_sammeln()
elif st.session_state.modus == "abfrage":
    screen_abfrage()
elif st.session_state.modus == "ranking":
    screen_ranking()
