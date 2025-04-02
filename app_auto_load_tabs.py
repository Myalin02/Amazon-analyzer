
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

st.set_page_config(page_title="Amazon Analyzer", layout="wide")

with st.sidebar:
    st.markdown("## 📤 Daten hochladen")

    uploaded_business = st.file_uploader("📊 Business Report (.csv)", type="csv")
    if uploaded_business:
        with open("data/business_reports/" + uploaded_business.name, "wb") as f:
            f.write(uploaded_business.getbuffer())
        st.success(f"✅ Business Report gespeichert: {uploaded_business.name}")

    uploaded_campaign = st.file_uploader("📈 Kampagnenbericht (.csv)", type="csv")
    if uploaded_campaign:
        with open("data/campaigns/" + uploaded_campaign.name, "wb") as f:
            f.write(uploaded_campaign.getbuffer())
        st.success(f"✅ Kampagnenbericht gespeichert: {uploaded_campaign.name}")

    uploaded_keywords = st.file_uploader("🔍 Suchbegriffe (.xlsx)", type="xlsx")
    if uploaded_keywords:
        with open("data/search_terms/" + uploaded_keywords.name, "wb") as f:
            f.write(uploaded_keywords.getbuffer())
        st.success(f"✅ Suchbegriffe gespeichert: {uploaded_keywords.name}")


# === Login-Schutz ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔐 Zugriff geschützt")
    password = st.text_input("Bitte Passwort eingeben:", type="password")
    if password == "sonnenaufgang":  # <-- Hier das echte Passwort eintragen
        st.session_state.logged_in = True
        st.rerun()
    elif password:
        st.error("❌ Falsches Passwort!")
    st.stop()


st.title("📊 AmazonAnalyzer Dashboard")

def extract_asin(text):
    matches = re.findall(r"\b[A-Z0-9]{10}\b", str(text))
    return matches[0] if matches else None

def get_latest_file(folder, ext=".csv"):
    try:
        files = [f for f in os.listdir(folder) if f.endswith(ext)]
        if not files:
            return None
        return os.path.join(folder, sorted(files, key=lambda x: os.path.getctime(os.path.join(folder, x)))[-1])
    except Exception:
        return None

# === Dateipfade setzen ===
business_path = get_latest_file("data/business_reports", ".csv")
campaign_path = get_latest_file("data/campaigns", ".csv")
keyword_path = get_latest_file("data/search_terms", ".xlsx")

# === Tabs vorbereiten ===
tab1, tab2, tab3, tab4 = st.tabs(["📈 Analyse", "🧠 ASIN Insights", "🔍 Keywords", "🔁 Monatsvergleich"])

# === Datenprüfung ===
if not all([business_path, campaign_path, keyword_path]):
    st.warning("❗ Bitte lade in jeden Datenordner mindestens eine Datei hoch: business_reports, campaigns, search_terms")
else:
    df_business = pd.read_csv(business_path)
    df_campaigns = pd.read_csv(campaign_path)
    df_keywords = pd.read_excel(keyword_path)

    def process_campaigns(df):
        df = df.rename(columns={
            "Klickrate (CTR)": "CTR",
            "Zugeschriebene Umsatzkosten (ACOS) gesamt ": "ACOS",
            "Gesamte Rentabilität der Anzeigenkosten (ROAS)": "ROAS",
            "Ausgaben": "Spend",
            "7 Tage, Umsatz gesamt (€)": "Umsatz",
            "Kampagnen-Name": "Kampagnenname"
        })
        df["ACOS (%)"] = df["ACOS"].astype(str).str.replace("%", "").str.replace(",", ".").astype(float)
        df["ROAS"] = df["ROAS"].astype(str).str.replace(",", ".").astype(float)
        df["Spend (€)"] = df["Spend"].astype(str).str.replace("€", "").str.replace(",", ".").astype(float)
        df["Umsatz (€)"] = df["Umsatz"].astype(str).str.replace("€", "").str.replace(",", ".").astype(float)
        df["ASIN"] = df["Kampagnenname"].apply(extract_asin)
        df["Ad_Bewertung"] = df.apply(lambda row: (
            "🔴 Schwach" if row["ACOS (%)"] > 40 and row["ROAS"] < 2 else
            "🟢 Top" if row["ACOS (%)"] < 20 and row["ROAS"] > 5 else
            "🟡 Neutral"
        ), axis=1)
        return df

    def process_business(df):
        df = df.rename(columns={
            "(Untergeordnete) ASIN": "ASIN",
            "Titel": "Produktname",
            "Sitzungen – Summe": "Sessions",
            "Prozentsatz an Einheiten pro Sitzung": "CR (%)",
            "Durch bestellte Produkte erzielter Umsatz": "Umsatz (organisch)"
        })
        df["Sessions"] = pd.to_numeric(df["Sessions"], errors='coerce')
        df["CR (%)"] = df["CR (%)"].astype(str).str.replace("%", "").str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)
        df["Umsatz (organisch)"] = df["Umsatz (organisch)"].astype(str).str.replace("€", "").str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)
        return df

    def process_asins(df):
        def bewertung(row):
            if row["Umsatz (organisch)"] > 300 and row["CR (%)"] > 10:
                return "🟢 Jetzt bewerben"
            elif row["CR (%)"] < 5 and row["Sessions"] > 50:
                return "🔴 Listing optimieren"
            elif row["Umsatz (organisch)"] < 100 and row["CR (%)"] >= 8:
                return "🟡 Potenzial – Pushen"
            else:
                return "🟠 Beobachten"
        df["Empfehlung"] = df.apply(bewertung, axis=1)
        return df

    def process_keywords(df):
        df = df.rename(columns={
            "Suchbegriff des Kunden": "Keyword",
            "Kampagnen-Name": "Kampagne",
            "Klicks": "Klicks",
            "Impressionen": "Impressionen",
            "Kosten pro Klick (CPC)": "CPC",
            "Klickrate (CTR)": "CTR",
            "Zugeschriebene Umsatzkosten (ACOS) gesamt ": "ACOS",
            "Gesamte Rentabilität der Anzeigenkosten (ROAS)": "ROAS",
            "7 Tage, Umsatz gesamt (€)": "Umsatz",
            "7-Tage-Konversionsrate": "CR"
        })
        df["ACOS"] = df["ACOS"].astype(str).str.replace("%", "").str.replace(",", ".").astype(float)
        df["ROAS"] = df["ROAS"].astype(str).str.replace(",", ".").astype(float)
        df["Umsatz"] = df["Umsatz"].astype(str).str.replace("€", "").str.replace(",", ".").astype(float)
        df["CR"] = df["CR"].astype(str).str.replace("%", "").str.replace(",", ".").astype(float)
        df["CTR"] = df["CTR"].astype(str).str.replace("%", "").str.replace(",", ".").astype(float)
        df["Empfehlung"] = df.apply(lambda row: (
            "🟢 Skalieren" if row["ACOS"] < 20 and row["ROAS"] > 4 else
            "🔴 Negativ setzen" if row["ACOS"] > 60 or row["CR"] < 3 else
            "🟡 Optimieren" if 20 <= row["ACOS"] <= 40 or 5 <= row["CR"] <= 10 else
            "🟠 Beobachten"
        ), axis=1)
        return df

    df_business_processed = process_business(df_business)
    df_campaigns_processed = process_campaigns(df_campaigns)
    df_keywords_processed = process_keywords(df_keywords)
    df_asins_processed = process_asins(df_business_processed)
    df_combined = pd.merge(df_business_processed, df_campaigns_processed, on="ASIN", how="outer")

    with tab1:
        st.subheader("📊 Kampagnen + Produktanalyse")
        st.dataframe(df_combined)

    with tab2:
        st.subheader("🧠 ASIN-Empfehlungen")
        st.dataframe(df_asins_processed)

    with tab3:
        st.subheader("🔍 Keyword-Auswertung")
        st.dataframe(df_keywords_processed)

    with tab4:
        st.subheader("🔁 Monatsvergleich")
        st.markdown("🧪 Funktion für Monatsvergleichs-Export kann hier integriert werden.")
