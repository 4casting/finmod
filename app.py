import streamlit as st
import pandas as pd
import math
import json
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime

# --- LOGIN FUNKTION ---
def check_password():
    """Gibt True zurück, wenn das Passwort korrekt ist."""

    # Prüfen, ob das Passwort schon in der Session ist
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Eingabefelder für Login
    st.markdown("## 🔒 Bitte einloggen")
    
    # Hier können Sie Benutzername/Passwort festlegen
    # In einer echten App sollten diese idealerweise in st.secrets stehen
    user = st.text_input("Benutzername")
    pwd = st.text_input("Passwort", type="password")
    
    if st.button("Anmelden"):
        # BEISPIEL: User="admin", Passwort="123"
        if user == "admin" and pwd == "123":
            st.session_state["password_correct"] = True
            st.rerun()  # App neu laden, um Inhalt anzuzeigen
        else:
            st.error("Falscher Benutzername oder Passwort")
            
    return False

# --- HAUPTPROGRAMM ---
# Nur wenn Login erfolgreich, läuft der Rest des Codes weiter
if not check_password():
    st.stop()  # Stoppt die Ausführung hier, wenn nicht eingeloggt

# ... HIER BEGINNT IHR NORMALER CODE (Inputs, Tabs etc.) ...
st.sidebar.success("Eingeloggt als Admin")
if st.sidebar.button("Abmelden"):
    st.session_state["password_correct"] = False
    st.rerun()

# --- KONFIGURATION ---
st.set_page_config(page_title="Finanzmodell Pro", layout="wide")

# --- 1. DEFINITION DER STANDARDS (ZENTRAL) ---
DEFAULTS = {
    # Markt & Wachstum
    "sam": 39000.0, "cap_pct": 2.3, "p_pct": 2.5, "q_pct": 38.0, "churn": 10.0, "arpu": 3000.0, "discount": 0.0,
    # Finanzierung
    "equity": 100000.0, "loan_initial": 0.0, "min_cash": 100000.0, "loan_rate": 5.0,
    # Personal Global
    "wage_inc": 1.5, "inflation": 2.0, "lnk_pct": 25.0, "target_rev_per_fte": 150000.0,
    # Working Capital & Tax
    "dso": 30, "dpo": 30, "tax_rate": 30.0, "cac": 3590.0,
    # Assets PREISE
    "price_desk": 2500, "price_laptop": 2000, "price_phone": 800, "price_car": 40000, "price_truck": 60000,
    # Assets NUTZUNGSDAUER (Jahre)
    "ul_desk": 13, "ul_laptop": 3, "ul_phone": 2, "ul_car": 6, "ul_truck": 8,
    # Sonstiges
    "capex_annual": 5000, "depreciation_misc": 5
}

# --- 2. INITIALISIERUNG STATE ---
for key, default_val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# Jobs Tabelle Initialisieren
if "current_jobs_df" not in st.session_state:
    defined_roles = [
        {"Job Titel": "Geschäftsführer", "Jahresgehalt (€)": 120000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Vertriebsleiter", "Jahresgehalt (€)": 80000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Sales Manager", "Jahresgehalt (€)": 50000.0, "FTE Jahr 1": 3.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500.0},
        {"Job Titel": "Marketing", "Jahresgehalt (€)": 45000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 2000.0},
        {"Job Titel": "Techniker", "Jahresgehalt (€)": 40000.0, "FTE Jahr 1": 2.0, "Laptop": False, "Smartphone": True, "Auto": False, "LKW": True, "Büro": False, "Sonstiges (€)": 1000.0},
        {"Job Titel": "Buchhaltung", "Jahresgehalt (€)": 42000.0, "FTE Jahr 1": 0.5, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
    ]
    # Auffüllen auf 15 Slots
    for i in range(len(defined_roles) + 1, 16):
        defined_roles.append({
            "Job Titel": f"Position {i} (Platzhalter)", "Jahresgehalt (€)": 0.0, "FTE Jahr 1": 0.0, 
            "Laptop": False, "Smartphone": False, "Auto": False, "LKW": False, "Büro": False, "Sonstiges (€)": 0.0
        })
    st.session_state["current_jobs_df"] = pd.DataFrame(defined_roles)

# --- HILFSFUNKTIONEN ---
def safe_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value): return default
        return float(value)
    except: return default

# --- PDF GENERATOR ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Integrierter Finanzplan & Business Case', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Erstellt am: {datetime.now().strftime("%d.%m.%Y")}', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Seite {self.page_no()}/{{nb}}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 230, 255)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)
    def add_table(self, df, title=None, col_width=25):
        if title: self.chapter_title(title)
        self.set_font('Arial', 'B', 7)
        self.cell(35, 6, "", 1)
        for col in df.columns: self.cell(col_width, 6, str(col), 1, 0, 'C')
        self.ln()
        self.set_font('Arial', '', 7)
        for index, row in df.iterrows():
            self.cell(35, 6, str(index), 1)
            for col in df.columns:
                val = row[col]
                txt = f"{val:,.0f}".replace(",", ".") if isinstance(val, (int, float)) else str(val)
                self.cell(col_width, 6, txt, 1, 0, 'R')
            self.ln()
        self.ln(5)
    def add_plot(self, fig):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            fig.savefig(tmpfile.name, dpi=100, bbox_inches='tight')
            self.image(tmpfile.name, w=270)

def create_pdf(df_results, inputs, jobs_df):
    pdf = PDFReport(orientation='L', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # 1. Management Summary
    pdf.chapter_title("Management Summary (Jahr 10)")
    pdf.set_font('Arial', '', 10)
    if not df_results.empty:
        kpi = df_results.iloc[-1]
        pdf.cell(60, 10, f"Umsatz: {kpi.get('Umsatz',0):,.0f} EUR", 0, 0)
        pdf.cell(60, 10, f"EBITDA: {kpi.get('EBITDA',0):,.0f} EUR", 0, 0)
        pdf.cell(60, 10, f"Cash: {kpi.get('Kasse',0):,.0f} EUR", 0, 1)
    pdf.ln(5)

    # 2. GuV
    cols = ["Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    existing_cols = [c for c in cols if c in df_results.columns]
    if existing_cols:
        pdf.add_table(df_results.set_index("Jahr")[existing_cols].T, "Gewinn- und Verlustrechnung (GuV)")

    # 3. Cashflow
    pdf.add_page()
    cf_cols = ["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    existing_cf = [c for c in cf_cols if c in df_results.columns]
    if existing_cf:
        pdf.add_table(df_results.set_index("Jahr")[existing_cf].T, "Kapitalflussrechnung")

    # 4. Bilanz (GETRENNT)
    pdf.add_page()
    pdf.chapter_title("Bilanz")
    
    # Aktiva
    aktiva_cols = ["Anlagevermögen", "Kasse", "Forderungen", "Summe Aktiva"]
    existing_akt = [c for c in aktiva_cols if c in df_results.columns]
    if existing_akt:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, "Aktiva (Mittelverwendung)", 0, 1)
        pdf.add_table(df_results.set_index("Jahr")[existing_akt].T)
    
    pdf.ln(5)
    
    # Passiva
    passiva_cols = ["Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]
    existing_pass = [c for c in passiva_cols if c in df_results.columns]
    if existing_pass:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, "Passiva (Mittelherkunft)", 0, 1)
        pdf.add_table(df_results.set_index("Jahr")[existing_pass].T)

    # 5. Charts
    pdf.add_page()
    pdf.chapter_title("Finanzielle Entwicklung")
    if not df_results.empty:
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(df_results["Jahr"], df_results["Umsatz"], label="Umsatz")
        ax1.bar(df_results["Jahr"], df_results["EBITDA"], label="EBITDA", alpha=0.5, color="green")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        pdf.add_plot(fig1)
        plt.close(fig1)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- HEADER & BUTTONS ---
st.title("Integriertes Finanzmodell: Cash Sweep & Asset Management")

col_main_act1, col_main_act2 = st.columns([1, 3])
with col_main_act1:
    if st.button("🔄 MODELL JETZT NEU BERECHNEN", type="primary", use_container_width=True):
        st.rerun()
with col_main_act2:
    st.info("💡 Klicken Sie links, um nach Änderungen die Berechnung zu aktualisieren.")

# --- SZENARIO MANAGER ---
with st.expander("📂 Datei Speichern & Laden (Import/Export)", expanded=True):
    col_io1, col_io2 = st.columns(2)
    with col_io1:
        st.markdown("##### 1. Speichern")
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        if "current_jobs_df" in st.session_state:
             df_export = st.session_state["current_jobs_df"].fillna(0).copy()
             for c in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
                 if c in df_export.columns: df_export[c] = df_export[c].apply(bool)
             config_data["jobs_data"] = df_export.to_dict(orient="records")
        st.download_button("💾 Als JSON herunterladen", json.dumps(config_data, indent=2), "finanzmodell_config.json", "application/json")

    with col_io2:
        st.markdown("##### 2. Laden")
        uploaded_file = st.file_uploader("JSON-Datei hier hereinziehen:", type=["json"])
        if uploaded_file is not None:
            c_imp = st.container()
            c_imp.success("Datei erkannt!")
            if c_imp.button("📥 Importieren & Anwenden", type="secondary"):
                try:
                    data = json.load(uploaded_file)
                    for key, val in data.items():
                        if key in DEFAULTS: st.session_state[key] = val
                    if "jobs_data" in data:
                        new_df = pd.DataFrame(data["jobs_data"])
                        st.session_state["current_jobs_df"] = new_df
                        if "job_editor_widget" in st.session_state: del st.session_state["job_editor_widget"]
                    st.toast("Import erfolgreich!", icon="✅")
                    st.rerun()
                except Exception as e: st.error(f"Fehler: {e}")

# --- TABS ---
tab_input, tab_assets, tab_jobs, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt & Finanzen", "📉 Abschreibungen & Assets", "👥 Personal & Jobs", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# --- TAB 1: MARKT ---
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
        st.subheader("Umsatz")
        st.number_input("ARPU (€)", step=100.0, key="arpu")
        st.slider("Rabatte %", 0.0, 20.0, key="discount")

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

# --- TAB 2: ABSCHREIBUNGEN ---
with tab_assets:
    st.header("Asset Management & AfA")
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        st.subheader("IT & Kommunikation")
        st.number_input("Laptop Preis (€)", key="price_laptop")
        st.number_input("Laptop Dauer (Jahre)", key="ul_laptop", min_value=1)
        st.markdown("---")
        st.number_input("Handy Preis (€)", key="price_phone")
        st.number_input("Handy Dauer (Jahre)", key="ul_phone", min_value=1)
        
    with col_a2:
        st.subheader("Mobilität")
        st.number_input("PKW Preis (€)", key="price_car")
        st.number_input("PKW Dauer (Jahre)", key="ul_car", min_value=1)
        st.markdown("---")
        st.number_input("LKW Preis (€)", key="price_truck")
        st.number_input("LKW Dauer (Jahre)", key="ul_truck", min_value=1)

    with col_a3:
        st.subheader("Sonstiges")
        st.number_input("Büroplatz Preis (€)", key="price_desk")
        st.number_input("Büro Dauer (Jahre)", key="ul_desk", min_value=1)
        st.markdown("---")
        st.number_input("Sonstiges Capex p.a. (Pauschale €)", key="capex_annual")
        st.number_input("AfA Dauer Sonstiges (Jahre)", key="depreciation_misc")

# --- TAB 3: JOBS ---
with tab_jobs:
    st.header("Personalplanung")
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.number_input("Ziel-Umsatz je FTE (€/Jahr)", step=5000.0, key="target_rev_per_fte", help="Steuert den Personalbedarf.")
        
    st.subheader("Job Definitionen (15 Slots)")
    df_edit = st.session_state["current_jobs_df"].copy()
    for c in ["Jahresgehalt (€)", "FTE Jahr 1", "Sonstiges (€)"]:
        df_edit[c] = pd.to_numeric(df_edit[c], errors='coerce').fillna(0.0)
        
    edited_jobs = st.data_editor(
        df_edit,
        num_rows="fixed",
        use_container_width=True,
        key="job_editor_widget",
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

# --- BERECHNUNG ---

# Jobs Parsen
jobs_config = edited_jobs.to_dict(orient="records")
valid_jobs = []
for job in jobs_config:
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
    for k in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
        job[k] = bool(job.get(k))
    
    setup = job["Sonstiges (€)"] 
    job["_setup_opex"] = setup
    valid_jobs.append(job)

# Konstanten
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
CHURN = st.session_state["churn"] / 100.0
N_start = 10.0 
revenue_y1 = N_start * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)

# Asset Register Initialisierung
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

cash = 0.0
fixed_assets = 0.0
debt = st.session_state["loan_initial"]
retained_earnings = 0.0
wage_factor = 1.0
debt_prev = st.session_state["loan_initial"]

asset_details_log = []

for t in range(1, 11):
    row = {"Jahr": t}
    
    # Markt
    if t == 1: n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    net_rev = n_t * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
    row["Umsatz"] = net_rev
    
    # Personal
    target_total_fte = 0
    if st.session_state["target_rev_per_fte"] > 0:
        target_total_fte = net_rev / st.session_state["target_rev_per_fte"]
        
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
    
    # Asset Berechnung
    capex_now = 0.0
    depreciation_now = 0.0
    
    # Misc
    capex_misc = st.session_state["capex_annual"]
    asset_register["Misc"].append({
        "year": t, "amount": 1, "price": capex_misc, "total_cost": capex_misc, "ul": st.session_state["depreciation_misc"]
    })
    capex_now += capex_misc
    
    # Specific Assets
    for atype, needed in asset_needs.items():
        price = st.session_state[asset_types[atype]["price_key"]]
        ul = st.session_state[asset_types[atype]["ul_key"]]
        
        valid = 0
        for p in asset_register[atype]:
            if (t - p["year"]) < p["ul"]: valid += p["amount"]
            
        buy = max(0, needed - valid)
        if buy > 0:
            cost = buy * price
            capex_now += cost
            asset_register[atype].append({
                "year": t, "amount": buy, "price": price, "total_cost": cost, "ul": ul
            })
            
    # AfA
    for atype, purchases in asset_register.items():
        type_depr = 0
        for p in purchases:
            age = t - p["year"]
            if 0 <= age < p["ul"]:
                type_depr += p["total_cost"] / p["ul"]
        depreciation_now += type_depr
        asset_details_log.append({"Jahr": t, "Typ": atype, "Invest (€)": sum(p["total_cost"] for p in purchases if p["year"]==t), "AfA (€)": type_depr})

    row["Investitionen (Assets)"] = capex_now
    row["Abschreibungen"] = depreciation_now
    
    # GuV
    cost_mkt = n_t * st.session_state["cac"]
    cost_cogs = net_rev * 0.10
    cost_cons = net_rev * 0.02
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_cons + setup_opex
    row["Gesamtkosten (OPEX)"] = total_opex
    ebitda = net_rev - total_opex
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
    
    # Cashflow
    ar_end = net_rev * (st.session_state["dso"]/365.0)
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
    
    # Bilanz
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
df_assets_log = pd.DataFrame(asset_details_log)

# --- PDF ERSTELLUNG ---
pdf_bytes = create_pdf(df, st.session_state, pd.DataFrame(valid_jobs))

with col_io1:
    st.download_button(
        label="📄 PDF Report herunterladen",
        data=pdf_bytes,
        file_name="finanzreport.pdf",
        mime="application/pdf",
        type="primary"
    )

# --- VISUALISIERUNG ---
with tab_assets:
    st.subheader("Anlagen & AfA Detail")
    if not df_assets_log.empty:
        c1, c2 = st.columns(2)
        c1.dataframe(df_assets_log.pivot(index="Jahr", columns="Typ", values="Invest (€)").style.format("{:,.0f}"))
        c2.dataframe(df_assets_log.pivot(index="Jahr", columns="Typ", values="AfA (€)").style.format("{:,.0f}"))

with tab_dash:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz J10", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA J10", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs J10", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse J10", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    st.line_chart(df.set_index("Jahr")[["Kasse", "Bankdarlehen"]])
    st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])

# Tabellen
with tab_guv: 
    cols = ["Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_cf:
    cols = ["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_bilanz:
    st.subheader("Bilanzstruktur")
    c1, c2 = st.columns(2)
    
    # Trennung Aktiva / Passiva
    aktiva_cols = ["Anlagevermögen", "Kasse", "Forderungen", "Summe Aktiva"]
    passiva_cols = ["Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]
    
    with c1:
        st.markdown("**Aktiva**")
        st.dataframe(df.set_index("Jahr")[aktiva_cols].T.style.format("€ {:,.0f}"))
    with c2:
        st.markdown("**Passiva**")
        st.dataframe(df.set_index("Jahr")[passiva_cols].T.style.format("€ {:,.0f}"))
    
    if df["Bilanz Check"].abs().max() > 1: st.error("Bilanzfehler!")
    else: st.success("Bilanz ist ausgeglichen.")

