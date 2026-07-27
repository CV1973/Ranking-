import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Stock Analyse v7.45.5", layout="wide")
st.title("📊 Stock Analyse v7.45.5 + Levermann TXT")

# === SESSION STATE ===
if 'datenbank' not in st.session_state: st.session_state.datenbank = {}
if 'aktien_liste' not in st.session_state: st.session_state.aktien_liste = []
if 'modus' not in st.session_state: st.session_state.modus = "sammeln"
if 'abfrage_queue' not in st.session_state: st.session_state.abfrage_queue = []
if 'abfrage_index' not in st.session_state: st.session_state.abfrage_index = 0
if 'levermann_queue' not in st.session_state: st.session_state.levermann_queue = []
if 'levermann_index' not in st.session_state: st.session_state.levermann_index = 0
if 'levermann_txt' not in st.session_state: st.session_state.levermann_txt = {}

# === HELFER ===
def init_ticker(ticker):
    if ticker not in st.session_state.datenbank:
        st.session_state.datenbank[ticker] = {"daten": {}, "timestamp": None}

def save_kpi(ticker, kpi_name, wert, quelle):
    init_ticker(ticker)
    st.session_state.datenbank[ticker]["daten"][kpi_name] = wert
    st.session_state.datenbank[ticker]["quelle_"+kpi_name] = quelle
    st.session_state.datenbank[ticker]["timestamp"] = datetime.now().isoformat()

def lade_levermann_aus_datei():
    """Lädt TXT in Session State für Abfrage"""
    try:
        df_lev = pd.read_csv('Levermann.txt', header=None, names=['Ticker', 'Wert'], dtype={'Ticker': str, 'Wert': float})
        df_lev['Ticker'] = df_lev['Ticker'].str.strip().str.upper()
        df_lev = df_lev.dropna(subset=['Ticker'])
        st.session_state.levermann_txt = df_lev.set_index('Ticker')['Wert'].to_dict()
    except FileNotFoundError:
        st.session_state.levermann_txt = {}
        st.error("Levermann.txt nicht gefunden im Ordner")
    except Exception as e:
        st.session_state.levermann_txt = {}
        st.error(f"Fehler beim Lesen von Levermann.txt: {e}")

def berechne_levermann_faktor(lev):
    """0.8 / 1.0 / 1.1 / 1.2 / 1.3 / 1.4 Logik"""
    if pd.isna(lev): return 1.0
    try:
        lev = float(lev)
    except:
        return 1.0
    if lev < 3: return 0.8
    elif lev == 3: return 1.0
    elif lev <= 4: return 1.1
    elif lev <= 5: return 1.2
    elif lev <= 6: return 1.3
    else: return 1.4

def baue_abfrage_queue():
    """Baue Queue für fehlende KPIs nach Levermann"""
    st.session_state.abfrage_queue = []
    for ticker in st.session_state.aktien_liste:
        d = st.session_state.datenbank.get(ticker, {}).get("daten", {})
        if pd.isna(d.get("KGV")): st.session_state.abfrage_queue.append((ticker, "KGV"))
        if pd.isna(d.get("KUV")): st.session_state.abfrage_queue.append((ticker, "KUV"))
        if pd.isna(d.get("PEG")): st.session_state.abfrage_queue.append((ticker, "PEG"))

#Ende Block 1
def hole_grunddaten(ticker):
    """Holt Daten via yfinance und speichert sie"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        hist = tk.history(period="1y")

        if len(hist) < 2: raise ValueError("Keine historischen Daten")

        save_kpi(ticker, "Name", info.get("longName", ticker), "yfinance")
        save_kpi(ticker, "Sektor", info.get("sector", "N/A"), "yfinance")
        save_kpi(ticker, "Marktkap", info.get("marketCap", np.nan), "yfinance")
        save_kpi(ticker, "Beta", info.get("beta", 1.0), "yfinance")
        save_kpi(ticker, "KGV", info.get("trailingPE", np.nan), "yfinance")
        save_kpi(ticker, "KUV", info.get("priceToSalesTrailing12Months", np.nan), "yfinance")
        save_kpi(ticker, "PEG", info.get("pegRatio", np.nan), "yfinance")
        save_kpi(ticker, "KBV", info.get("priceToBook", np.nan), "yfinance")
        save_kpi(ticker, "EKQ", info.get("totalDebtToEquity", np.nan), "yfinance")
        save_kpi(ticker, "Dividendenrendite", info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0, "yfinance")
        save_kpi(ticker, "Gewinnwachstum", info.get("earningsQuarterlyGrowth", np.nan) * 100 if info.get("earningsQuarterlyGrowth") else np.nan, "yfinance")
        save_kpi(ticker, "Umsatzwachstum", info.get("revenueGrowth", np.nan) * 100 if info.get("revenueGrowth") else np.nan, "yfinance")
        save_kpi(ticker, "Operative Marge", info.get("operatingMargins", np.nan) * 100 if info.get("operatingMargins") else np.nan, "yfinance")

        vol = hist['Close'].pct_change().std() * np.sqrt(252) * 100
        mdd = ((hist['Close']/hist['Close'].cummax())-1).min() * 100
        save_kpi(ticker, "Volatilität", vol, "yfinance")
        save_kpi(ticker, "MaxDrawdown", mdd, "yfinance")
        save_kpi(ticker, "RSI", 50, "Platzhalter") # TODO: echte RSI Berechnung

    except Exception as e:
        st.warning(f"Konnte Daten für {ticker} nicht laden: {e}")

def berechne_kpis(ticker):
    """v7.45.4 Logik + Levermann Multiplikator"""
    d = st.session_state.datenbank[ticker]["daten"]

    # 1. Finanzscore v7.45.4 - Platzhalter. Hier kommt deine echte Logik rein
    finanzscore = 50.0
    if not pd.isna(d.get("KGV")) and d.get("KGV") < 20: finanzscore += 10
    if not pd.isna(d.get("KUV")) and d.get("KUV") < 5: finanzscore += 10
    if not pd.isna(d.get("PEG")) and d.get("PEG") < 1.5: finanzscore += 10

    # 2. DQ Faktor
    dq_faktor = 1.0

    # 3. Bias
    bias = 0

    # 4. Vorläufiger Score
    vorlaeufiger_score = finanzscore * 0.9 * dq_faktor + bias
    save_kpi(ticker, "Vorlaeufiger_Score", round(vorlaeufiger_score, 2), "Berechnet v7.45.4")

    # 5. NEU: Levermann Multiplikator
    lev = d.get("Levermann")
    levermann_faktor = berechne_levermann_faktor(lev)
    save_kpi(ticker, "Levermann_Faktor", levermann_faktor, "Berechnet")

    gesamtscore = vorlaeufiger_score * levermann_faktor
    save_kpi(ticker, "Gesamtscore", round(gesamtscore, 2), "Berechnet v7.45.4 + Lev")

    # 6. Rating
    if gesamtscore >= 80: rating = "Strong Buy"
    elif gesamtscore >= 65: rating = "Buy"
    elif gesamtscore >= 45: rating = "Hold"
    else: rating = "Sell"
    save_kpi(ticker, "Investment_Rating", rating, "Berechnet")

#Ende Block 2
def screen_sammeln():
    st.header("1. Aktien sammeln")
    neue_aktien = st.text_area("Tickers kommagetrennt", "AAPL, NVDA, MSFT")
    if st.button("Liste übernehmen"):
        st.session_state.aktien_liste = [x.strip().upper() for x in neue_aktien.split(",") if x.strip()]
        for t in st.session_state.aktien_liste: init_ticker(t)
        st.success(f"{len(st.session_state.aktien_liste)} Aktien geladen")
        st.rerun()

    if len(st.session_state.aktien_liste) > 0:
        st.write("Aktien:", ", ".join(st.session_state.aktien_liste))
        if st.button("✅ Auswertung starten", type="primary", use_container_width=True):
            with st.spinner("Lade Levermann.txt..."):
                lade_levermann_aus_datei()
                # Baue Queue nur mit Aktien die in TXT sind
                st.session_state.levermann_queue = [t for t in st.session_state.aktien_liste if t in st.session_state.levermann_txt]

                if len(st.session_state.levermann_queue) > 0:
                    st.session_state.modus = "levermann_abfrage"
                    st.session_state.levermann_index = 0
                else:
                    for t in st.session_state.aktien_liste: hole_grunddaten(t)
                    baue_abfrage_queue()
                    st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
                st.rerun()

def screen_levermann_abfrage():
    st.header("2a. Levermann Werte prüfen")
    i = st.session_state.levermann_index
    queue = st.session_state.levermann_queue
    if i >= len(queue):
        st.rerun()
        return

    ticker = queue[i]
    txt_wert = st.session_state.levermann_txt[ticker]
    db_wert = st.session_state.datenbank.get(ticker, {}).get("daten", {}).get("Levermann", "nicht gesetzt")

    st.info(f"**{ticker}** | Wert aus TXT: **{txt_wert}** | Aktuell in DB: **{db_wert}**")
    st.progress((i+1)/len(queue), text=f"{i+1} / {len(queue)}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Übernehmen", use_container_width=True, type="primary"):
            save_kpi(ticker, "Levermann", txt_wert, "Levermann.txt")
            st.session_state.levermann_index += 1
            if st.session_state.levermann_index >= len(queue):
                for t in st.session_state.aktien_liste: hole_grunddaten(t)
                baue_abfrage_queue()
                st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
            st.rerun()
    with col2:
        if st.button("⏭️ Überspringen", use_container_width=True):
            st.session_state.levermann_index += 1
            if st.session_state.levermann_index >= len(queue):
                for t in st.session_state.aktien_liste: hole_grunddaten(t)
                baue_abfrage_queue()
                st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
            st.rerun()
    with col3:
        if st.button("⏭️ Alle überspringen", use_container_width=True):
            for t in st.session_state.aktien_liste: hole_grunddaten(t)
            baue_abfrage_queue()
            st.session_state.modus = "abfrage" if len(st.session_state.abfrage_queue) > 0 else "ranking"
            st.rerun()

def screen_abfrage():
    st.header("2b. Fehlende KPIs manuell")
    if st.session_state.abfrage_index >= len(st.session_state.abfrage_queue):
        st.session_state.modus = "ranking"
        st.rerun()
        return

    ticker, kpi = st.session_state.abfrage_queue[st.session_state.abfrage_index]
    st.info(f"**{ticker}** - Bitte {kpi} eingeben")

    wert = st.number_input(kpi, value=0.0, step=0.1)
    if st.button("Speichern"):
        save_kpi(ticker, kpi, wert, "Manuell")
        st.session_state.abfrage_index += 1
        st.rerun()

def screen_ranking():
    st.header("3. Ranking")
    rows = []
    for ticker in st.session_state.aktien_liste:
        berechne_kpis(ticker) # neu berechnen mit Levermann
        d = st.session_state.datenbank[ticker]["daten"]
        rows.append({
            "Ticker": ticker,
            "Name": d.get("Name"),
            "Gesamtscore": d.get("Gesamtscore"),
            "Vorlaeufiger_Score": d.get("Vorlaeufiger_Score"),
            "Rating": d.get("Investment_Rating"),
            "Levermann": d.get("Levermann"),
            "Levermann_Faktor": d.get("Levermann_Faktor")
        })
    df = pd.DataFrame(rows).sort_values("Gesamtscore", ascending=False).reset_index(drop=True)
    st.dataframe(df, use_container_width=True)

def main():
    if st.session_state.modus == "sammeln":
        screen_sammeln()
    elif st.session_state.modus == "levermann_abfrage":
        screen_levermann_abfrage()
    elif st.session_state.modus == "abfrage":
        screen_abfrage()
    elif st.session_state.modus == "ranking":
        screen_ranking()

if __name__ == "__main__":
    main()
