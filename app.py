import streamlit as st
import pandas as pd
import json
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime

# ==========================================
# 0. HILFSFUNKTIONEN & LOGIN
# ==========================================

def safe_float(value, default=0.0):
    """Konvertiert Eingaben sicher in float, fängt Fehler ab."""
    try:
        if value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value): 
            return default
        return float(value)
    except: 
        return default

def check_password():
    """Login Screen."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("## 🔒 Finanzmodell Pro - Login")
    st.caption("Standard: admin / 123")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.text_input("Benutzername")
        pwd = st.text_input("Passwort", type="password")
        if st.button("Anmelden", type="primary"):
            if user == "admin" and pwd == "123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Zugangsdaten falsch.")
    return False

# Start Prüfung
if not check_password():
    st.stop()

# Page Config
st.set_page_config(page_title="Finanzmodell Pro (Master)", layout="wide")

# Sidebar
st.sidebar.success("✅ Eingeloggt als Admin")
if st.sidebar.button("Abmelden"):
    st.session_state["password_correct"] = False
    st.rerun()

# ==========================================
# 1. STATUS & DEFAULTS INITIALISIEREN
# ==========================================

DEFAULTS = {
    # Markt
    "sam": 39000.0, "cap_pct": 2.3, "p_pct": 2.5, "q_pct": 38.0, "churn": 10.0, "manual_arpu": 3000.0,
    # Finanzierung
    "equity": 300000.0, "loan_initial": 0.0, "min_cash": 10000.0, "loan_rate": 5.0,
    # Personal Global
    "wage_inc": 1.5, "inflation": 2.0, "lnk_pct": 25.0, "target_rev_per_fte": 150000.0,
    # Working Capital & Tax
    "dso": 30, "dpo": 30, "tax_rate": 25.0, "cac": 3590.0,
    # Assets
    "price_desk": 2500, "price_laptop": 2000, "price_phone": 800, "price_car": 40000, "price_truck": 60000,
    "ul_desk": 13, "ul_laptop": 3, "ul_phone": 2, "ul_car": 6, "ul_truck": 8,
    "capex_annual": 5000, "depreciation_misc": 5,
}

# Werte initialisieren
for key, default_val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# DataFrames initialisieren

# 1. JOBS
if "current_jobs_df" not in st.session_state:
    defined_roles = [
        {"Job Titel": "Geschäftsführer", "Jahresgehalt (€)": 120000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Vertriebsleiter", "Jahresgehalt (€)": 80000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Sales Manager", "Jahresgehalt (€)": 50000.0, "FTE Jahr 1": 2.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500.0},
        {"Job Titel": "Marketing", "Jahresgehalt (€)": 45000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 2000.0},
    ]
    # Platzhalter auffüllen
    for i in range(len(defined_roles) + 1, 16):
        defined_roles.append({
            "Job Titel": f"Position {i}", "Jahresgehalt (€)": 0.0, "FTE Jahr 1": 0.0, 
            "Laptop": False, "Smartphone": False, "Auto": False, "LKW": False, "Büro": False, "Sonstiges (€)": 0.0
        })
    st.session_state["current_jobs_df"] = pd.DataFrame(defined_roles)

# 2. KOSTENSTELLEN
if "cost_centers_df" not in st.session_state:
    st.session_state["cost_centers_df"] = pd.DataFrame([
        {"Kostenstelle": "Büromaterial", "Grundwert Jahr 1 (€)": 1200, "Umsatz-Kopplung (%)": 10},
        {"Kostenstelle": "Reisekosten", "Grundwert Jahr 1 (€)": 5000, "Umsatz-Kopplung (%)": 50},
        {"Kostenstelle": "IT-Infrastruktur", "Grundwert Jahr 1 (€)": 2400, "Umsatz-Kopplung (%)": 20},
        {"Kostenstelle": "Rechtsberatung", "Grundwert Jahr 1 (€)": 1500, "Umsatz-Kopplung (%)": 0},
        {"Kostenstelle": "Versicherungen", "Grundwert Jahr 1 (€)": 3000, "Umsatz-Kopplung (%)": 0},
    ])

# 3. PRODUKTE
if "products_df" not in st.session_state:
    st.session_state["products_df"] = pd.DataFrame([
        {"Produkt": "Standard Abo", "Preis (€)": 100.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 15.0, "Take Rate (%)": 80.0, "Wiederkauf Rate (%)": 90.0, "Wiederkauf alle (Monate)": 12},
        {"Produkt": "Premium Add-On", "Preis (€)": 500.0, "Avg. Rabatt (%)": 5.0, "Herstellungskosten (COGS €)": 50.0, "Take Rate (%)": 20.0, "Wiederkauf Rate (%)": 50.0, "Wiederkauf alle (Monate)": 24},
        {"Produkt": "Setup Gebühr", "Preis (€)": 1000.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 100.0, "Take Rate (%)": 100.0, "Wiederkauf Rate (%)": 0.0, "Wiederkauf alle (Monate)": 0},
    ])

# ==========================================
# 2. PDF REPORT GENERATOR (Fixed Class)
# ==========================================

class PDFReport(FPDF):
    def fix_text(self, text):
        """Bereinigt Strings für Latin-1 Encoding (Euro-Zeichen Fix)."""
        if isinstance(text, (int, float)): return str(text)
        if text is None: return ""
        # Zeichen ersetzen
        text = str(text).replace("€", "EUR").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        # Sicherstellen, dass Encoding klappt
        return text.encode('latin-1', 'replace').decode('latin-1')

    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(44, 62, 80) 
        self.cell(0, 10, self.fix_text('Business Plan & Finanzmodell'), 0, 1, 'L')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, self.fix_text(f'Generiert am: {datetime.now().strftime("%d.%m.%Y")}'), 0, 1, 'L')
        self.set_draw_color(200, 200, 200)
        self.line(10, 25, 287, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, self.fix_text(f'Seite {self.page_no()}/{{nb}}'), 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102) 
        self.set_fill_color(230, 240, 255) 
        self.cell(0, 10, self.fix_text(title), 0, 1, 'L', 1)
        self.ln(4)

    def sub_title(self, title):
        self.set_font('Arial', 'B', 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, self.fix_text(title), 0, 1, 'L')

    def add_key_value_table(self, data_dict, title="Parameter"):
        self.sub_title(title)
        self.set_font('Arial', '', 9)
        col_width = 80
        row_height = 6
        for k, v in data_dict.items():
            self.set_font('Arial', 'B', 9)
            self.cell(col_width, row_height, self.fix_text(str(k)), 1)
            self.set_font('Arial', '', 9)
            val_str = f"{v:,.2f}" if isinstance(v, float) else str(v)
            self.cell(col_width, row_height, self.fix_text(val_str), 1)
            self.ln()
        self.ln(5)

    def add_dataframe_table(self, df, col_widths=None):
        self.set_font('Arial', 'B', 8)
        self.set_fill_color(240, 240, 240)
        
        # Spaltenbreiten berechnen
        if not col_widths:
            col_width = 277 / len(df.columns)
            widths = [col_width] * len(df.columns)
        else: 
            widths = col_widths
            
        # Header
        for i, col in enumerate(df.columns):
            self.cell(widths[i], 7, self.fix_text(str(col)), 1, 0, 'C', 1)
        self.ln()
        
        # Rows
        self.set_font('Arial', '', 8)
        for _, row in df.iterrows():
            for i, col in enumerate(df.columns):
                val = row[col]
                txt = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
                self.cell(widths[i], 6, self.fix_text(txt), 1, 0, 'R' if isinstance(val, (int, float)) else 'L')
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
    
    # SEITE 1: MANAGEMENT SUMMARY
    pdf.add_page()
    pdf.section_title("1. Management Summary & KPIs")
    
    if not df_results.empty:
        last = df_results.iloc[-1]
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, pdf.fix_text(f"Jahr 10 Prognose: Umsatz {last['Umsatz']:,.0f} EUR | EBITDA {last['EBITDA']:,.0f} EUR | Cash {last['Kasse']:,.0f} EUR"), 0, 1)
        pdf.ln(5)
        
        # Chart 1
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(df_results["Jahr"], df_results["Umsatz"], label="Umsatz", marker='o', linewidth=2)
        ax1.plot(df_results["Jahr"], df_results["Gesamtkosten (OPEX)"] + df_results["Wareneinsatz (COGS)"], label="Gesamtkosten", linestyle='--', color='red')
        ax1.bar(df_results["Jahr"], df_results["EBITDA"], label="EBITDA", alpha=0.3, color='green')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_title("Umsatz vs. Kosten & Profitabilitaet")
        pdf.add_chart(fig1)
        plt.close(fig1)

    # SEITE 2: EINGABEN
    pdf.add_page()
    pdf.section_title("2. Eingaben & Annahmen")
    
    # Tabelle Parameter
    pdf.add_key_value_table({
        "Marktpotenzial (SAM)": session_data.get("sam"), 
        "Eigenkapital Start": session_data.get("equity"), 
        "Min. Liquiditaet": session_data.get("min_cash")
    }, "Markt & Finanzierung")
    
    # Tabelle Jobs
    if jobs_data is not None and not jobs_data.empty:
        pdf.sub_title("Personalplanung")
        pdf.add_dataframe_table(jobs_data[["Job Titel", "Jahresgehalt (€)", "FTE Jahr 1"]].head(15))

    # SEITE 3: GuV
    pdf.add_page()
    pdf.section_title("3. Gewinn- und Verlustrechnung (GuV)")
    cols_guv = ["Jahr", "Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Steuern", "Jahresüberschuss"]
    exist = [c for c in cols_guv if c in df_results.columns]
    widths = [15] + [30] * (len(exist)-1)
    pdf.add_dataframe_table(df_results[exist], col_widths=widths)

    # SEITE 4: CASHFLOW & BILANZ
    pdf.add_page()
    pdf.section_title("4. Cashflow & Bilanz")
    
    cols_cf = ["Jahr", "Jahresüberschuss", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    pdf.add_dataframe_table(df_results[cols_cf])
    
    pdf.ln(5)
    # Chart 2
    fig2, ax2 = plt.subplots(figsize=(10, 3.5))
    ax2.fill_between(df_results["Jahr"], df_results["Kasse"], color="skyblue", alpha=0.4, label="Kasse")
    ax2.plot(df_results["Jahr"], df_results["Bankdarlehen"], color="red", linestyle="--", label="Bankkredit")
    ax2.legend()
    ax2.set_title("Liquiditaet vs. Verbindlichkeiten")
    pdf.add_chart(fig2)
    plt.close(fig2)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 3. UI LAYOUT & TABS
# ==========================================

st.title("Integriertes Finanzmodell: Cash Sweep & Asset Management")

col_top1, col_top2 = st.columns([1, 3])
with col_top1:
    if st.button("🔄 NEU BERECHNEN", type="primary", use_container_width=True): 
        st.rerun()

# Import / Export
with st.expander("📂 Import / Export (JSON)", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        # Dataframes packen
        if "current_jobs_df" in st.session_state:
             df = pd.DataFrame(st.session_state["current_jobs_df"])
             for col in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
                 if col in df.columns: df[col] = df[col].apply(bool)
             config_data["jobs_data"] = df.to_dict('records')
        if "cost_centers_df" in st.session_state:
             config_data["cc_data"] = pd.DataFrame(st.session_state["cost_centers_df"]).to_dict('records')
        if "products_df" in st.session_state:
             config_data["prod_data"] = pd.DataFrame(st.session_state["products_df"]).to_dict('records')
        
        st.download_button("💾 Config Speichern", json.dumps(config_data, indent=2), "model_config.json")
    with c2:
        up = st.file_uploader("Config Laden", type=["json"])
        if up:
            if st.button("Importieren"):
                d = json.load(up)
                for k,v in d.items():
                    if k in DEFAULTS: st.session_state[k] = v
                if "jobs_data" in d: st.session_state["current_jobs_df"] = pd.DataFrame(d["jobs_data"])
                if "cc_data" in d: st.session_state["cost_centers_df"] = pd.DataFrame(d["cc_data"])
                if "prod_data" in d: st.session_state["products_df"] = pd.DataFrame(d["prod_data"])
                st.rerun()

# Tab Navigation
tab_input, tab_prod, tab_assets, tab_jobs, tab_cc, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt", "📦 Produkte", "📉 Assets", "👥 Personal", "🏢 Kostenstellen", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# --- TAB INHALTE ---

with tab_input:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Markt")
        st.number_input("SAM (Marktpotenzial)", step=1000.0, key="sam")
        st.number_input("Marktanteil Ziel %", step=0.1, key="cap_pct")
        st.number_input("Churn Rate %", step=1.0, key="churn")
        st.number_input("Manueller ARPU (Fallback)", step=100.0, key="manual_arpu")
    with c2:
        st.subheader("Finanzierung")
        st.number_input("Eigenkapital Start (€)", step=5000.0, key="equity", help="Startguthaben")
        st.number_input("Start-Kredit (€)", step=5000.0, key="loan_initial")
        st.number_input("Mindest-Cash (€)", step=5000.0, key="min_cash", help="Puffer")
        st.number_input("Kredit-Zins %", step=0.1, key="loan_rate")
        st.markdown("---")
        st.number_input("Steuersatz %", step=1.0, key="tax_rate")
        st.number_input("Lohnsteigerung %", step=0.1, key="wage_inc")
        st.number_input("Inflation %", step=0.1, key="inflation")

with tab_prod:
    st.info("Produkte definieren. Diese Werte steuern Umsatz & COGS.")
    edited_products = st.data_editor(st.session_state["products_df"], num_rows="fixed", use_container_width=True, key="ed_prod")
    st.session_state["products_df"] = edited_products

with tab_assets:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("IT Hardware")
        st.number_input("Laptop Preis", key="price_laptop")
        st.number_input("Laptop Dauer", key="ul_laptop")
        st.number_input("Handy Preis", key="price_phone")
        st.number_input("Handy Dauer", key="ul_phone")
    with c2:
        st.caption("Fahrzeuge")
        st.number_input("PKW Preis", key="price_car")
        st.number_input("PKW Dauer", key="ul_car")
        st.number_input("LKW Preis", key="price_truck")
        st.number_input("LKW Dauer", key="ul_truck")
    with c3:
        st.caption("Büro & Sonstiges")
        st.number_input("Büroplatz Preis", key="price_desk")
        st.number_input("Büro Dauer", key="ul_desk")
        st.number_input("Sonstiges Capex p.a.", key="capex_annual")
        st.number_input("AfA Dauer Sonst.", key="depreciation_misc")

with tab_jobs:
    st.number_input("Ziel-Umsatz je FTE (€)", step=5000.0, key="target_rev_per_fte")
    edited_jobs = st.data_editor(st.session_state["current_jobs_df"], num_rows="fixed", use_container_width=True, key="ed_jobs")
    st.session_state["current_jobs_df"] = edited_jobs

with tab_cc:
    st.info("Kostenstellen mit Umsatzkopplung definieren.")
    edited_cc = st.data_editor(st.session_state["cost_centers_df"], num_rows="dynamic", use_container_width=True, key="ed_cc")
    st.session_state["cost_centers_df"] = edited_cc

# ==========================================
# 4. BERECHNUNGSLOGIK (CORE ENGINE)
# ==========================================

# Inputs vorbereiten
jobs = pd.DataFrame(st.session_state["current_jobs_df"]).to_dict('records')
products = pd.DataFrame(st.session_state["products_df"]).to_dict('records')
ccs = pd.DataFrame(st.session_state["cost_centers_df"]).to_dict('records')

# 1. Produkt-Mix (ARPU & COGS Ratio)
w_arpu, w_cogs = 0.0, 0.0
has_prod = False

for p in products:
    pr = safe_float(p.get("Preis (€)"))
    if pr > 0:
        has_prod = True
        cogs_unit = safe_float(p.get("Herstellungskosten (COGS €)"))
        take = safe_float(p.get("Take Rate (%)")) / 100.0
        months = safe_float(p.get("Wiederkauf alle (Monate)"))
        # Frequenz pro Jahr berechnen
        freq = 1.0
        if months > 0:
            cycles = 12.0 / months
            repurchase = safe_float(p.get("Wiederkauf Rate (%)")) / 100.0
            freq = 1.0 + (repurchase * (cycles - 1)) if cycles >= 1 else 1.0
        
        w_arpu += (pr * take * freq)
        w_cogs += (cogs_unit * take * freq)

# Fallback wenn keine Produkte da sind
if has_prod and w_arpu > 0:
    calc_arpu = w_arpu
    calc_cogs_ratio = w_cogs / w_arpu
else:
    calc_arpu = st.session_state["manual_arpu"]
    calc_cogs_ratio = 0.15 # Fallback Annahme

# Konstanten
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
N_start = 10.0

# Initialisierung Simulation
n_prev = N_start
debt = st.session_state["loan_initial"]
# WICHTIG: Cash ist Start-Equity
cash = st.session_state["equity"] 
loss_carryforward = 0.0 # Verlustvortrag
retained_earnings = 0.0
fixed_assets = 0.0
results = []
prev_cc = {}
asset_types = {
    "Laptop": {"price": "price_laptop", "ul": "ul_laptop"},
    "Smartphone": {"price": "price_phone", "ul": "ul_phone"},
    "Auto": {"price": "price_car", "ul": "ul_car"},
    "LKW": {"price": "price_truck", "ul": "ul_truck"},
    "Büro": {"price": "price_desk", "ul": "ul_desk"},
}
# Asset Register (Liste von Käufen)
asset_register = {k: [] for k in asset_types.keys()}
asset_register["Misc"] = []

# --- LOOP JAHRE 1 BIS 10 ---
for t in range(1, 11):
    row = {"Jahr": t}
    
    # A. Umsatz
    pot = max(0, st.session_state["sam"] * (st.session_state["cap_pct"]/100) - n_prev)
    adopt = P + Q * (n_prev / (st.session_state["sam"] or 1))
    n_t = n_prev * (1 - st.session_state["churn"]/100) + (adopt * pot) if t > 1 else N_start
    row["Kunden"] = n_t
    revenue = n_t * calc_arpu
    row["Umsatz"] = revenue
    
    # Wachstum berechnen (für Kostenstellen)
    prev_rev = results[-1]["Umsatz"] if t > 1 else revenue
    growth = (revenue - prev_rev)/prev_rev if (t > 1 and prev_rev > 0) else 0.0

    # B. Kosten
    
    # 1. COGS
    cogs = revenue * calc_cogs_ratio
    row["Wareneinsatz (COGS)"] = cogs
    
    # 2. Personal (OPEX)
    wage_factor = (1 + st.session_state["wage_inc"]/100)**(t-1)
    personnel_cost = 0.0
    target_ftes = revenue / st.session_state["target_rev_per_fte"] if st.session_state["target_rev_per_fte"] > 0 else 0
    curr_ftes = {}
    
    # Hardware Bedarf ermitteln
    asset_needs = {k: 0.0 for k in asset_types.keys()}
    total_base_fte = sum(safe_float(j.get("FTE Jahr 1")) for j in jobs)
    
    for job in jobs:
        role = job.get("Job Titel")
        base = safe_float(job.get("FTE Jahr 1"))
        sal = safe_float(job.get("Jahresgehalt (€)"))
        
        # FTE Scaling
        if t == 1: fte = base
        else:
            share = base / total_base_fte if total_base_fte > 0 else 0
            fte = max(base, target_ftes * share) 
        
        personnel_cost += (sal * fte * wage_factor * (1 + st.session_state["lnk_pct"]/100))
        curr_ftes[role] = fte
        
        # Assets zählen
        if job.get("Laptop"): asset_needs["Laptop"] += fte
        if job.get("Smartphone"): asset_needs["Smartphone"] += fte
        if job.get("Auto"): asset_needs["Auto"] += fte
        if job.get("LKW"): asset_needs["LKW"] += fte
        if job.get("Büro"): asset_needs["Büro"] += fte

    row["Personalkosten"] = personnel_cost
    row["FTE Total"] = sum(curr_ftes.values())
    
    # 3. Kostenstellen (OPEX)
    cc_cost = 0.0
    for c in ccs:
        nm = c.get("Kostenstelle")
        if not nm: continue
        base_val = safe_float(c.get("Grundwert Jahr 1 (€)"))
        coup = safe_float(c.get("Umsatz-Kopplung (%)")) / 100.0
        
        last_val = prev_cc.get(nm, base_val)
        curr_val = base_val if t == 1 else last_val * (1 + (growth * coup))
        
        prev_cc[nm] = curr_val
        cc_cost += curr_val
        row[f"CC_{nm}"] = curr_val # Speichern für Detail-Tab
        
    # 4. Marketing & Sonstiges (OPEX)
    mkt_cost = n_t * st.session_state["cac"]
    row["Marketing Kosten"] = mkt_cost
    misc_opex = revenue * 0.02
    
    # C. CAPEX & AFA
    capex_now = 0.0
    depr_now = 0.0
    
    # Misc Capex
    misc_inv = st.session_state["capex_annual"]
    asset_register["Misc"].append({"year": t, "amount": 1, "cost": misc_inv, "ul": st.session_state["depreciation_misc"]})
    capex_now += misc_inv
    
    # Hardware Capex
    for k, needed in asset_needs.items():
        price = st.session_state[asset_types[k]["price"]]
        ul = st.session_state[asset_types[k]["ul"]]
        
        # Verfügbare Assets prüfen (die noch nicht abgelaufen sind)
        available = sum(p["amount"] for p in asset_register[k] if (t - p["year"]) < p["ul"])
        buy = max(0, needed - available)
        
        if buy > 0:
            cost = buy * price
            capex_now += cost
            asset_register[k].append({"year": t, "amount": buy, "cost": cost, "ul": ul})
            
    # AfA berechnen
    for cat, purchases in asset_register.items():
        for p in purchases:
            if 0 <= (t - p["year"]) < p["ul"]:
                depr_now += p["cost"] / p["ul"]
                
    row["Abschreibungen"] = depr_now
    row["Investitionen (Assets)"] = capex_now
    
    # D. ERGEBNIS RECHNUNG
    opex = personnel_cost + cc_cost + mkt_cost + misc_opex
    row["Gesamtkosten (OPEX)"] = opex
    
    # KORREKTUR: EBITDA = UMSATZ - COGS - OPEX
    ebitda = revenue - cogs - opex
    row["EBITDA"] = ebitda
    
    ebit = ebitda - depr_now
    row["EBIT"] = ebit
    
    interest = debt * (st.session_state["loan_rate"]/100.0)
    row["Zinsaufwand"] = interest
    ebt = ebit - interest
    
    # KORREKTUR: Steuer mit Verlustvortrag
    if ebt < 0:
        loss_carryforward += abs(ebt)
        tax = 0.0
    else:
        used_loss = min(ebt, loss_carryforward)
        taxable_income = ebt - used_loss
        loss_carryforward -= used_loss
        tax = taxable_income * (st.session_state["tax_rate"]/100.0)
    
    row["Steuern"] = tax
    net_income = ebt - tax
    row["Jahresüberschuss"] = net_income
    
    # E. CASHFLOW & SWEEP
    
    # Operativer CF
    cf_op = net_income + depr_now
    # Investitions CF
    cf_inv = -capex_now
    
    # Cash vor Finanzierung
    # Start-Cash ist End-Cash des Vorjahres (oder Equity in Jahr 1)
    cash_begin = results[-1]["Kasse"] if t > 1 else st.session_state["equity"]
    
    cash_before_fin = cash_begin + cf_op + cf_inv
    
    # Kredit Logic
    min_c = st.session_state["min_cash"]
    borrow = 0.0
    repay = 0.0
    
    if cash_before_fin < min_c:
        borrow = min_c - cash_before_fin
    elif cash_before_fin > min_c and debt > 0:
        repay = min(debt, cash_before_fin - min_c)
        
    cf_fin = borrow - repay
    delta_cash = cf_op + cf_inv + cf_fin
    row["Net Cash Change"] = delta_cash
    
    cash_end = cash_before_fin + cf_fin
    debt_end = debt + borrow - repay
    
    # State Updates
    cash = cash_end
    debt = debt_end
    n_prev = n_t
    fixed_assets = max(0, fixed_assets + capex_now - depr_now)
    retained_earnings += net_income
    
    row["Kasse"] = cash_end
    row["Bankdarlehen"] = debt_end
    row["Kreditaufnahme"] = borrow
    row["Tilgung"] = repay
    
    # Bilanz
    row["Anlagevermögen"] = fixed_assets
    row["Eigenkapital"] = st.session_state["equity"] + retained_earnings
    row["Summe Aktiva"] = fixed_assets + cash_end
    row["Summe Passiva"] = row["Eigenkapital"] + debt_end
    
    results.append(row)

df = pd.DataFrame(results)

# ==========================================
# 5. OUTPUTS & DASHBOARD
# ==========================================

# PDF Download Button
with col_top2:
    pdf_bytes = create_detailed_pdf(
        df, st.session_state, 
        pd.DataFrame(st.session_state["current_jobs_df"]), 
        pd.DataFrame(st.session_state["products_df"]), 
        pd.DataFrame(st.session_state["cost_centers_df"])
    )
    st.download_button("📄 PDF REPORT LADEN", pdf_bytes, "business_plan.pdf", "application/pdf")

with tab_dash:
    k1, k2, k3 = st.columns(3)
    k1.metric("Umsatz J10", f"{df.iloc[-1]['Umsatz']:,.0f} €")
    k2.metric("EBITDA J10", f"{df.iloc[-1]['EBITDA']:,.0f} €")
    k3.metric("Kasse J10", f"{df.iloc[-1]['Kasse']:,.0f} €")
    
    st.write("### Plausibilitäts-Check (Jahr 1)")
    # Debug View für den User
    r1 = df.iloc[0]
    st.code(f"""
    Umsatz: {r1['Umsatz']:,.0f}
    - COGS: {r1['Wareneinsatz (COGS)']:,.0f}
    - OPEX: {r1['Gesamtkosten (OPEX)']:,.0f}
    = EBITDA: {r1['EBITDA']:,.0f}
    
    Cash Start: {st.session_state['equity']:,.0f} (Equity)
    + Net Cash Change: {r1['Net Cash Change']:,.0f}
    = Kasse Ende: {r1['Kasse']:,.0f}
    """)
    st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])

with tab_guv:
    st.dataframe(df.set_index("Jahr")[["Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "EBIT", "Steuern", "Jahresüberschuss"]].T.style.format("{:,.0f}"))

with tab_cf:
    st.dataframe(df.set_index("Jahr")[["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]].T.style.format("{:,.0f}"))

with tab_bilanz:
    st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Summe Aktiva", "Eigenkapital", "Bankdarlehen", "Summe Passiva"]].T.style.format("{:,.0f}"))
