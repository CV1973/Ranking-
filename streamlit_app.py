import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
from datetime import datetime, timedelta
import time
import io

VERSION = "v3.1 Levermann Fix"
DB_NAME = "ranking_db.json"

# --- 1. KONFIGURATION ---
AI_CYCLE_ASSUMPTION = "OpMargin 30% als Proxy für 2026 KI-CapEx Zyklus"

STOCK_UNIVERSE = [
    {"ticker": "NVDA", "name": "NVIDIA", "flag": "🇺🇸", "segment": "Chipdesign", "typ": "Empfänger"},
    {"ticker": "AMD", "name": "AMD", "flag": "🇺🇸", "segment": "Chipdesign", "typ": "Empfänger"},
    {"ticker": "AVGO", "name": "Broadcom", "flag": "🇺🇸", "segment": "Chipdesign", "typ": "Empfänger"},
    {"ticker": "MRVL", "name": "Marvell", "flag": "🇺🇸", "segment": "Chipdesign", "typ": "Empfänger"},
    {"ticker": "INTC", "name": "Intel", "flag": "🇺🇸", "segment": "Chipdesign", "typ": "Empfänger"},
    {"ticker": "MU", "name": "Micron", "flag": "🇺🇸", "segment": "Speicher", "typ": "Empfänger"},
    {"ticker": "SKHY", "name": "SK Hynix", "flag": "🇰🇷", "segment": "Speicher", "typ": "Empfänger"},
    {"ticker": "WDC", "name": "Western Digital", "flag": "🇺🇸", "segment": "Speicher", "typ": "Empfänger"},
    {"ticker": "STX", "name": "Seagate", "flag": "🇺🇸", "segment": "Speicher", "typ": "Empfänger"},
    {"ticker": "ASML", "name": "ASML", "flag": "🇳🇱", "segment": "Ausrüster", "typ": "Empfänger"},
    {"ticker": "AMAT", "name": "Applied Materials", "flag": "🇺🇸", "segment": "Ausrüster", "typ": "Empfänger"},
    {"ticker": "LRCX", "name": "Lam Research", "flag": "🇺🇸", "segment": "Ausrüster", "typ": "Empfänger"},
    {"ticker": "KLAC", "name": "KLA", "flag": "🇺🇸", "segment": "Ausrüster", "typ": "Empfänger"},
    {"ticker": "TER", "name": "Teradyne", "flag": "🇺🇸", "segment": "Ausrüster", "typ": "Empfänger"},
    {"ticker": "TSM", "name": "TSMC", "flag": "🇹🇼", "segment": "Foundry", "typ": "Empfänger"},
    {"ticker": "GFS", "name": "GlobalFoundries", "flag": "🇺🇸", "segment": "Foundry", "typ": "Empfänger"},
    {"ticker": "DELL", "name": "Dell", "flag": "🇺🇸", "segment": "Server", "typ": "Empfänger"},
    {"ticker": "SMCI", "name": "Super Micro", "flag": "🇺🇸", "segment": "Server", "typ": "Empfänger"},
    {"ticker": "ETN", "name": "Eaton", "flag": "🇺🇸", "segment": "Strom", "typ": "Empfänger"},
    {"ticker": "VRT", "name": "Vertiv", "flag": "🇺🇸", "segment": "Kühlung", "typ": "Empfänger"},
    {"ticker": "BE", "name": "Bloom Energy", "flag": "🇺🇸", "segment": "Strom", "typ": "Empfänger"},
    {"ticker": "GEV", "name": "GE Vernova", "flag": "🇺🇸", "segment": "Strom", "typ": "Empfänger"},
    {"ticker": "CEG", "name": "Constellation", "flag": "🇺🇸", "segment": "Strom", "typ": "Empfänger"},
    {"ticker": "TXN", "name": "Texas Instruments", "flag": "🇺🇸", "segment": "Analog", "typ": "Empfänger"},
    {"ticker": "ANET", "name": "Arista", "flag": "🇺🇸", "segment": "Netzwerk", "typ": "Empfänger"},
    {"ticker": "CRDO", "name": "Credo", "flag": "🇺🇸", "segment": "Netzwerk", "typ": "Empfänger"},
    {"ticker": "COHR", "name": "Coherent", "flag": "🇺🇸", "segment": "Optik", "typ": "Empfänger"},
    {"ticker": "LITE", "name": "Lumentum", "flag": "🇺🇸", "segment": "Optik", "typ": "Empfänger"},
    {"ticker": "CSCO", "name": "Cisco", "flag": "🇺🇸", "segment": "Netzwerk", "typ": "Neutral"},
    {"ticker": "MSFT", "name": "Microsoft", "flag": "🇺🇸", "segment": "Hyperscaler", "typ": "Spender"},
    {"ticker": "AMZN", "name": "Amazon", "flag": "🇺🇸", "segment": "Hyperscaler", "typ": "Spender"},
    {"ticker": "GOOGL", "name": "Alphabet", "flag": "🇺🇸", "segment": "Hyperscaler", "typ": "Spender"},
    {"ticker": "META", "name": "Meta", "flag": "🇺🇸", "segment": "Hyperscaler", "typ": "Spender"},
    {"ticker": "ORCL", "name": "Oracle", "flag": "🇺🇸", "segment": "Software", "typ": "Spender"},
    {"ticker": "NOW", "name": "ServiceNow", "flag": "🇺🇸", "segment": "Software", "typ": "Spender"},
    {"ticker": "EQIX", "name": "Equinix", "flag": "🇺🇸", "segment": "Rechenzentrum", "typ": "Neutral"},
    {"ticker": "DLR", "name": "Digital Realty", "flag": "🇺🇸", "segment": "Rechenzentrum", "typ": "Neutral"},
    {"ticker": "PLTR", "name": "Palantir", "flag": "🇺🇸", "segment": "Software", "typ": "Spender"},
]

# --- 2. SESSION STATE & DB FUNKTIONEN ---
def init_session_state():
    if 'datenbank' not in st.session_state:
        st.session_state.datenbank = {}
    if 'aktien_liste' not in st.session_state:
        st.session_state.aktien_liste = [s["ticker"] for s in STOCK_UNIVERSE]
    if 'modus' not in st.session_state:
        st.session_state.modus = "sammeln"
    if 'abfrage_queue' not in st.session_state:
        st.session_state.abfrage_queue = []
    if 'abfrage_index' not in st.session_state:
        st.session_state.abfrage_index = 0

def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        st.session_state.datenbank[ticker] = {
            "meta": next((s for s in STOCK_UNIVERSE if s["ticker"] == ticker), {}),
            "daten": {"Ticker": ticker},
            "quellen": {},
            "status": "leer"
        }

def save_kpi(ticker, kpi_name, wert, quelle):
    init_ticker(ticker)
    st.session_state.datenbank[ticker]["daten"][kpi_name] = wert
    st.session_state.datenbank[ticker]["quellen"][kpi_name] = quelle

def lade_levermann_aus_datei():
    try:
        df_lev = pd.read_csv('Levermann.txt', header=None, names=['Ticker', 'Wert'])
        df_lev['Ticker'] = df_lev['Ticker'].str.strip().str.upper()
        levermann_dict = df_lev.set_index('Ticker')['Wert'].to_dict()

        geladen = 0
        for ticker, wert in levermann_dict.items():
            if ticker in st.session_state.aktien_liste and not pd.isna(wert):
                init_ticker(ticker) # FIX: Sicherheitshalber init
                save_kpi(ticker, "Levermann", float(wert), "TXT-Datei")
                st.session_state.datenbank[ticker]["daten"]["Levermann"] = float(wert)
                geladen += 1
        if geladen > 0:
            st.success(f"Levermann.txt geladen: {geladen} Werte")
        else:
            st.warning("Levermann.txt geladen aber 0 Werte gefunden")
    except FileNotFoundError:
        st.warning("Levermann.txt nicht gefunden. Lege die Datei im Repo Root an.")
    except Exception as e:
        st.error(f"Fehler beim Laden der Levermann.txt: {e}")
        # --- 3. DATENABFRAGE ---
def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        return int(r.json()['data'][0]['value'])
    except:
        return 50

def yahoo_laden(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        fin = t.financials

        save_kpi(ticker, "Marktkap_Mrd", info.get('marketCap', 0) / 1e9, "Yahoo")
        save_kpi(ticker, "Kurs", info.get('currentPrice', 0), "Yahoo")
        save_kpi(ticker, "Beta", info.get('beta', 1), "Yahoo")
        save_kpi(ticker, "KGV", info.get('trailingPE', 0), "Yahoo")
        save_kpi(ticker, "KBV", info.get('priceToBook', 0), "Yahoo")
        save_kpi(ticker, "Div_Rendite", info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0, "Yahoo")

        if not fin.empty:
            revenue = fin.loc['Total Revenue'].iloc[0] if 'Total Revenue' in fin.index else 0
            op_income = fin.loc['Operating Income'].iloc[0] if 'Operating Income' in fin.index else 0
            save_kpi(ticker, "Umsatz_Mrd", revenue / 1e9, "Yahoo")
            save_kpi(ticker, "OpMargin", (op_income / revenue * 100) if revenue > 0 else 0, "Yahoo")
            save_kpi(ticker, "FCF_Mrd", info.get('freeCashflow', 0) / 1e9, "Yahoo")

        st.session_state.datenbank[ticker]["status"] = "geladen"
        return True
    except Exception as e:
        st.warning(f"Yahoo Fehler bei {ticker}: {e}")
        return False

def berechne_kpis(ticker):
    obj = st.session_state.datenbank[ticker]
    d = obj["daten"]

    opm = d.get("OpMargin", 0)
    save_kpi(ticker, "OpMargin_Score", min(10, max(0, opm / 3)), "Berechnet")

    lev = d.get("Levermann", np.nan)
    save_kpi(ticker, "Levermann_Score", lev if not pd.isna(lev) else 0, "TXT")

    score = 0
    score += d.get("OpMargin_Score", 0) * 0.5
    score += d.get("Levermann_Score", 0) * 0.5

    if lev == 0:
        score *= 0.8

    save_kpi(ticker, "Gesamtscore", round(score, 2), "Berechnet")

    rating = "Halten"
    if score > 7: rating = "Kaufen"
    elif score < 3: rating = "Verkaufen"
    save_kpi(ticker, "Investment_Rating", rating, "Berechnet")

def baue_abfrage_queue():
    st.session_state.abfrage_queue = []
    for ticker in st.session_state.aktien_liste:
        obj = st.session_state.datenbank.get(ticker, {})
        if obj.get("status")!= "geladen":
            st.session_state.abfrage_queue.append({"ticker": ticker, "typ": "Yahoo"})
        if pd.isna(obj.get("daten", {}).get("Levermann")):
            st.session_state.abfrage_queue.append({"ticker": ticker, "typ": "Levermann"})
            # --- 4. SCREENS ---
def screen_sammeln():
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');.stTable {font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif;}</style>""", unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col1: st.title(f"AI Infrastructure Ranking {VERSION}")
    with col2: st.markdown(""); st.markdown("[📄 README](https://github.com/CV1973/Ranking-/blob/main/README.md)")

    fear_greed = get_fear_greed()
    st.info(f"**Axiom:** {AI_CYCLE_ASSUMPTION} | Fear&Greed: {fear_greed} | **OpMargin: 30%**")

    if st.button("🔄 Levermann.txt neu laden"):
        for t in st.session_state.aktien_liste: init_ticker(t)
        lade_levermann_aus_datei()
        st.rerun()

    st.subheader(
        f"Universum: {len([s for s in STOCK_UNIVERSE if s['typ']=='Empfänger'])} Empfänger + "
        f"{len([s for s in STOCK_UNIVERSE if s['typ']=='Spender'])} Spender + "
        f"{len([s for s in STOCK_UNIVERSE if s['typ']=='Neutral'])} Neutral = {len(STOCK_UNIVERSE)} US/ADR Werte"
    )
    df_meta = pd.DataFrame([s for s in STOCK_UNIVERSE if s["ticker"] in st.session_state.aktien_liste])
    st.table(df_meta[['ticker', 'name', 'flag', 'segment', 'typ']])

    if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
        with st.spinner("Initialisiere DB + lade Levermann.txt..."):
            # FIX: Erst alle init, dann Levermann, dann Queue
            for t in st.session_state.aktien_liste: init_ticker(t)
            lade_levermann_aus_datei()
            baue_abfrage_queue()
        st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
        st.session_state.abfrage_index = 0
        st.rerun()

def screen_abfrage():
    st.title("Datenabfrage")
    if st.session_state.abfrage_index >= len(st.session_state.abfrage_queue):
        st.session_state.modus = "ranking"
        st.rerun()
        return

    item = st.session_state.abfrage_queue[st.session_state.abfrage_index]
    ticker = item["ticker"]
    st.progress(st.session_state.abfrage_index / len(st.session_state.abfrage_queue), text=f"{st.session_state.abfrage_index+1}/{len(st.session_state.abfrage_queue)}: {ticker} - {item['typ']}")

    if item["typ"] == "Yahoo":
        yahoo_laden(ticker)

    st.session_state.abfrage_index += 1
    time.sleep(0.2)
    st.rerun()

def screen_ranking():
    st.title("Ranking Ergebnis")

    daten_liste = []
    for ticker in st.session_state.aktien_liste:
        obj = st.session_state.datenbank.get(ticker)
        if obj and obj.get("status") == "geladen":
            berechne_kpis(ticker)
            row = obj["meta"].copy()
            row.update(obj["daten"])
            daten_liste.append(row)

    if not daten_liste:
        st.error("Keine Daten vorhanden. Bitte Datenabfrage durchführen.")
        if st.button("Zurück zum Start"): st.session_state.modus = "sammeln"; st.rerun()
        return

    df = pd.DataFrame(daten_liste)
    df['Levermann'] = df.get('Levermann', np.nan)
    df['Investment_Rating'] = df.get('Investment_Rating', 'N/A - Daten fehlen')
    df = df.sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    df.index = df.index + 1

    st.subheader("Top 10 Ranking")
    show_cols = ['Ticker', 'name', 'flag', 'segment', 'typ', 'Gesamtscore', 'Investment_Rating', 'Levermann', 'OpMargin']
    st.dataframe(df[show_cols], use_container_width=True)

    fehlende = df[df['Levermann'].isna()]
    if not fehlende.empty:
        st.warning(f"{len(fehlende)} Werte haben keinen Levermann Score")
        st.table(fehlende[['Ticker', 'name', 'flag']])

    buffer = io.BytesIO()
    df.to_excel(buffer, index=True)
    st.download_button("📥 Ranking als Excel", buffer, "ranking.xlsx", "application/vnd.ms-excel")

    if st.button("🔄 Neue Auswertung"): st.session_state.modus = "sammeln"; st.rerun()

# --- 5. MAIN ---
def main():
    init_session_state()
    if st.session_state.modus == "sammeln": screen_sammeln()
    elif st.session_state.modus == "abfrage": screen_abfrage()
    elif st.session_state.modus == "ranking": screen_ranking()

if __name__ == "__main__":
    main()
        
