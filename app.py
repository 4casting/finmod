import streamlit as st
import pandas as pd
import json
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime

# --- 0. HILFSFUNKTIONEN & LOGIN ---

def safe_float(value, default=0.0):
    """Konvertiert Eingaben sicher in float, fängt Fehler und None ab."""
    try:
        if value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value): 
            return default
        return float(value)
    except: 
        return default

def check_password():
    """Einfache Login-Schranke."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("## 🔒 Bitte einloggen")
    st.caption("Default: admin / 123")
    col1, col2 = st.columns([1,2])
    with col1:
        user = st.text_input("Benutzername")
        pwd = st.text_input("Passwort", type="password")
        if st.button("Anmelden"):
            if user == "admin" and pwd == "123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Falscher Benutzername oder Passwort")
    return False

# --- HAUPTPROGRAMM START ---
if not check_password():
    st.stop()

st.set_page_config(page_title="Finanzmodell Pro", layout="wide")

st.sidebar.success("Eingeloggt als Admin")
if st.sidebar.button("Abmelden"):
    st.session_state["password_correct"] = False
    st.rerun()

# --- 1. DEFINITION DER STANDARDS & STATE ---
DEFAULTS = {
    # Markt
    "sam": 39000.0, "cap_pct": 2.3, "p_pct": 2.5, "q_pct": 38.0, "churn": 10.0, "manual_arpu": 3000.0,
    # Finanzierung
    "equity": 100000.0, "loan_initial": 0.0, "min_cash": 100000.0, "loan_rate": 5.0,
    # Personal Global
    "wage_inc": 1.5, "inflation": 2.0, "lnk_pct": 25.0, "target_rev_per_fte": 150000.0,
    # Working Capital & Tax
    "dso": 30, "dpo": 30, "tax_rate": 30.0, "cac": 3590.0,
    # Assets Preise & Dauer
    "price_desk": 2500, "price_laptop": 2000, "price_phone": 800, "price_car": 40000, "price_truck": 60000,
    "ul_desk": 13, "ul_laptop": 3, "ul_phone": 2, "ul_car": 6, "ul_truck": 8,
    "capex_annual": 5000, "depreciation_misc": 5,
}

# State initialisieren (Werte)
for key, default_val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# State initialisieren (Tabellen)
if "current_jobs_df" not in st.session_state:
    defined_roles = [
        {"Job Titel": "Geschäftsführer", "Jahresgehalt (€)": 120000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Vertriebsleiter", "Jahresgehalt (€)": 80000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Sales Manager", "Jahresgehalt (€)": 50000.0, "FTE Jahr 1": 3.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500.0},
        {"Job Titel": "Marketing", "Jahresgehalt (€)": 45000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 2000.0},
        {"Job Titel": "Techniker", "Jahresgehalt (€)": 40000.0, "FTE Jahr 1": 2.0, "Laptop": False, "Smartphone": True, "Auto": False, "LKW": True, "Büro": False, "Sonstiges (€)": 1000.0},
        {"Job Titel": "Buchhaltung", "Jahresgehalt (€)": 42000.0, "FTE Jahr 1": 0.5, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
    ]
    for i in range(len(defined_roles) + 1, 16):
        defined_roles.append({
            "Job Titel": f"Position {i}", "Jahresgehalt (€)": 0.0, "FTE Jahr 1": 0.0, 
            "Laptop": False, "Smartphone": False, "Auto": False, "LKW": False, "Büro": False, "Sonstiges (€)": 0.0
        })
    st.session_state["current_jobs_df"] = pd.DataFrame(defined_roles)

if "cost_centers_df" not in st.session_state:
    st.session_state["cost_centers_df"] = pd.DataFrame([
        {"Kostenstelle": "Büromaterial", "Grundwert Jahr 1 (€)": 1200, "Umsatz-Kopplung (%)": 20},
        {"Kostenstelle": "Reisekosten", "Grundwert Jahr 1 (€)": 5000, "Umsatz-Kopplung (%)": 80},
        {"Kostenstelle": "IT-Infrastruktur", "Grundwert Jahr 1 (€)": 2400, "Umsatz-Kopplung (%)": 40},
        {"Kostenstelle": "Rechtsberatung", "Grundwert Jahr 1 (€)": 1500, "Umsatz-Kopplung (%)": 10},
        {"Kostenstelle": "Versicherungen", "Grundwert Jahr 1 (€)": 3000, "Umsatz-Kopplung (%)": 0},
    ])

if "products_df" not in st.session_state:
    products_init = [
        {"Produkt": "Standard Abo", "Preis (€)": 100.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 10.0, "Take Rate (%)": 80.0, "Wiederkauf Rate (%)": 90.0, "Wiederkauf alle (Monate)": 12},
        {"Produkt": "Premium Add-On", "Preis (€)": 500.0, "Avg. Rabatt (%)": 5.0, "Herstellungskosten (COGS €)": 50.0, "Take Rate (%)": 20.0, "Wiederkauf Rate (%)": 50.0, "Wiederkauf alle (Monate)": 24},
        {"Produkt": "Setup Gebühr", "Preis (€)": 1000.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 200.0, "Take Rate (%)": 100.0, "Wiederkauf Rate (%)": 0.0, "Wiederkauf alle (Monate)": 0},
    ]
    for i in range(len(products_init) + 1, 11):
        products_init.append({
            "Produkt": f"Produkt {i}", "Preis (€)": 0.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 0.0, "Take Rate (%)": 0.0, "Wiederkauf Rate (%)": 0.0, "Wiederkauf alle (Monate)": 0
        })
    st.session_state["products_df"] = pd.DataFrame(products_init)

# --- 2. PDF REPORT GENERATOR (DETAIL) ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(44, 62, 80) # Dunkelblau
        self.cell(0, 10, 'Business Plan & Finanzmodell', 0, 1, 'L')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Generiert am: {datetime.now().strftime("%d.%m.%Y %H:%M")}', 0, 1, 'L')
        self.set_draw_color(200, 200, 200)
        self.line(10, 25, 287, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Seite {self.page_no()}/{{nb}} - Vertraulich', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102) # Navy
        self.set_fill_color(230, 240, 255) # Hellblau
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def sub_title(self, title):
        self.set_font('Arial', 'B', 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, title, 0, 1, 'L')

    def add_key_value_table(self, data_dict, title="Parameter"):
        self.sub_title(title)
        self.set_font('Arial', '', 9)
        col_width = 80
        row_height = 6
        for k, v in data_dict.items():
            self.set_font('Arial', 'B', 9)
            self.cell(col_width, row_height, str(k), 1)
            self.set_font('Arial', '', 9)
            val_str = str(v)
            if isinstance(v, float): val_str = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.cell(col_width, row_height, val_str, 1)
            self.ln()
        self.ln(5)

    def add_dataframe_table(self, df, col_widths=None):
        self.set_font('Arial', 'B', 8)
        self.set_fill_color(240, 240, 240)
        if not col_widths:
            page_width = 277
            col_width = page_width / len(df.columns)
            widths = [col_width] * len(df.columns)
        else:
            widths = col_widths
        for i, col in enumerate(df.columns):
            self.cell(widths[i], 7, str(col), 1, 0, 'C', 1)
        self.ln()
        self.set_font('Arial', '', 8)
        for _, row in df.iterrows():
            for i, col in enumerate(df.columns):
                val = row[col]
                if isinstance(val, (int, float)): txt = f"{val:,.0f}".replace(",", ".")
                elif isinstance(val, bool): txt = "Ja" if val else "Nein"
                else: txt = str(val)
                self.cell(widths[i], 6, txt, 1, 0, 'R' if isinstance(val, (int, float)) else 'L')
            self.ln()
        self.ln(5)

    def add_chart(self, fig):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            fig.savefig(tmpfile.name, dpi=150, bbox_inches='tight')
            self.image(tmpfile.name, x=30, w=230)
        self.ln(5)

def create_detailed_pdf(df_results, session_data, jobs_data, products_data, cc_data):
    pdf = PDFReport(orientation='L', unit='mm', format='A4')
    pdf.alias_nb_pages()
    
    # 1. Management Summary
    pdf.add_page()
    pdf.section_title("1. Management Summary & KPIs")
    if not df_results.empty:
        last_year = df_results.iloc[-1]
        pdf.set_font('Arial', '', 12)
        pdf.ln(5)
        pdf.cell(0, 10, "Ergebnisse im Jahr 10 (Prognose):", 0, 1)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(60, 15, f"Umsatz: {last_year['Umsatz']:,.0f} EUR", 1, 0, 'C')
        pdf.cell(10, 15, "", 0, 0)
        pdf.cell(60, 15, f"EBITDA: {last_year['EBITDA']:,.0f} EUR", 1, 0, 'C')
        pdf.cell(10, 15, "", 0, 0)
        pdf.cell(60, 15, f"Cash: {last_year['Kasse']:,.0f} EUR", 1, 0, 'C')
        pdf.ln(25)
        
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(df_results["Jahr"], df_results["Umsatz"], label="Umsatz", linewidth=2, marker='o')
        ax1.plot(df_results["Jahr"], df_results["Gesamtkosten (OPEX)"], label="Kosten (OPEX)", linestyle='--', color='red')
        ax1.bar(df_results["Jahr"], df_results["EBITDA"], label="EBITDA", alpha=0.3, color='green')
        ax1.set_title("Umsatz vs. Kosten & Gewinn")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        pdf.sub_title("Finanzielle Entwicklung (10 Jahre)")
        pdf.add_chart(fig1)
        plt.close(fig1)

    # 2. Annahmen
    pdf.add_page()
    pdf.section_title("2. Annahmen & Planungsgrundlagen")
    col1_params = {
        "Marktpotenzial (SAM)": session_data.get("sam"), "Marktanteil Ziel (%)": session_data.get("cap_pct"),
        "Startkapital (Equity)": session_data.get("equity"), "Startkredit": session_data.get("loan_initial")
    }
    col2_params = {
        "Lohnsteigerung p.a. (%)": session_data.get("wage_inc"), "Inflation p.a. (%)": session_data.get("inflation"),
        "Steuersatz (%)": session_data.get("tax_rate")
    }
    y_start = pdf.get_y()
    pdf.set_x(10)
    pdf.add_key_value_table(col1_params, "Markt & Finanzierung")
    pdf.set_y(y_start)
    pdf.set_x(150)
    pdf.add_key_value_table(col2_params, "Makroökonomie & Steuern")
    pdf.ln(10)
    
    if jobs_data is not None and not jobs_data.empty:
        pdf.sub_title("Geplante Personalstruktur (Start)")
        cols_job = ["Job Titel", "Jahresgehalt (€)", "FTE Jahr 1", "Sonstiges (€)"]
        pdf.add_dataframe_table(jobs_data[cols_job], col_widths=[80, 40, 30, 40])

    # 3. Details
    pdf.add_page()
    pdf.section_title("3. Produktkalkulation & Kostenstellen")
    if products_data is not None and not products_data.empty:
        pdf.sub_title("Produkt Portfolio")
        prod_print = products_data[products_data["Preis (€)"] > 0].copy()
        cols_prod = ["Produkt", "Preis (€)", "Herstellungskosten (COGS €)", "Take Rate (%)", "Wiederkauf Rate (%)"]
        if not prod_print.empty:
            pdf.add_dataframe_table(prod_print[cols_prod])
    pdf.ln(5)
    if cc_data is not None and not cc_data.empty:
        pdf.sub_title("Kostenstellen (Manuell)")
        cc_print = cc_data[cc_data["Kostenstelle"] != ""].copy()
        if not cc_print.empty:
            pdf.add_dataframe_table(cc_print)

    # 4. Finanzen
    pdf.add_page()
    pdf.section_title("4. Gewinn- und Verlustrechnung (GuV)")
    cols_guv = ["Jahr", "Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Steuern", "Jahresüberschuss"]
    exist_guv = [c for c in cols_guv if c in df_results.columns]
    widths = [15] + [30] * (len(exist_guv)-1)
    pdf.add_dataframe_table(df_results[exist_guv], col_widths=widths)
    
    pdf.ln(5)
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    years = df_results["Jahr"]
    pers = df_results["Personalkosten"]
    mkt = df_results["Marketing Kosten"]
    cogs = df_results["Wareneinsatz (COGS)"]
    rest = df_results["Gesamtkosten (OPEX)"] - pers - mkt - cogs
    ax2.stackplot(years, cogs, pers, mkt, rest, labels=['COGS', 'Personal', 'Marketing', 'Sonstiges'], alpha=0.8)
    ax2.set_title("Kostenstruktur (Stacked)")
    ax2.legend(loc='upper left')
    pdf.sub_title("Analyse der Kostenstruktur")
    pdf.add_chart(fig2)
    plt.close(fig2)

    # 5. Cashflow/Bilanz
    pdf.add_page()
    pdf.section_title("5. Cashflow & Bilanz")
    pdf.sub_title("Kapitalflussrechnung")
    cols_cf = ["Jahr", "Jahresüberschuss", "Investitionen (Assets)", "Net Cash Change", "Kasse"]
    pdf.add_dataframe_table(df_results[cols_cf])
    pdf.ln(5)
    pdf.sub_title("Bilanzstruktur (Passiva)")
    cols_bil = ["Jahr", "Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]
    pdf.add_dataframe_table(df_results[cols_bil])
    
    fig3, ax3 = plt.subplots(figsize=(10, 3.5))
    ax3.fill_between(df_results["Jahr"], df_results["Kasse"], color="skyblue", alpha=0.4, label="Kassenbestand")
    ax3.plot(df_results["Jahr"], df_results["Bankdarlehen"], color="red", linestyle="--", label="Verbindlichkeiten")
    ax3.set_title("Liquidität vs. Schulden")
    ax3.legend()
    pdf.sub_title("Liquiditätsentwicklung")
    pdf.add_chart(fig3)
    plt.close(fig3)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. UI LAYOUT ---

st.title("Integriertes Finanzmodell: Cash Sweep & Asset Management")

col_main_act1, col_main_act2 = st.columns([1, 3])
with col_main_act1:
    if st.button("🔄 MODELL JETZT NEU BERECHNEN", type="primary", use_container_width=True):
        st.rerun()
with col_main_act2:
    st.info("💡 Eingaben in den Tabellen werden nun direkt gespeichert.")

# SPEICHERN & LADEN
with st.expander("📂 Datei Speichern & Laden (Import/Export)", expanded=False):
    col_io1, col_io2 = st.columns(2)
    with col_io1:
        st.markdown("##### 1. Speichern")
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        
        # Sicherstellen, dass alles DFs sind
        if "current_jobs_df" in st.session_state:
             df_jobs = pd.DataFrame(st.session_state["current_jobs_df"])
             df_export = df_jobs.fillna(0).copy()
             for c in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
                 if c in df_export.columns: df_export[c] = df_export[c].apply(bool)
             config_data["jobs_data"] = df_export.to_dict(orient="records")
        
        if "cost_centers_df" in st.session_state:
             df_cc = pd.DataFrame(st.session_state["cost_centers_df"])
             config_data["cost_centers_data"] = df_cc.to_dict(orient="records")
        
        if "products_df" in st.session_state:
             df_prod = pd.DataFrame(st.session_state["products_df"])
             config_data["products_data"] = df_prod.to_dict(orient="records")
        
        st.download_button("💾 Als JSON herunterladen", json.dumps(config_data, indent=2), "finanzmodell_config.json", "application/json")

    with col_io2:
        st.markdown("##### 2. Laden")
        uploaded_file = st.file_uploader("JSON-Datei:", type=["json"])
        if uploaded_file is not None:
            if st.button("📥 Importieren", type="secondary"):
                try:
                    data = json.load(uploaded_file)
                    for key, val in data.items():
                        if key in DEFAULTS: st.session_state[key] = val
                    if "jobs_data" in data:
                        st.session_state["current_jobs_df"] = pd.DataFrame(data["jobs_data"])
                    if "cost_centers_data" in data:
                         st.session_state["cost_centers_df"] = pd.DataFrame(data["cost_centers_data"])
                    if "products_data" in data:
                         st.session_state["products_df"] = pd.DataFrame(data["products_data"])
                    st.toast("Daten geladen!", icon="✅")
                    st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# TABS
tab_input, tab_products, tab_assets, tab_jobs, tab_costs, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt & Finanzen", "📦 Produkte", "📉 Abschreibungen & Assets", "👥 Personal", 
    "🏢 Kostenstellen", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# TAB 1: MARKT
with tab_input:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Markt & Wachstum")
        st.number_input("SAM (Marktpotenzial)", step=1000.0, key="sam")
        st.number_input("Marktanteil Ziel %", step=0.1, key="cap_pct")
        SOM = st.session_state["sam"] * (st.session_state["cap_pct"] / 100.0)
        st.info(f"SOM: {int(SOM)} Kunden")
        st.number_input("Innovatoren (p) %", step=0.1, key="p_pct")
        st.number_input("Imitatoren (q) %", step=1.0, key="q_pct")
        st.number_input("Churn Rate %", step=1.0, key="churn")
        st.subheader("Umsatz Basis")
        st.caption("Wird überschrieben, wenn Produkte definiert sind.")
        st.number_input("Manueller ARPU (€) (Fallback)", step=100.0, key="manual_arpu")

    with col2:
        st.subheader("2. Finanzierung")
        st.number_input("Eigenkapital Start (€)", step=5000.0, key="equity")
        st.number_input("Start-Schuldenstand (€)", step=5000.0, key="loan_initial")
        st.number_input("Mindest-Liquidität (Puffer) €", step=5000.0, key="min_cash")
        st.number_input("Soll-Zins Kredit %", step=0.1, key="loan_rate")
        st.markdown("---")
        st.number_input("Lohnsteigerung %", step=0.1, key="wage_inc")
        st.number_input("Inflation %", step=0.1, key="inflation")
        st.number_input("Lohnnebenkosten %", step=1.0, key="lnk_pct")
        st.markdown("---")
        st.number_input("DSO (Tage)", key="dso")
        st.number_input("DPO (Tage)", key="dpo")
        st.number_input("Steuersatz %", key="tax_rate")
        st.number_input("Marketing CAC (€)", key="cac")

# TAB 2: PRODUKTE
with tab_products:
    st.header("Produktkalkulation")
    st.info("Produkte definieren. Diese Werte steuern den Umsatz.")
    edited_products = st.data_editor(
        st.session_state["products_df"],
        num_rows="fixed", use_container_width=True, key="prod_editor_widget",
        column_config={
            "Produkt": st.column_config.TextColumn("Produkt Name", required=True),
            "Preis (€)": st.column_config.NumberColumn("Preis (Netto)", min_value=0.0, format="%.2f €"),
            "Avg. Rabatt (%)": st.column_config.NumberColumn("Ø Rabatt", min_value=0.0, max_value=100.0, format="%.1f %%"),
            "Herstellungskosten (COGS €)": st.column_config.NumberColumn("COGS (EK/Prod)", min_value=0.0, format="%.2f €"),
            "Take Rate (%)": st.column_config.NumberColumn("Take Rate (Kunden %)", min_value=0.0, max_value=100.0),
            "Wiederkauf Rate (%)": st.column_config.NumberColumn("Wiederkauf Quote", min_value=0.0, max_value=100.0),
            "Wiederkauf alle (Monate)": st.column_config.NumberColumn("Zyklus (Monate)", min_value=0),
        }
    )
    st.session_state["products_df"] = edited_products

# TAB 3: ASSETS
with tab_assets:
    st.header("Asset Management")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("IT")
        st.number_input("Laptop Preis (€)", key="price_laptop")
        st.number_input("Laptop Dauer (Jahre)", key="ul_laptop", min_value=1)
        st.number_input("Handy Preis (€)", key="price_phone")
        st.number_input("Handy Dauer (Jahre)", key="ul_phone", min_value=1)
    with c2:
        st.subheader("Mobilität")
        st.number_input("PKW Preis (€)", key="price_car")
        st.number_input("PKW Dauer (Jahre)", key="ul_car", min_value=1)
        st.number_input("LKW Preis (€)", key="price_truck")
        st.number_input("LKW Dauer (Jahre)", key="ul_truck", min_value=1)
    with c3:
        st.subheader("Sonstiges")
        st.number_input("Büroplatz Preis (€)", key="price_desk")
        st.number_input("Büro Dauer (Jahre)", key="ul_desk", min_value=1)
        st.markdown("---")
        st.number_input("Sonstiges Capex p.a. (€)", key="capex_annual")
        st.number_input("AfA Dauer Sonstiges (Jahre)", key="depreciation_misc")

# TAB 4: PERSONAL
with tab_jobs:
    st.header("Personalplanung")
    st.number_input("Ziel-Umsatz je FTE (€/Jahr)", step=5000.0, key="target_rev_per_fte")
    edited_jobs = st.data_editor(
        st.session_state["current_jobs_df"],
        num_rows="fixed", use_container_width=True, key="job_editor_widget",
        column_config={
            "Job Titel": st.column_config.TextColumn("Job Titel", required=True),
            "Jahresgehalt (€)": st.column_config.NumberColumn("Jahresgehalt", min_value=0, format="%d €"),
            "FTE Jahr 1": st.column_config.NumberColumn("FTE Start", min_value=0.0, step=0.1, format="%.1f"),
            "Sonstiges (€)": st.column_config.NumberColumn("Setup sonst. (€)", min_value=0, format="%d €"),
            "Laptop": st.column_config.CheckboxColumn("Laptop", default=False),
            "Smartphone": st.column_config.CheckboxColumn("Handy", default=False),
            "Auto": st.column_config.CheckboxColumn("Auto", default=False),
            "LKW": st.column_config.CheckboxColumn("LKW", default=False),
            "Büro": st.column_config.CheckboxColumn("Büro", default=False),
        },
        hide_index=True
    )
    st.session_state["current_jobs_df"] = edited_jobs

# TAB 5: KOSTENSTELLEN
with tab_costs:
    st.header("Zusätzliche Kostenstellen")
    st.info("Definieren Sie hier sonstige Kosten und deren Abhängigkeit vom Umsatz.")
    edited_cc = st.data_editor(
        st.session_state["cost_centers_df"],
        num_rows="dynamic", use_container_width=True, key="cc_editor_widget",
        column_config={
            "Kostenstelle": st.column_config.TextColumn("Bezeichnung", required=True),
            "Grundwert Jahr 1 (€)": st.column_config.NumberColumn("Startwert (Jahr 1)", min_value=0, format="%.2f €"),
            "Umsatz-Kopplung (%)": st.column_config.NumberColumn(
                "Steigerung mit Umsatz (%)", min_value=0, max_value=100, format="%d %%"
            ),
        }
    )
    st.session_state["cost_centers_df"] = edited_cc

# --- 4. BERECHNUNGSLOGIK ---

# Input Parsing
jobs_config = pd.DataFrame(st.session_state["current_jobs_df"]).to_dict(orient="records")
valid_jobs = []
for job in jobs_config:
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
    for k in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
        job[k] = bool(job.get(k))
    job["_setup_opex"] = job["Sonstiges (€)"]
    valid_jobs.append(job)

cc_config = pd.DataFrame(st.session_state["cost_centers_df"]).to_dict(orient="records")
products_config = pd.DataFrame(st.session_state["products_df"]).to_dict(orient="records")

# Produkt Logik (ARPU)
weighted_arpu, weighted_cogs = 0.0, 0.0
has_products = False
for p in products_config:
    price = safe_float(p.get("Preis (€)"))
    if price > 0:
        has_products = True
        disc = safe_float(p.get("Avg. Rabatt (%)")) / 100.0
        cogs_val = safe_float(p.get("Herstellungskosten (COGS €)"))
        take_rate = safe_float(p.get("Take Rate (%)")) / 100.0
        repurchase_rate = safe_float(p.get("Wiederkauf Rate (%)")) / 100.0
        months = safe_float(p.get("Wiederkauf alle (Monate)"))
        
        freq = 1.0
        if months > 0:
            cycles_per_year = 12.0 / months
            freq = 1.0 + (repurchase_rate * (cycles_per_year - 1)) if cycles_per_year >= 1 else 1.0
            
        net_price = price * (1 - disc)
        rev_per_customer = net_price * take_rate * freq
        cogs_per_customer = cogs_val * take_rate * freq
        weighted_arpu += rev_per_customer
        weighted_cogs += cogs_per_customer

if not has_products or weighted_arpu == 0:
    calc_arpu = st.session_state["manual_arpu"]
    calc_cogs_ratio = 0.10 
else:
    calc_arpu = weighted_arpu
    calc_cogs_ratio = weighted_cogs / weighted_arpu if weighted_arpu > 0 else 0.0

# Initialwerte Loop
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
CHURN = st.session_state["churn"] / 100.0
N_start = 10.0 

asset_types = {
    "Laptop": {"price_key": "price_laptop", "ul_key": "ul_laptop"},
    "Smartphone": {"price_key": "price_phone", "ul_key": "ul_phone"},
    "Auto": {"price_key": "price_car", "ul_key": "ul_car"},
    "LKW": {"price_key": "price_truck", "ul_key": "ul_truck"},
    "Büro": {"price_key": "price_desk", "ul_key": "ul_desk"},
    "Misc": {"price_key": None, "ul_key": "depreciation_misc"} 
}
asset_register = {k: [] for k in asset_types.keys()}

results = []
n_prev = N_start
prev_ftes_by_role = {j["Job Titel"]: j["FTE Jahr 1"] for j in valid_jobs}
prev_cc_values = {}
for item in cc_config:
    nm = item.get("Kostenstelle")
    if nm: prev_cc_values[nm] = safe_float(item.get("Grundwert Jahr 1 (€)"))

cash = 0.0
fixed_assets = 0.0
debt = st.session_state["loan_initial"]
retained_earnings = 0.0
wage_factor = 1.0
debt_prev = st.session_state["loan_initial"]
asset_details_log = []

# --- CORE LOOP (JAHRE 1-10) ---
for t in range(1, 11):
    row = {"Jahr": t}
    
    # 1. Markt
    if t == 1: n_t = N_start
    else:
        pot = max(0, st.session_state["sam"] * (st.session_state["cap_pct"]/100.0) - n_prev)
        adopt = (P + Q * (n_prev / (st.session_state["sam"] * (st.session_state["cap_pct"]/100.0) or 1)))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    gross_rev = n_t * calc_arpu
    row["Umsatz"] = gross_rev
    
    # Wachstum berechnen
    rev_prev_val = results[-1]["Umsatz"] if t > 1 else gross_rev
    growth_rate = (gross_rev - rev_prev_val) / rev_prev_val if (t > 1 and rev_prev_val > 0) else 0.0

    # 2. Personal
    target_total_fte = 0
    if st.session_state["target_rev_per_fte"] > 0:
        target_total_fte = gross_rev / st.session_state["target_rev_per_fte"]
    if t > 1: wage_factor *= (1 + st.session_state["wage_inc"]/100) * (1 + st.session_state["inflation"]/100)
    
    daily_personnel_cost = 0
    setup_opex = 0
    asset_needs = {k: 0.0 for k in asset_types.keys() if k != "Misc"}
    current_ftes_by_role = {}
    
    for job in valid_jobs:
        role = job["Job Titel"]
        base_fte = job["FTE Jahr 1"]
        if t == 1: curr_fte = base_fte
        else:
            if base_fte > 0 and total_fte_y1 > 0:
                share = base_fte / total_fte_y1
                req = target_total_fte * share
                curr_fte = max(req, prev_ftes_by_role.get(role, 0))
            else: curr_fte = 0.0
        current_ftes_by_role[role] = curr_fte
        if curr_fte > 0: row[f"FTE {role}"] = curr_fte
        else: row[f"FTE {role}"] = 0.0
        
        cost = job["Jahresgehalt (€)"] * curr_fte * wage_factor * (1 + st.session_state["lnk_pct"]/100)
        daily_personnel_cost += cost
        prev = prev_ftes_by_role.get(role, 0) if t > 1 else 0
        delta = max(0, curr_fte - prev)
        setup_opex += delta * job["_setup_opex"]
        
        if job["Laptop"]: asset_needs["Laptop"] += curr_fte
        if job["Smartphone"]: asset_needs["Smartphone"] += curr_fte
        if job["Auto"]: asset_needs["Auto"] += curr_fte
        if job["LKW"]: asset_needs["LKW"] += curr_fte
        if job["Büro"]: asset_needs["Büro"] += curr_fte

    row["FTE Total"] = sum(current_ftes_by_role.values())
    row["Personalkosten"] = daily_personnel_cost
    
    # 3. Assets
    capex_now = 0.0
    depreciation_now = 0.0
    capex_misc = st.session_state["capex_annual"]
    asset_register["Misc"].append({"year": t, "amount": 1, "price": capex_misc, "total_cost": capex_misc, "ul": st.session_state["depreciation_misc"]})
    capex_now += capex_misc
    
    for atype, needed in asset_needs.items():
        price = st.session_state[asset_types[atype]["price_key"]]
        ul = st.session_state[asset_types[atype]["ul_key"]]
        valid = sum(p["amount"] for p in asset_register[atype] if (t - p["year"]) < p["ul"])
        buy = max(0, needed - valid)
        if buy > 0:
            cost = buy * price
            capex_now += cost
            asset_register[atype].append({"year": t, "amount": buy, "price": price, "total_cost": cost, "ul": ul})
            
    for atype, purchases in asset_register.items():
        type_depr = 0
        for p in purchases:
            if 0 <= (t - p["year"]) < p["ul"]:
                type_depr += p["total_cost"] / p["ul"]
        depreciation_now += type_depr
        asset_details_log.append({"Jahr": t, "Typ": atype, "Invest (€)": sum(p["total_cost"] for p in purchases if p["year"]==t), "AfA (€)": type_depr})

    row["Investitionen (Assets)"] = capex_now
    row["Abschreibungen"] = depreciation_now
    
    # 4. Manuelle Kostenstellen
    total_manual_cc_cost = 0.0
    for cc_item in cc_config:
        name = cc_item.get("Kostenstelle")
        if not name: continue
        coupling = safe_float(cc_item.get("Umsatz-Kopplung (%)")) / 100.0
        prev_val = prev_cc_values.get(name, 0.0)
        
        if t == 1:
            current_val = safe_float(cc_item.get("Grundwert Jahr 1 (€)"))
        else:
            current_val = prev_val * (1 + (growth_rate * coupling))
            
        prev_cc_values[name] = current_val
        total_manual_cc_cost += current_val
        row[f"CC_{name}"] = current_val

    # 5. GuV
    cost_cogs = gross_rev * calc_cogs_ratio
    row["Wareneinsatz (COGS)"] = cost_cogs
    cost_mkt = n_t * st.session_state["cac"]
    row["Marketing Kosten"] = cost_mkt
    cost_cons = gross_rev * 0.02
    
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_cons + setup_opex + total_manual_cc_cost
    row["Gesamtkosten (OPEX)"] = total_opex
    
    ebitda = gross_rev - total_opex
    ebit = ebitda - depreciation_now
    interest = debt_prev * (st.session_state["loan_rate"] / 100.0)
    ebt = ebit - interest
    tax = max(0, ebt * (st.session_state["tax_rate"] / 100.0))
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Steuern"] = tax
    row["Zinsaufwand"] = interest
    row["Jahresüberschuss"] = net_income
    
    # 6. Cashflow
    ar_end = gross_rev * (st.session_state["dso"]/365.0)
    ap_end = total_opex * (st.session_state["dpo"]/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    cf_op = net_income + depreciation_now - (ar_end - ar_prev) + (ap_end - ap_prev)
    cf_inv = -capex_now
    
    cash_start = results[-1]["Kasse"] if t > 1 else 0.0
    equity_in = st.session_state["equity"] if t == 1 else 0.0
    cash_pre_fin = cash_start + cf_op + cf_inv + equity_in
    
    gap = st.session_state["min_cash"] - cash_pre_fin
    borrow = gap if gap > 0 else 0
    repay = min(debt_prev, abs(gap)) if gap < 0 else 0
        
    cf_fin = equity_in + borrow - repay
    delta_cash = cf_op + cf_inv + cf_fin
    row["Net Cash Change"] = delta_cash
    
    cash = cash_start + delta_cash
    debt = debt_prev + borrow - repay
    
    # 7. Bilanz
    fixed_assets = max(0, fixed_assets + capex_now - depreciation_now)
    if t==1: retained_earnings = net_income
    else: retained_earnings += net_income
    eq_curr = st.session_state["equity"] + retained_earnings
    
    row["Kasse"] = cash
    row["Anlagevermögen"] = fixed_assets
    row["Forderungen"] = ar_end
    row["Summe Aktiva"] = cash + fixed_assets + ar_end
    row["Verb. LL"] = ap_end
    row["Bankdarlehen"] = debt
    row["Eigenkapital"] = eq_curr
    row["Summe Passiva"] = eq_curr + debt + ap_end
    row["Bilanz Check"] = row["Summe Aktiva"] - row["Summe Passiva"]
    row["Kreditaufnahme"] = borrow
    row["Tilgung"] = repay
    
    results.append(row)
    n_prev = n_t
    prev_ftes_by_role = current_ftes_by_role
    debt_prev = debt

df = pd.DataFrame(results)

# --- PDF DOWNLOAD SECTION ---
job_export_df = pd.DataFrame(st.session_state["current_jobs_df"])
prod_export_df = pd.DataFrame(st.session_state["products_df"])
cc_export_df = pd.DataFrame(st.session_state["cost_centers_df"])

pdf_bytes = create_detailed_pdf(df, st.session_state, job_export_df, prod_export_df, cc_export_df)
with col_io1:
    st.download_button("📄 Ausführlichen PDF Report herunterladen", pdf_bytes, "business_plan.pdf", "application/pdf", type="primary")

# --- OUTPUT TABS (Visualisierung) ---

with tab_costs:
    st.divider()
    st.subheader("Kostenübersicht")
    years = range(1, 11)
    manual_rows = []
    for cc_item in cc_config:
        nm = cc_item.get("Kostenstelle")
        if not nm: continue
        row_data = {"Kategorie": "Gemeinkosten", "Bezeichnung": nm}
        for y in years: row_data[y] = df.loc[df["Jahr"] == y, f"CC_{nm}"].values[0]
        manual_rows.append(row_data)
        
    other_cats = [("Personal", "Löhne", "Personalkosten"), ("Marketing", "Ads", "Marketing Kosten"), ("COGS", "Wareneinsatz", "Wareneinsatz (COGS)"), ("Assets", "AfA", "Abschreibungen")]
    for cat, bez, col in other_cats:
        r = {"Kategorie": cat, "Bezeichnung": bez}
        for y in years: r[y] = df.loc[df["Jahr"] == y, col].values[0]
        manual_rows.append(r)
        
    df_cost_overview = pd.DataFrame(manual_rows)
    st.dataframe(df_cost_overview.style.format({y: "{:,.0f} €" for y in years}), use_container_width=True, hide_index=True)
    st.bar_chart(df_cost_overview.melt(id_vars=["Bezeichnung", "Kategorie"], value_vars=years, var_name="Jahr", value_name="Kosten"), x="Jahr", y="Kosten", color="Kategorie", stack=True)

with tab_dash:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz J10", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA J10", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs J10", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse J10", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    st.subheader("Vergleich: Umsatz vs. Kosten")
    st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])

with tab_guv: 
    cols = ["Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_cf:
    cols = ["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_bilanz:
    c1, c2 = st.columns(2)
    with c1: st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Forderungen", "Summe Aktiva"]].T.style.format("€ {:,.0f}"))
    with c2: st.dataframe(df.set_index("Jahr")[["Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]].T.style.format("€ {:,.0f}"))
    if df["Bilanz Check"].abs().max() > 1: st.error("Bilanzfehler!")
    else: st.success("Bilanz ausgeglichen.")
