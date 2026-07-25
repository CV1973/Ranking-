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

st.set_page_config(page_title="AI Infrastructure Ranking v7.45.16-TEST", layout="wide")
VERSION = "v7.45.16-TEST"

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

def yahoo_laden_test(ticker): # OHNE DELAY + MIT STOP
    st.subheader(f"Teste: {ticker}")
    try:
        tk = yf.Ticker(ticker)
        info = tk.info # KEIN DELAY

        # DEBUG OUTPUT + SOFORT STOP
        st.write(f"**Keys gefunden:** {len(info)}")

        if len(info) > 0:
            st.json({k: info[k] for k in list(info.keys())[:10]}) # Zeig erste 10 Keys

        st.error(f"STOP BEI {ticker}. App hält hier an.")
        st.stop() # <- HIER BLEIBT ES STEHEN

        return info
    except Exception as e:
        st.error(f"EXCEPTION bei {ticker}: {e}")
        st.stop()

def screen_sammeln():
    st.title(f"Yahoo Block Test {VERSION}")
    st.warning("Wir testen 1 Aktie und stoppen sofort. Kein Delay.")

    if st.button("✅ TEST STARTEN BEI SK HYNIX", type="primary"):
        yahoo_laden_test("A000660.KS")

    if st.button("✅ TEST STARTEN BEI SAMSUNG"):
        yahoo_laden_test("A005930.KS")

    if st.button("✅ TEST STARTEN BEI NVDA"):
        yahoo_laden_test("NVDA")

screen_sammeln()
