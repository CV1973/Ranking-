# ============================================
# AI Infrastructure CAPEX Cycle Ranking v7.47.0-US
# KISS VERSION
#
# Änderungen ggü. v7.46.2:
# 1) Performance_52W entfernt
# 2) Levermann nur aus Levermann.txt
# 3) Levermann Faktor max. 1.10
# 4) CAPEX_Bias +/-5 statt +/-10
# 5) Horizont: CAPEX Zyklus bis Ende 2027
# ============================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import warnings
import fear_and_greed

warnings.filterwarnings("ignore")


# ============================================
# 0. LOGIN SCHUTZ
# ============================================

def check_password():

    def password_entered():
        expected = st.secrets.get("app_password", None)

        if expected is not None and st.session_state["password"] == expected:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        if st.secrets.get("app_password", None) is None:
            st.error("Kein Passwort in st.secrets konfiguriert.")
            st.stop()

        if "password_correct" not in st.session_state:

            st.text_input(
                "Passwort",
                type="password",
                on_change=password_entered,
                key="password"
            )
            st.stop()

        elif not st.session_state["password_correct"]:

            st.text_input(
                "Passwort",
                type="password",
                on_change=password_entered,
                key="password"
            )

            st.error("Passwort falsch")
            st.stop()

        else:
            return True


check_password()


st.set_page_config(
    page_title="AI Infrastructure CAPEX Cycle Ranking 2027",
    layout="wide"
)


VERSION = "v7.47.0-US"

AI_CYCLE_ASSUMPTION = (
    "CAPEX BOOM BIS ENDE 2027 - INFRASTRUKTUR EMPFÄNGER PROFITIEREN"
)


# ============================================
# 1. SESSION STATE
# ============================================

DEFAULTS = {

    "aktien_liste": [],
    "datenbank": {},
    "modus": "sammeln",
    "abfrage_queue": [],
    "version_loaded": "",
    "levermann_txt": {}

}


for key, value in DEFAULTS.items():

    if key not in st.session_state:
        st.session_state[key] = value



if st.session_state.version_loaded != VERSION:

    for key, value in DEFAULTS.items():
        st.session_state[key] = value

    st.session_state.version_loaded = VERSION



# ============================================
# 2. STOCK UNIVERSUM
# ============================================

STOCK_UNIVERSE = [


{"ticker":"NVDA","name":"Nvidia",
"country":"USA","flag":"🇺🇸",
"segment":"AI Compute","typ":"Empfänger"},


{"ticker":"AMD","name":"AMD",
"country":"USA","flag":"🇺🇸",
"segment":"AI Compute","typ":"Empfänger"},


{"ticker":"AVGO","name":"Broadcom",
"country":"USA","flag":"🇺🇸",
"segment":"AI Compute","typ":"Empfänger"},


{"ticker":"MRVL","name":"Marvell",
"country":"USA","flag":"🇺🇸",
"segment":"AI Compute","typ":"Empfänger"},


{"ticker":"INTC","name":"Intel",
"country":"USA","flag":"🇺🇸",
"segment":"AI Compute","typ":"Empfänger"},


{"ticker":"MU","name":"Micron",
"country":"USA","flag":"🇺🇸",
"segment":"Memory / HBM","typ":"Empfänger"},


{"ticker":"SKHY","name":"SK Hynix ADR",
"country":"South Korea","flag":"🇰🇷",
"segment":"Memory / HBM","typ":"Empfänger"},


{"ticker":"WDC","name":"Western Digital",
"country":"USA","flag":"🇺🇸",
"segment":"Memory / HBM","typ":"Empfänger"},


{"ticker":"STX","name":"Seagate",
"country":"USA","flag":"🇺🇸",
"segment":"Memory / HBM","typ":"Empfänger"},


{"ticker":"ASML","name":"ASML ADR",
"country":"Netherlands","flag":"🇳🇱",
"segment":"Semi Equipment","typ":"Empfänger"},


{"ticker":"AMAT","name":"Applied Materials",
"country":"USA","flag":"🇺🇸",
"segment":"Semi Equipment","typ":"Empfänger"},


{"ticker":"LRCX","name":"Lam Research",
"country":"USA","flag":"🇺🇸",
"segment":"Semi Equipment","typ":"Empfänger"},


{"ticker":"KLAC","name":"KLA",
"country":"USA","flag":"🇺🇸",
"segment":"Semi Equipment","typ":"Empfänger"},


{"ticker":"TER","name":"Teradyne",
"country":"USA","flag":"🇺🇸",
"segment":"Semi Equipment","typ":"Empfänger"},


{"ticker":"TSM","name":"TSMC ADR",
"country":"Taiwan","flag":"🇹🇼",
"segment":"Foundry","typ":"Empfänger"},


{"ticker":"TXN","name":"Texas Instruments",
"country":"USA","flag":"🇺🇸",
"segment":"Analog Semiconductor","typ":"Empfänger"},


{"ticker":"PLTR","name":"Palantir",
"country":"USA","flag":"🇺🇸",
"segment":"AI Application Layer","typ":"Neutral"},


{"ticker":"MSFT","name":"Microsoft",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"AMZN","name":"Amazon",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"GOOGL","name":"Alphabet",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"META","name":"Meta",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"ORCL","name":"Oracle",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"NOW","name":"ServiceNow",
"country":"USA","flag":"🇺🇸",
"segment":"Cloud / AI Platform","typ":"Spender"},


{"ticker":"EQIX","name":"Equinix",
"country":"USA","flag":"🇺🇸",
"segment":"Data Center","typ":"Spender"},


{"ticker":"DLR","name":"Digital Realty",
"country":"USA","flag":"🇺🇸",
"segment":"Data Center","typ":"Spender"}

]


if len(st.session_state.aktien_liste) == 0:

    st.session_state.aktien_liste = [
        x["ticker"] for x in STOCK_UNIVERSE
    ]


# ============================================
# 3. CAPEX LOGIK
# ============================================

CAPEX_BIAS = {

    "Empfänger": 5,
    "Spender": -5,
    "Neutral": 0

}



# ============================================
# 4. GEWICHTUNG
# ============================================

WEIGHTS = {


"Empfänger": {

"Forward_KGV":0.15,
"EV_EBITDA":0.10,
"Umsatz_Wachstum":0.25,
"Bruttomarge":0.10,
"Operating_Margin":0.25,
"FCF_Marge":0.05,
"NetDebt_EBITDA":0.10

},


"Spender": {

"Forward_KGV":0.15,
"EV_EBITDA":0.10,
"Umsatz_Wachstum":0.10,
"Bruttomarge":0.15,
"Operating_Margin":0.25,
"FCF_Marge":0.15,
"NetDebt_EBITDA":0.10

},


"Neutral": {

"Forward_KGV":0.15,
"EV_EBITDA":0.15,
"Umsatz_Wachstum":0.15,
"Bruttomarge":0.15,
"Operating_Margin":0.15,
"FCF_Marge":0.15,
"NetDebt_EBITDA":0.10

}

}


PFLICHT_KPIS = [

"Forward_KGV",
"EV_EBITDA",
"Umsatz_Wachstum",
"Bruttomarge",
"Operating_Margin",
"FCF_Marge",
"NetDebt_EBITDA"

]


KPI_LABELS = {

"Forward_KGV":"Forward KGV",
"EV_EBITDA":"EV/EBITDA",
"Umsatz_Wachstum":"Umsatzwachstum",
"Bruttomarge":"Bruttomarge",
"Operating_Margin":"Operating Margin",
"FCF_Marge":"FCF Marge",
"NetDebt_EBITDA":"Net Debt/EBITDA",
"Aktueller_Kurs":"Aktueller Kurs"

}


# ============================================
# LEVERMANN TXT
# ============================================

def lade_levermann_aus_datei():

    try:

        df_lev = pd.read_csv(
            "Levermann.txt",
            header=None,
            names=["Ticker","Wert"]
        )

        df_lev["Ticker"] = (
            df_lev["Ticker"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df_lev["Wert"] = pd.to_numeric(
            df_lev["Wert"],
            errors="coerce"
        )


        if df_lev["Wert"].isna().any():

            st.warning(
                "Ungültige Levermann Werte in TXT gefunden"
            )


        st.session_state.levermann_txt = (
            df_lev
            .dropna()
            .set_index("Ticker")["Wert"]
            .to_dict()
        )


    except Exception:

        st.error(
            "Levermann.txt fehlt oder ist fehlerhaft"
        )

        st.stop()



def berechne_levermann_faktor(score):

    if pd.isna(score):

        return 1.0


    score=float(score)


    if score >= 6:
        return 1.10

    elif score >=4:
        return 1.05

    elif score >=0:
        return 1.00

    else:
        return 0.95


#ende block1
# ============================================
# 5. HELPER
# ============================================

@st.cache_data(ttl=7200)
def get_fear_greed():

    try:
        return round(fear_and_greed.get().value)

    except:
        return 50



def safe_get(info, key):

    try:

        value = info.get(key)

        if value is None:
            return np.nan

        return value

    except:

        return np.nan



def parse_number(text):

    if text is None:
        return np.nan

    text = str(text).strip().replace(",", ".")

    try:
        return float(text)

    except:
        return np.nan



def init_ticker(ticker):

    if ticker not in st.session_state.datenbank:

        meta = next(
            (
                x for x in STOCK_UNIVERSE
                if x["ticker"] == ticker
            ),
            {
                "ticker":ticker,
                "name":ticker
            }
        )


        st.session_state.datenbank[ticker] = {

            "daten":{
                "Ticker":ticker,
                **meta
            },

            "audit":{},
            "status":"neu"

        }



def save_kpi(ticker, kpi, value, quelle):

    obj = st.session_state.datenbank[ticker]

    obj["daten"][kpi] = value


    obj["audit"][kpi] = {

        "Wert":value,
        "Quelle":quelle,
        "Zeit":datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Version":VERSION

    }



# ============================================
# 6. YAHOO DATEN
# ============================================

@st.cache_data(ttl=7200, show_spinner=False)
def yahoo_laden(ticker):

    try:

        time.sleep(0.2)

        tk = yf.Ticker(ticker)

        info = tk.info or {}

        fin = tk.financials

        cf = tk.cashflow



        price = (
            safe_get(info,"currentPrice")
            or safe_get(info,"regularMarketPrice")
            or safe_get(info,"previousClose")
        )


        currency = safe_get(info,"currency")


        forward_kgv = safe_get(
            info,
            "forwardPE"
        )


        ev_ebitda = safe_get(
            info,
            "enterpriseToEbitda"
        )


        umsatz_wachstum = safe_get(
            info,
            "revenueGrowth"
        )


        brutto = safe_get(
            info,
            "grossMargins"
        )


        op_marge = safe_get(
            info,
            "operatingMargins"
        )


        fcf = safe_get(
            info,
            "freeCashflow"
        )


        revenue = safe_get(
            info,
            "totalRevenue"
        )


        if pd.isna(revenue) and not fin.empty:

            revenue = fin.iloc[0,0]


        if (
            pd.isna(fcf)
            and not cf.empty
            and "Free Cash Flow" in cf.index
        ):

            fcf = cf.loc[
                "Free Cash Flow"
            ].iloc[0]



        fcf_marge = np.nan


        if (
            not pd.isna(fcf)
            and not pd.isna(revenue)
            and revenue != 0
        ):

            fcf_marge = fcf / revenue



        if (
            pd.isna(brutto)
            and not fin.empty
            and "Gross Profit" in fin.index
            and "Total Revenue" in fin.index
        ):

            try:

                brutto = (
                    fin.loc["Gross Profit"].iloc[0]
                    /
                    fin.loc["Total Revenue"].iloc[0]
                )

            except:
                pass



        if (
            pd.isna(op_marge)
            and not fin.empty
            and "Operating Income" in fin.index
            and "Total Revenue" in fin.index
        ):

            try:

                op_marge = (
                    fin.loc["Operating Income"].iloc[0]
                    /
                    fin.loc["Total Revenue"].iloc[0]
                )

            except:
                pass



        total_debt = safe_get(
            info,
            "totalDebt"
        )

        total_cash = safe_get(
            info,
            "totalCash"
        )

        ebitda = safe_get(
            info,
            "ebitda"
        )


        netdebt_ebitda = np.nan


        if (
            not pd.isna(total_debt)
            and not pd.isna(total_cash)
            and not pd.isna(ebitda)
            and ebitda > 0
        ):

            netdebt_ebitda = (
                total_debt - total_cash
            ) / ebitda



        return {

            "Aktueller_Kurs":price,
            "Waehrung":currency,
            "Forward_KGV":forward_kgv,
            "EV_EBITDA":ev_ebitda,
            "Umsatz_Wachstum":umsatz_wachstum,
            "Bruttomarge":brutto,
            "Operating_Margin":op_marge,
            "FCF_Marge":fcf_marge,
            "NetDebt_EBITDA":netdebt_ebitda

        }



    except Exception:

        return None




def fehlende_kpis(ticker):

    daten = (
        st.session_state
        .datenbank[ticker]["daten"]
    )


    return [

        kpi
        for kpi in PFLICHT_KPIS
        if pd.isna(
            daten.get(kpi,np.nan)
        )

    ]



def baue_abfrage_queue():

    queue=[]


    for ticker in st.session_state.aktien_liste:


        init_ticker(ticker)


        obj = st.session_state.datenbank[ticker]


        if obj["status"]=="neu":


            daten = yahoo_laden(ticker)


            if daten:


                for kpi, wert in daten.items():

                    if not pd.isna(wert):

                        save_kpi(
                            ticker,
                            kpi,
                            wert,
                            "Yahoo"
                        )


            obj["status"]="geladen"



        for kpi in fehlende_kpis(ticker):

            queue.append(
                (ticker,kpi)
            )


    st.session_state.abfrage_queue = queue




# ============================================
# 7. SCORING ENGINE
# ============================================

def normalize_global(
    df,
    col,
    higher_better=True
):


    s = pd.to_numeric(
        df[col],
        errors="coerce"
    )


    valid=s.dropna()


    if len(valid)<2:

        return pd.Series(
            np.nan,
            index=s.index
        )


    x=s.copy()


    if not higher_better:

        x=-x


    return x.rank(
        pct=True
    )




def calculate_scores(df):


    df["Datenpunkte"] = (
        df[PFLICHT_KPIS]
        .notna()
        .sum(axis=1)
    )


    df["Vollständig"] = (
        df["Datenpunkte"]
        ==
        len(PFLICHT_KPIS)
    )


    df["Datenqualität"] = (
        df["Datenpunkte"]
        /
        len(PFLICHT_KPIS)
    )


    df["Capex_Bias"] = (
        df["typ"]
        .map(CAPEX_BIAS)
    )



    for col in PFLICHT_KPIS:


        lower_better = col in [

            "Forward_KGV",
            "EV_EBITDA",
            "NetDebt_EBITDA"

        ]


        df[f"Norm_{col}"] = normalize_global(

            df,
            col,
            not lower_better

        )



    df["Finanzscore"]=0.0



    for idx,row in df.iterrows():


        weights = WEIGHTS[row["typ"]]

        score=0


        for col,w in weights.items():


            value=row[f"Norm_{col}"]


            if not pd.isna(value):

                score += value*w



        df.at[idx,"Finanzscore"] = score*100




    df["Gesamtscore_Roh"] = (
        df["Finanzscore"]*0.9
    )



    # Levermann nur TXT
    df["Levermann"] = df["Ticker"].apply(

        lambda x:
        st.session_state.levermann_txt.get(
            x,
            np.nan
        )

    )


    df["Levermann_Faktor"] = (

        df["Levermann"]
        .apply(
            berechne_levermann_faktor
        )

    )



    df["Gesamtscore_Roh_mit_Lev"] = (

        df["Gesamtscore_Roh"]
        *
        df["Levermann_Faktor"]

    )



    df["Gesamtscore"] = (

        df["Gesamtscore_Roh_mit_Lev"]
        *
        (
            0.3
            +
            0.7*df["Datenqualität"]
        )
        +
        df["Capex_Bias"]

    ).round(1)



    df=df.sort_values(

        "Gesamtscore",
        ascending=False,
        na_position="last"

    ).reset_index(drop=True)



    df["Rang"]=df.index+1


    return df




def get_investment_rating(score, vollständig):

    if pd.isna(score):

        return "N/A"


    if not vollständig:

        return "N/A - Daten fehlen"


    if score >=80:

        return "Strong Buy"

    elif score >=65:

        return "Buy"

    elif score >=45:

        return "Hold"

    else:

        return "Sell"



def highlight_na(val):

    return (
        "background-color: #FFF9C4"
        if pd.isna(val)
        else ""
    )


#ende block2
# ============================================
# 8. SCREENS
# ============================================


def screen_sammeln():


    st.markdown(
        """
        <style>
        @import url(
        'https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap'
        );

        .stTable {
        font-family:
        'Noto Color Emoji',
        'Apple Color Emoji',
        'Segoe UI Emoji',
        sans-serif;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    col1,col2 = st.columns([4,1])


    with col1:

        st.title(
            f"AI Infrastructure CAPEX Cycle Ranking 2027 {VERSION}"
        )


    with col2:

        st.markdown(
            "[📄 README](https://github.com/CV1973/Ranking-/blob/main/README.md)"
        )


    fear = get_fear_greed()


    st.info(
        f"""
        **Axiom:** {AI_CYCLE_ASSUMPTION}

        | Fear&Greed: {fear}

        | Horizont: Ende 2027
        """
    )



    empfänger = len(
        [
            x for x in STOCK_UNIVERSE
            if x["typ"]=="Empfänger"
        ]
    )


    spender = len(
        [
            x for x in STOCK_UNIVERSE
            if x["typ"]=="Spender"
        ]
    )


    neutral = len(
        [
            x for x in STOCK_UNIVERSE
            if x["typ"]=="Neutral"
        ]
    )


    st.subheader(

        f"Universum: {empfänger} Empfänger + "
        f"{spender} Spender + "
        f"{neutral} Neutral"

    )


    df_meta=pd.DataFrame(

        [
            x for x in STOCK_UNIVERSE
            if x["ticker"]
            in st.session_state.aktien_liste
        ]

    )


    st.table(

        df_meta[
            [
                "ticker",
                "name",
                "flag",
                "segment",
                "typ"
            ]
        ]

    )



    if st.button(
        "✅ Auswertung starten",
        type="primary",
        use_container_width=True
    ):


        with st.spinner(
            "Lade Yahoo + Levermann TXT..."
        ):


            lade_levermann_aus_datei()

            baue_abfrage_queue()


            if len(st.session_state.abfrage_queue)>0:

                st.session_state.modus="abfrage"

            else:

                st.session_state.modus="ranking"


        st.rerun()





def screen_abfrage():


    if len(st.session_state.abfrage_queue)==0:

        st.session_state.modus="ranking"

        st.rerun()

        return



    ticker,kpi = (
        st.session_state.abfrage_queue[0]
    )


    st.error(
        f"Fehlender Wert: {ticker} - {KPI_LABELS[kpi]}"
    )


    st.write(
        f"Noch {len(st.session_state.abfrage_queue)} fehlende KPIs"
    )



    eingabe = st.text_input(
        "Wert eingeben"
    )



    col1,col2,col3 = st.columns(3)



    with col1:


        if st.button("💾 Speichern"):


            wert=parse_number(eingabe)


            if pd.isna(wert):

                st.error(
                    "Keine gültige Zahl"
                )

                return



            save_kpi(
                ticker,
                kpi,
                wert,
                "Manuell"
            )


            st.session_state.abfrage_queue.pop(0)

            st.rerun()



    with col2:


        if st.button("⏭️ Überspringen"):


            save_kpi(
                ticker,
                kpi,
                np.nan,
                "Übersprungen"
            )


            st.session_state.abfrage_queue.pop(0)

            st.rerun()



    with col3:


        if st.button(
            "⏭️⏭️ Alle überspringen"
        ):


            for t,k in st.session_state.abfrage_queue:

                save_kpi(
                    t,
                    k,
                    np.nan,
                    "Bulk Übersprungen"
                )


            st.session_state.abfrage_queue=[]

            st.session_state.modus="ranking"

            st.rerun()





def screen_ranking():


    st.markdown(
        """
        <style>
        @import url(
        'https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap'
        );

        .stTable {
        font-family:
        'Noto Color Emoji',
        'Apple Color Emoji',
        'Segoe UI Emoji',
        sans-serif;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    col1,col2 = st.columns([4,1])


    with col1:

        st.title(
            f"AI Infrastructure CAPEX Cycle Ranking 2027 {VERSION}"
        )


    with col2:

        st.markdown(
            "[📄 README](https://github.com/CV1973/Ranking-/blob/main/README.md)"
        )



    liste=[

        st.session_state.datenbank[x]["daten"]

        for x in st.session_state.aktien_liste

    ]



    df=pd.DataFrame(liste)



    if len(df)<2:

        st.error(
            "Zu wenige Aktien"
        )

        return



    df=calculate_scores(df)



    df["Investment_Rating"]=df.apply(

        lambda x:

        get_investment_rating(
            x["Gesamtscore"],
            x["Vollständig"]
        ),

        axis=1

    )



    fehlende=df[
        df["Vollständig"]==False
    ]



    if len(fehlende)>0:

        st.warning(

            f"{len(fehlende)} Werte haben fehlende Daten"

        )


        st.table(

            fehlende[
                [
                    "Ticker",
                    "name",
                    "flag",
                    "Datenpunkte"
                ]
            ]

        )



    st.subheader(
        "Globales Ranking"
    )


    st.success(
        f"Axiom aktiv: {AI_CYCLE_ASSUMPTION}"
    )


    st.caption(
        """
        Modell:
        Finanzqualität + Wachstum + Profitabilität

        CAPEX Bias:
        Empfänger +5 | Spender -5

        Levermann:
        zusätzlicher Qualitätsmultiplikator

        Horizont:
        Ende 2027
        """
    )



    seg_filter = st.selectbox(

        "Segment Filter",

        [
            "Alle"
        ]
        +
        sorted(
            df["segment"].unique()
        )

    )



    if seg_filter!="Alle":

        df_show=df[
            df["segment"]==seg_filter
        ].copy()

    else:

        df_show=df.copy()



    show_cols=[

        "Rang",
        "Ticker",
        "name",
        "flag",
        "segment",
        "typ",

        "Capex_Bias",

        "Levermann",
        "Levermann_Faktor",

        "Gesamtscore",

        "Investment_Rating",

        "Aktueller_Kurs",

        "Forward_KGV",

        "EV_EBITDA",

        "Umsatz_Wachstum",

        "Operating_Margin",

        "FCF_Marge",

        "NetDebt_EBITDA"

    ]



    show_cols=[

        x for x in show_cols

        if x in df_show.columns

    ]



    st.dataframe(

        df_show[show_cols]

        .style
        .applymap(
            highlight_na
        ),

        use_container_width=True

    )



    csv=df_show.to_csv(
        index=False
    ).encode(
        "utf-8"
    )



    st.download_button(

        "📥 CSV Export",

        csv,

        "AI_CAPEX_Ranking_2027.csv",

        "text/csv"

    )





# ============================================
# 9. APP START
# ============================================


if st.session_state.modus=="sammeln":

    screen_sammeln()


elif st.session_state.modus=="abfrage":

    screen_abfrage()


elif st.session_state.modus=="ranking":

    screen_ranking()
