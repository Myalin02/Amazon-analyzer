
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



    # === 🟪 Tab: Marge & Break-Even-ACOS ===
    margin_tab = st.tabs(["📉 Marge & Break-Even-ACOS"])[0]

    with margin_tab:
        st.subheader("📉 Margenkontrolle & Rentabilität")

        price_file = st.file_uploader("📥 Einkaufspreise hochladen (.csv, Spalten: ASIN,Einkaufspreis)", type="csv")
        if price_file:
            df_preise = pd.read_csv(price_file)
            df_margin = df_combined.merge(df_preise, on="ASIN", how="left")

            df_margin["Amazon Gebühren (€)"] = df_margin["Umsatz (€)"] * 0.15 + 2
            df_margin["Netto-Marge (€)"] = df_margin["Umsatz (€)"] - df_margin["Amazon Gebühren (€)"] - df_margin["Einkaufspreis"]
            df_margin["Break-Even-ACOS (%)"] = (df_margin["Netto-Marge (€)"] / df_margin["Umsatz (€)"]) * 100
            df_margin["ACOS (%)"] = df_margin["ACOS (%)"].fillna(0)

            def bewertung(row):
                if pd.isna(row["Einkaufspreis"]):
                    return "⚠️ Kein EK hinterlegt"
                if row["ACOS (%)"] > row["Break-Even-ACOS (%)"]:
                    return "🔴 Unprofitabel"
                else:
                    return "🟢 OK"

            df_margin["Rentabilität"] = df_margin.apply(bewertung, axis=1)

            st.dataframe(df_margin[["ASIN", "Umsatz (€)", "Einkaufspreis", "Netto-Marge (€)", "ACOS (%)", "Break-Even-ACOS (%)", "Rentabilität"]])
        else:
            st.info("Bitte CSV mit ASIN & Einkaufspreis hochladen.")



    # === 🟪 Tab: Top & Flop Produkte ===
    topflop_tab = st.tabs(["🏆 Top & Flop Produkte"])[0]

    with topflop_tab:
        st.subheader("🏆 Top 10 Bestseller")
        df_top10 = df_combined.sort_values("Umsatz (€)", ascending=False).head(10)
        st.dataframe(df_top10[["ASIN", "Kampagnenname", "Umsatz (€)", "ACOS (%)", "ROAS"]])

        st.subheader("⚠️ Flop 10 Produkte (hoher ACOS oder niedriger Umsatz)")
        df_flop = df_combined[
            (df_combined["ACOS (%)"] > 50) | (df_combined["Umsatz (€)"] < 20)
        ].sort_values(["ACOS (%)", "Umsatz (€)"], ascending=[False, True]).head(10)
        st.dataframe(df_flop[["ASIN", "Kampagnenname", "Umsatz (€)", "ACOS (%)", "ROAS"]])



    # === 🟪 Tab: SEO-Check – Keyword-Coverage ===
    seo_tab = st.tabs(["🔎 SEO-Check"])[0]

    with seo_tab:
        st.subheader("🔍 Keyword-Abdeckung im Listing & in Kampagnen")

        keywords = df_keywords_processed["Keyword"].dropna().unique()
        kampagnen_content = df_campaigns["Kampagnenname"].astype(str).str.lower().str.cat(sep=" ")
        listing_content = df_business["Produktname"].astype(str).str.lower().str.cat(sep=" ")

        result = []
        for kw in keywords:
            kw_lc = kw.lower()
            in_listing = "✅" if kw_lc in listing_content else "❌"
            in_kampagne = "✅" if kw_lc in kampagnen_content else "❌"

            if in_listing == "✅" and in_kampagne == "✅":
                status = "🟢 Abgedeckt"
            elif in_listing == "❌" and in_kampagne == "✅":
                status = "🔴 Im Listing fehlt"
            elif in_listing == "✅" and in_kampagne == "❌":
                status = "🟠 Nicht beworben"
            else:
                status = "⚫ Nicht genutzt"

            result.append({"Keyword": kw, "Im Listing": in_listing, "In Kampagne": in_kampagne, "Status": status})

        df_seo = pd.DataFrame(result)
        st.dataframe(df_seo)



    # === 🟪 Tab: Katalog-Übersicht ===
    catalog_tab = st.tabs(["🗂️ Katalog-Übersicht"])[0]

    with catalog_tab:
        st.subheader("🗂️ Gesamtübersicht aller Amazon-Produkte")

        # Kombinieren: Business + Kampagnenberichte (falls nicht schon kombiniert)
        df_catalog = df_business.merge(df_campaigns[["ASIN", "Kampagnenname"]], on="ASIN", how="left")
        df_catalog["Werbung aktiv"] = df_catalog["Kampagnenname"].notnull().map({True: "✅ Ja", False: "❌ Nein"})

        # Bewertung basierend auf Umsatz + CR
        def bewertung(row):
            if row["Umsatz (organisch)"] == 0:
                return "🟥 Kein Verkauf"
            elif row["CR (%)"] >= 10:
                return "🟢 Hochperformer"
            elif row["CR (%)"] < 5:
                return "🟡 Optimieren"
            else:
                return "⚪ Mittel"

        df_catalog["Status"] = df_catalog.apply(bewertung, axis=1)

        # Zeige Tabelle
        st.dataframe(df_catalog[[
            "ASIN", "Produktname", "Sessions", "CR (%)", "Umsatz (organisch)",
            "Werbung aktiv", "Status"
        ]])
