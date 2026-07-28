# ============================================
# AI Infrastructure Ranking v7.47.0-US KISS
# Teil 1/3
#
# FIXES:
# 1) st.set_page_config an Anfang verschoben
# 2) Levermann nur aus Levermann.txt
# 3) Levermann als Multiplikator
# 4) CAPEX Zyklus bis Ende 2027 als Axiom
# 5) KISS: keine UI / kein Speichern Levermann
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
# 0. STREAMLIT CONFIG
# ============================================

st.set_page_config(
    page_title="AI Infrastructure Ranking v7.47.0-US",
    layout="wide"
)


VERSION = "v7.47.0-US"

AI_CYCLE_ASSUMPTION = (
    "CAPEX BOOM BIS ENDE 2027 - "
    "INFRASTRUKTUR EMPFÄNGER PROFITIEREN"
)


# ============================================
# 1. LOGIN
# ============================================

def check_password():

    def password_entered():

        expected = st.secrets.get(
            "app_password",
            None
        )

        if expected is not None and \
           st.session_state["password"] == expected:

            st.session_state[
                "password_correct"
            ] = True

            del st.session_state["password"]

        else:

            st.session_state[
                "password_correct"
            ] = False



    if st.secrets.get(
        "app_password",
        None
    ) is None:

        st.error(
            "Kein Passwort in st.secrets konfiguriert."
        )

        st.stop()



    if "password_correct" not in st.session_state:


        st.text_input(
            "Passwort",
            type="password",
            key="password",
            on_change=password_entered
        )

        st.stop()



    elif not st.session_state["password_correct"]:


        st.text_input(
            "Passwort",
            type="password",
            key="password",
            on_change=password_entered
        )

        st.error(
            "Passwort falsch"
        )

        st.stop()



    return True



check_password()



# ============================================
# 2. SESSION STATE
# ============================================


DEFAULTS = {

    "aktien_liste": [],

    "datenbank": {},

    "modus": "sammeln",

    "abfrage_queue": [],

    "version_loaded": "",

    "levermann_txt": {}

}



for key,value in DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key]=value



if st.session_state.version_loaded != VERSION:


    for key,value in DEFAULTS.items():

        st.session_state[key]=value


    st.session_state.version_loaded = VERSION





# ============================================
# 3. STOCK UNIVERSUM
# ============================================


STOCK_UNIVERSE = [


{
"ticker":"NVDA",
"name":"Nvidia",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Compute",
"typ":"Empfänger"
},


{
"ticker":"AMD",
"name":"AMD",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Compute",
"typ":"Empfänger"
},


{
"ticker":"AVGO",
"name":"Broadcom",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Compute",
"typ":"Empfänger"
},


{
"ticker":"MRVL",
"name":"Marvell",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Compute",
"typ":"Empfänger"
},


{
"ticker":"INTC",
"name":"Intel",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Compute",
"typ":"Empfänger"
},


{
"ticker":"MU",
"name":"Micron",
"country":"USA",
"flag":"🇺🇸",
"segment":"Memory / HBM",
"typ":"Empfänger"
},


{
"ticker":"SKHY",
"name":"SK Hynix ADR",
"country":"South Korea",
"flag":"🇰🇷",
"segment":"Memory / HBM",
"typ":"Empfänger"
},


{
"ticker":"WDC",
"name":"Western Digital",
"country":"USA",
"flag":"🇺🇸",
"segment":"Memory / HBM",
"typ":"Empfänger"
},


{
"ticker":"STX",
"name":"Seagate",
"country":"USA",
"flag":"🇺🇸",
"segment":"Memory / HBM",
"typ":"Empfänger"
},


{
"ticker":"ASML",
"name":"ASML ADR",
"country":"Netherlands",
"flag":"🇳🇱",
"segment":"Semi Equipment",
"typ":"Empfänger"
},


{
"ticker":"AMAT",
"name":"Applied Materials",
"country":"USA",
"flag":"🇺🇸",
"segment":"Semi Equipment",
"typ":"Empfänger"
},


{
"ticker":"LRCX",
"name":"Lam Research",
"country":"USA",
"flag":"🇺🇸",
"segment":"Semi Equipment",
"typ":"Empfänger"
},


{
"ticker":"KLAC",
"name":"KLA",
"country":"USA",
"flag":"🇺🇸",
"segment":"Semi Equipment",
"typ":"Empfänger"
},


{
"ticker":"TER",
"name":"Teradyne",
"country":"USA",
"flag":"🇺🇸",
"segment":"Semi Equipment",
"typ":"Empfänger"
},


{
"ticker":"TSM",
"name":"TSMC ADR",
"country":"Taiwan",
"flag":"🇹🇼",
"segment":"Foundry",
"typ":"Empfänger"
},


{
"ticker":"GFS",
"name":"GlobalFoundries",
"country":"USA",
"flag":"🇺🇸",
"segment":"Foundry",
"typ":"Empfänger"
},


{
"ticker":"DELL",
"name":"Dell",
"country":"USA",
"flag":"🇺🇸",
"segment":"Server Hardware",
"typ":"Empfänger"
},


{
"ticker":"SMCI",
"name":"Super Micro Computer",
"country":"USA",
"flag":"🇺🇸",
"segment":"Server Hardware",
"typ":"Empfänger"
},


{
"ticker":"ETN",
"name":"Eaton",
"country":"USA",
"flag":"🇺🇸",
"segment":"Power Infrastructure",
"typ":"Empfänger"
},


{
"ticker":"VRT",
"name":"Vertiv",
"country":"USA",
"flag":"🇺🇸",
"segment":"Power Infrastructure",
"typ":"Empfänger"
},


{
"ticker":"BE",
"name":"Bloom Energy",
"country":"USA",
"flag":"🇺🇸",
"segment":"Power Infrastructure",
"typ":"Empfänger"
},


{
"ticker":"GEV",
"name":"GE Vernova",
"country":"USA",
"flag":"🇺🇸",
"segment":"Power Infrastructure",
"typ":"Empfänger"
},


{
"ticker":"CEG",
"name":"Constellation Energy",
"country":"USA",
"flag":"🇺🇸",
"segment":"Power Infrastructure",
"typ":"Empfänger"
},


{
"ticker":"ANET",
"name":"Arista Networks",
"country":"USA",
"flag":"🇺🇸",
"segment":"Networking",
"typ":"Empfänger"
},


{
"ticker":"CSCO",
"name":"Cisco",
"country":"USA",
"flag":"🇺🇸",
"segment":"Networking",
"typ":"Empfänger"
},


{
"ticker":"MSFT",
"name":"Microsoft",
"country":"USA",
"flag":"🇺🇸",
"segment":"Cloud AI",
"typ":"Spender"
},


{
"ticker":"AMZN",
"name":"Amazon",
"country":"USA",
"flag":"🇺🇸",
"segment":"Cloud AI",
"typ":"Spender"
},


{
"ticker":"GOOGL",
"name":"Alphabet",
"country":"USA",
"flag":"🇺🇸",
"segment":"Cloud AI",
"typ":"Spender"
},


{
"ticker":"META",
"name":"Meta",
"country":"USA",
"flag":"🇺🇸",
"segment":"Cloud AI",
"typ":"Spender"
},


{
"ticker":"ORCL",
"name":"Oracle",
"country":"USA",
"flag":"🇺🇸",
"segment":"Cloud AI",
"typ":"Spender"
},


{
"ticker":"NOW",
"name":"ServiceNow",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Software",
"typ":"Spender"
},


{
"ticker":"EQIX",
"name":"Equinix",
"country":"USA",
"flag":"🇺🇸",
"segment":"Data Center",
"typ":"Spender"
},


{
"ticker":"DLR",
"name":"Digital Realty",
"country":"USA",
"flag":"🇺🇸",
"segment":"Data Center",
"typ":"Spender"
},


{
"ticker":"PLTR",
"name":"Palantir",
"country":"USA",
"flag":"🇺🇸",
"segment":"AI Software",
"typ":"Neutral"
}


]



if len(st.session_state.aktien_liste)==0:

    st.session_state.aktien_liste = [

        x["ticker"]

        for x in STOCK_UNIVERSE

    ]



CAPEX_BIAS = {

    "Empfänger":10,

    "Spender":-10,

    "Neutral":0

}


# ============================================
# 4. WEIGHTS
# ============================================


WEIGHTS = {


"Empfänger":{

"Forward_KGV":0.10,
"EV_EBITDA":0.05,
"Umsatz_Wachstum":0.30,
"Bruttomarge":0.10,
"Operating_Margin":0.30,
"FCF_Marge":0.05,
"NetDebt_EBITDA":0.05,
"Performance_52W":0.05

},


"Spender":{

"Forward_KGV":0.15,
"EV_EBITDA":0.10,
"Umsatz_Wachstum":0.05,
"Bruttomarge":0.15,
"Operating_Margin":0.25,
"FCF_Marge":0.20,
"NetDebt_EBITDA":0.05,
"Performance_52W":0.05

},


"Neutral":{

"Forward_KGV":0.15,
"EV_EBITDA":0.15,
"Umsatz_Wachstum":0.15,
"Bruttomarge":0.15,
"Operating_Margin":0.15,
"FCF_Marge":0.15,
"NetDebt_EBITDA":0.05,
"Performance_52W":0.05

}

}


PFLICHT_KPIS=[

"Forward_KGV",
"EV_EBITDA",
"Umsatz_Wachstum",
"Bruttomarge",
"Operating_Margin",
"FCF_Marge",
"Performance_52W",
"NetDebt_EBITDA"

]


KPI_LABELS={

"Forward_KGV":"Forward KGV",
"EV_EBITDA":"EV/EBITDA",
"Umsatz_Wachstum":"Umsatzwachstum",
"Bruttomarge":"Bruttomarge",
"Operating_Margin":"Operating Margin",
"FCF_Marge":"FCF Marge",
"Performance_52W":"Performance 52 Wochen",
"NetDebt_EBITDA":"Net Debt/EBITDA"

}



# ============================================
# LEVERMANN TXT
# ============================================


def lade_levermann_aus_datei():

    try:

        df=pd.read_csv(
            "Levermann.txt",
            header=None,
            names=[
                "Ticker",
                "Wert"
            ]
        )


        df["Ticker"]=(
            df["Ticker"]
            .astype(str)
            .str.upper()
            .str.strip()
        )


        st.session_state.levermann_txt = dict(
            zip(
                df["Ticker"],
                df["Wert"]
            )
        )


    except:


        st.session_state.levermann_txt={}


        st.warning(
            "Levermann.txt nicht gefunden"
        )



#Ende Block 1
# ============================================
# 5. HELPER
# ============================================


@st.cache_data(ttl=1800)
def get_fear_greed():

    try:

        return round(
            fear_and_greed.get().value
        )

    except:

        return 50



def safe_get(info,key):

    try:

        value=info.get(key)

        if value is None:

            return np.nan

        return value


    except:

        return np.nan



def parse_number(text):

    if text is None:

        return np.nan


    text=str(text).strip().replace(",",".")


    try:

        return float(text)

    except:

        return np.nan




def init_ticker(ticker):


    if ticker not in st.session_state.datenbank:


        meta=next(

            (
                x for x in STOCK_UNIVERSE
                if x["ticker"]==ticker
            ),

            {
                "ticker":ticker,
                "name":ticker
            }

        )


        st.session_state.datenbank[ticker]={

            "daten":{

                "Ticker":ticker,

                **meta

            },


            "audit":{},

            "status":"neu"

        }




def save_kpi(
    ticker,
    kpi,
    value,
    quelle
):


    obj=st.session_state.datenbank[ticker]


    obj["daten"][kpi]=value


    obj["audit"][kpi]={

        "Wert":value,

        "Quelle":quelle,

        "Zeit":
        datetime.now()
        .strftime("%Y-%m-%d %H:%M"),

        "Version":VERSION

    }






# ============================================
# 6. YAHOO DATEN
# ============================================


@st.cache_data(
    ttl=3600,
    show_spinner=False
)

def yahoo_laden(ticker):


    try:


        time.sleep(0.2)


        tk=yf.Ticker(ticker)


        info=tk.info or {}


        fin=tk.financials


        cf=tk.cashflow



        price = (

            safe_get(info,"currentPrice")

            or

            safe_get(info,"regularMarketPrice")

            or

            safe_get(info,"previousClose")

        )



        revenue=safe_get(
            info,
            "totalRevenue"
        )


        fcf=safe_get(
            info,
            "freeCashflow"
        )



        if pd.isna(revenue) and not fin.empty:

            revenue=fin.iloc[0,0]



        if (

            pd.isna(fcf)

            and not cf.empty

            and "Free Cash Flow" in cf.index

        ):

            fcf=cf.loc[
                "Free Cash Flow"
            ].iloc[0]



        fcf_marge=np.nan


        if (

            not pd.isna(fcf)

            and not pd.isna(revenue)

            and revenue!=0

        ):

            fcf_marge=fcf/revenue




        brutto=safe_get(
            info,
            "grossMargins"
        )


        op_marge=safe_get(
            info,
            "operatingMargins"
        )



        if (

            pd.isna(brutto)

            and not fin.empty

            and "Gross Profit" in fin.index

            and "Total Revenue" in fin.index

        ):


            try:

                brutto=(

                    fin.loc[
                        "Gross Profit"
                    ].iloc[0]

                    /

                    fin.loc[
                        "Total Revenue"
                    ].iloc[0]

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

                op_marge=(

                    fin.loc[
                        "Operating Income"
                    ].iloc[0]

                    /

                    fin.loc[
                        "Total Revenue"
                    ].iloc[0]

                )


            except:

                pass




        debt=safe_get(
            info,
            "totalDebt"
        )


        cash=safe_get(
            info,
            "totalCash"
        )


        ebitda=safe_get(
            info,
            "ebitda"
        )


        netdebt_ebitda=np.nan



        if (

            not pd.isna(debt)

            and not pd.isna(cash)

            and not pd.isna(ebitda)

            and ebitda!=0

        ):


            netdebt_ebitda=(

                debt-cash

            )/ebitda





        return {


            "Aktueller_Kurs":price,

            "Forward_KGV":
            safe_get(info,"forwardPE"),

            "EV_EBITDA":
            safe_get(info,"enterpriseToEbitda"),

            "Umsatz_Wachstum":
            safe_get(info,"revenueGrowth"),

            "Bruttomarge":
            brutto,

            "Operating_Margin":
            op_marge,

            "FCF_Marge":
            fcf_marge,

            "Performance_52W":
            safe_get(info,"52WeekChange"),

            "NetDebt_EBITDA":
            netdebt_ebitda

        }



    except Exception:


        return None






def fehlende_kpis(ticker):


    daten=st.session_state.datenbank[ticker]["daten"]


    return [

        x for x in PFLICHT_KPIS

        if pd.isna(
            daten.get(x,np.nan)
        )

    ]






def baue_abfrage_queue():


    queue=[]


    for ticker in st.session_state.aktien_liste:


        init_ticker(ticker)


        obj=st.session_state.datenbank[ticker]



        if obj["status"]=="neu":


            daten=yahoo_laden(ticker)



            if daten:


                for kpi,wert in daten.items():


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
                (
                    ticker,
                    kpi
                )
            )



    st.session_state.abfrage_queue=queue





# ============================================
# 7. SCORING
# ============================================



def normalize_global(
    df,
    col,
    higher_better=True
):


    s=pd.to_numeric(
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






def berechne_levermann_faktor(lev):


    if pd.isna(lev):

        return 1.0



    try:

        lev=float(lev)


    except:

        return 1.0




    if lev < 3:

        return 0.90


    elif lev < 4:

        return 1.00


    elif lev < 5:

        return 1.05


    elif lev < 6:

        return 1.10


    else:

        return 1.20





def calculate_scores(df):


    df["Datenpunkte"]=(
        df[PFLICHT_KPIS]
        .notna()
        .sum(axis=1)
    )


    df["Vollständig"]=(
        df["Datenpunkte"]
        ==
        len(PFLICHT_KPIS)
    )


    df["Datenqualität"]=(
        df["Datenpunkte"]
        /
        len(PFLICHT_KPIS)
    )


    df["Capex_Bias"]=(
        df["typ"]
        .map(CAPEX_BIAS)
    )



    for col in PFLICHT_KPIS:


        lower = col in [

            "Forward_KGV",

            "EV_EBITDA",

            "NetDebt_EBITDA"

        ]


        df[
            f"Norm_{col}"
        ]=normalize_global(
            df,
            col,
            not lower
        )




    df["Finanzscore"]=0.0



    for idx,row in df.iterrows():


        score=0


        for col,w in WEIGHTS[row["typ"]].items():


            value=row[
                f"Norm_{col}"
            ]


            if not pd.isna(value):

                score += value*w



        df.at[idx,"Finanzscore"]=score*100





    df["Gesamtscore_Roh"]=(
        df["Finanzscore"]
        *
        0.9
    )



    # Levermann nur TXT
    df["Levermann"]=df["Ticker"].apply(

        lambda x:

        st.session_state.levermann_txt.get(
            x,
            np.nan
        )

    )



    df["Levermann_Faktor"]=(
        df["Levermann"]
        .apply(
            berechne_levermann_faktor
        )
    )



    df["Gesamtscore_Roh_mit_Lev"]=(
        df["Gesamtscore_Roh"]

        *

        df["Levermann_Faktor"]

    )



    df["Gesamtscore"]=(
        
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

        ascending=False

    ).reset_index(drop=True)



    df["Rang"]=df.index+1



    return df






def get_investment_rating(
    score,
    vollständig
):


    if pd.isna(score):

        return "N/A"


    if not vollständig:

        return "N/A - Daten fehlen"



    if score>=80:

        return "Strong Buy"


    elif score>=65:

        return "Buy"


    elif score>=45:

        return "Hold"


    else:

        return "Sell"



#Ende Block 2
# ============================================
# 8. SCREENS
# ============================================


def screen_sammeln():


    st.title(
        f"AI Infrastructure CAPEX Ranking {VERSION}"
    )


    fear=get_fear_greed()


    st.info(
        f"""
        **Axiom:** {AI_CYCLE_ASSUMPTION}

        | Horizont: Ende 2027

        | Fear&Greed: {fear}

        | Levermann: TXT Multiplikator
        """
    )



    empfänger=len(
        [
            x for x in STOCK_UNIVERSE
            if x["typ"]=="Empfänger"
        ]
    )


    spender=len(
        [
            x for x in STOCK_UNIVERSE
            if x["typ"]=="Spender"
        ]
    )


    neutral=len(
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
        STOCK_UNIVERSE
    )


    st.dataframe(

        df_meta[

            [
                "ticker",
                "name",
                "flag",
                "segment",
                "typ"
            ]

        ],

        use_container_width=True

    )



    if st.button(
        "✅ Auswertung starten",
        type="primary",
        use_container_width=True
    ):


        with st.spinner(
            "Lade Yahoo Daten + Levermann.txt..."
        ):


            lade_levermann_aus_datei()


            baue_abfrage_queue()



            if len(
                st.session_state.abfrage_queue
            )>0:


                st.session_state.modus="abfrage"


            else:


                st.session_state.modus="ranking"



        st.rerun()






def screen_abfrage():


    if len(
        st.session_state.abfrage_queue
    )==0:


        st.session_state.modus="ranking"

        st.rerun()

        return




    ticker,kpi=(
        st.session_state.abfrage_queue[0]
    )


    st.warning(
        f"Fehlender Wert: {ticker} - {KPI_LABELS[kpi]}"
    )


    st.write(

        f"Noch {len(st.session_state.abfrage_queue)} Werte offen"

    )


    wert_input=st.text_input(
        "Wert eingeben"
    )



    col1,col2,col3=st.columns(3)



    with col1:


        if st.button(
            "💾 Speichern"
        ):


            wert=parse_number(
                wert_input
            )


            if pd.isna(wert):

                st.error(
                    "Ungültige Zahl"
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


        if st.button(
            "⏭ Überspringen"
        ):


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
            "⏭⏭ Alle überspringen"
        ):


            for t,k in st.session_state.abfrage_queue:


                save_kpi(

                    t,

                    k,

                    np.nan,

                    "Bulk"

                )


            st.session_state.abfrage_queue=[]


            st.session_state.modus="ranking"


            st.rerun()







def screen_ranking():


    st.title(
        f"AI Infrastructure CAPEX Ranking {VERSION}"
    )



    liste=[

        st.session_state.datenbank[x]["daten"]

        for x in st.session_state.aktien_liste

    ]



    df=pd.DataFrame(
        liste
    )



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



    st.success(

        f"Axiom aktiv: {AI_CYCLE_ASSUMPTION}"

    )


    st.caption(

        """
        Modell:
        Finanzqualität + Wachstum + Profitabilität

        CAPEX Bias:
        Empfänger +10 | Spender -10

        Levermann:
        zusätzlicher Qualitätsmultiplikator

        Horizont:
        Ende 2027
        """

    )



    filter_segment=st.selectbox(

        "Segment Filter",

        [
            "Alle"
        ]

        +

        sorted(
            df["segment"]
            .dropna()
            .unique()
            .tolist()
        )

    )



    if filter_segment!="Alle":


        df_show=df[
            df["segment"]==filter_segment
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

        "Bruttomarge",

        "Operating_Margin",

        "FCF_Marge",

        "NetDebt_EBITDA"

    ]



    show_cols=[

        x for x in show_cols

        if x in df_show.columns

    ]



    # KISS: kein Styler / kein applymap
    st.dataframe(

        df_show[show_cols],

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
