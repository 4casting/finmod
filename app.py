import streamlit as st
import pandas as pd
import math
import json
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime

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
    # Assets
    "price_desk": 2500, "price_laptop": 2000, "price_phone": 800, "price_car": 40000, "price_truck": 60000,
    "capex_annual": 5000, "depreciation": 5
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

# --- PDF GENERATOR KLASSE ---
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
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def add_table(self, df, title=None, col_width=25):
        if title:
            self.chapter_title(title)
        
        self.set_font('Arial', 'B', 7) # Kleinere Schrift für breite Tabellen
        
        # Header
        self.cell(40, 7, "", 1)
        for col in df.columns:
            self.cell(col_width, 7, str(col), 1, 0, 'C')
        self.ln()
        
        # Rows
        self.set_font('Arial', '', 7)
        for index, row in df.iterrows():
            self.cell(40, 7, str(index), 1) # Zeilenbeschriftung
            for col in df.columns:
                val = row[col]
                if isinstance(val, (int, float)):
                    txt = f"{val:,.0f}".replace(",", ".")
                else:
                    txt = str(val)
                self.cell(col_width, 7, txt, 1, 0, 'R')
            self.ln()
        self.ln(10)

    def add_plot(self, fig):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            fig.savefig(tmpfile.name, dpi=100, bbox_inches='tight')
            self.image(tmpfile.name, w=260) 

# Funktion zum Generieren des PDF
def create_pdf(df_results, inputs, jobs_df):
    pdf = PDFReport(orientation='L', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # 1. Management Summary
    pdf.chapter_title("Management Summary (Jahr 10)")
    pdf.set_font('Arial', '', 10)
    
    kpi_cols = ["Umsatz", "EBITDA", "Jahresüberschuss", "Kasse", "FTE Total"]
    kpi_vals = df_results.iloc[-1][kpi_cols]
    
    pdf.cell(60, 10, f"Umsatz: {kpi_vals['Umsatz']:,.0f} EUR", 0, 0)
    pdf.cell(60, 10, f"EBITDA: {kpi_vals['EBITDA']:,.0f} EUR", 0, 0)
    pdf.cell(60, 10, f"Cash (Y10): {kpi_vals['Kasse']:,.0f} EUR", 0, 1)
    pdf.ln(5)

    # 2. Input Übersicht
    pdf.chapter_title("Wichtigste Annahmen")
    pdf.set_font('Arial', '', 8)
    input_text = f"Marktgroesse (SAM): {inputs['sam']:,.0f} | Ziel-Marktanteil: {inputs['cap_pct']}% | ARPU: {inputs['arpu']} EUR\n"
    input_text += f"Startkapital: {inputs['equity']:,.0f} EUR | Mindestliquiditaet: {inputs['min_cash']:,.0f} EUR\n"
    input_text += f"Lohnsteigerung: {inputs['wage_inc']}% | Inflation: {inputs['inflation']}%"
    pdf.multi_cell(0, 5, input_text)
    pdf.ln(10)

    # 3. GuV (Transponiert)
    guv_cols = ["Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    df_guv = df_results.set_index("Jahr")[guv_cols].T
    pdf.add_table(df_guv, "Gewinn- und Verlustrechnung (GuV)")

    # 4. Cashflow (Transponiert)
    pdf.add_page()
    cf_cols = ["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    df_cf = df_results.set_index("Jahr")[cf_cols].T
    pdf.add_table(df_cf, "Kapitalflussrechnung (Cashflow)")

    # 5. Bilanz (Transponiert)
    pdf.add_page()
    bilanz_cols = ["Anlagevermögen", "Kasse", "Forderungen", "Summe Aktiva", "Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]
    df_bil = df_results.set_index("Jahr")[bilanz_cols].T
    pdf.add_table(df_bil, "Bilanz")

    # 6. Grafiken
    pdf.add_page()
    pdf.chapter_title("Finanzielle Entwicklung")
    
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(df_results["Jahr"], df_results["Umsatz"], label="Umsatz", marker="o")
    ax1.bar(df_results["Jahr"], df_results["EBITDA"], label="EBITDA", alpha=0.5, color="green")
    ax1.set_title("Umsatz & EBITDA Entwicklung")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    pdf.add_plot(fig1)
    plt.close(fig1)
    
    pdf.ln(5)
    
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.fill_between(df_results["Jahr"], df_results["Kasse"], alpha=0.4, label="Kassenbestand")
    ax2.plot(df_results["Jahr"], df_results["Bankdarlehen"], color="red", label="Bankverbindlichkeiten", linewidth=2)
    ax2.set_title("Liquidität & Verschuldung")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    pdf.add_plot(fig2)
    plt.close(fig2)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- HEADER & GLOBAL BUTTONS ---
st.title("Integriertes Finanzmodell: Reporting Suite")

col_main_act1, col_main_act2 = st.columns([1, 3])
with col_main_act1:
    if st.button("🔄 MODELL JETZT NEU BERECHNEN", type="primary", use_container_width=True):
        st.rerun()
with col_main_act2:
    st.info("💡 Nach dem Anpassen der Werte klicken Sie bitte auf den Berechnen-Button, bevor Sie den Report erstellen.")

# --- SZENARIO MANAGER (IMPORT / EXPORT) ---
with st.expander("📂 Datei Speichern & Laden", expanded=True):
    col_io1, col_io2 = st.columns(2)
    
    # --- EXPORT ---
    with col_io1:
        st.markdown("##### 1. Aktuellen Stand sichern")
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        
        if "current_jobs_df" in st.session_state:
             df_export = st.session_state["current_jobs_df"].fillna(0).copy()
             for c in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
                 if c in df_export.columns: df_export[c] = df_export[c].apply(bool)
             config_data["jobs_data"] = df_export.to_dict(orient="records")
             
        st.download_button(
            label="💾 Als JSON herunterladen", 
            data=json.dumps(config_data, indent=2), 
            file_name="finanzmodell_config.json", 
            mime="application/json"
        )

    # --- IMPORT ---
    with col_io2:
        st.markdown("##### 2. Stand wiederherstellen")
        uploaded_file = st.file_uploader("JSON-Datei hier hereinziehen:", type=["json"])
        
        if uploaded_file is not None:
            c_imp = st.container()
            if c_imp.button("📥 Importieren & Anwenden", type="secondary"):
                try:
                    data = json.load(uploaded_file)
                    for key, val in data.items():
                        if key in DEFAULTS: 
                            st.session_state[key] = val
                    if "jobs_data" in data:
                        new_df = pd.DataFrame(data["jobs_data"])
                        st.session_state["current_jobs_df"] = new_df
                        if "job_editor_widget" in st.session_state:
                            del st.session_state["job_editor_widget"]
                    st.success("Erfolgreich geladen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

# --- TABS ---
tab_input, tab_res, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt & Finanzen", "👥 Jobs & Ressourcen", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# --- TAB 1: MARKT & BASIS-FINANZEN ---
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
        st.subheader("2. Finanzierung (Cash Sweep)")
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

# --- TAB 2: JOBS & RESSOURCEN ---
with tab_res:
    st.header("Personal & Assets")
    col_scale1, col_scale2 = st.columns([1, 2])
    with col_scale1:
        st.number_input("Ziel-Umsatz je FTE (€/Jahr)", step=5000.0, key="target_rev_per_fte", help="Steuert den Personalbedarf.")
    
    st.markdown("---")
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.subheader("Asset-Preise")
        st.number_input("Büro/Möbel (€)", key="price_desk")
        st.number_input("Laptop (€)", key="price_laptop")
        st.number_input("Handy (€)", key="price_phone")
        st.number_input("Auto (€)", key="price_car")
        st.number_input("LKW (€)", key="price_truck")
        st.markdown("---")
        st.number_input("Laufende Instandhaltung p.a.", key="capex_annual")
        st.number_input("Abschreibung (Jahre)", key="depreciation")
        
    with col_r2:
        st.subheader("Job Definitionen (15 Slots)")
        df_edit = st.session_state["current_jobs_df"].copy()
        for col in ["Jahresgehalt (€)", "FTE Jahr 1", "Sonstiges (€)"]:
            df_edit[col] = pd.to_numeric(df_edit[col], errors='coerce').fillna(0.0)
        
        edited_jobs = st.data_editor(
            df_edit,
            num_rows="fixed",
            use_container_width=True,
            key="job_editor_widget",
            column_config={
                "Job Titel": st.column_config.TextColumn("Job Titel", required=True),
                "Jahresgehalt (€)": st.column_config.NumberColumn("Jahresgehalt", min_value=0, format="%d €"),
                "FTE Jahr 1": st.column_config.NumberColumn("FTE Start", min_value=0.0, step=0.1, format="%.1f"),
                "Sonstiges (€)": st.column_config.NumberColumn("Setup sonst.", min_value=0, format="%d €"),
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

# 1. Jobs
jobs_config = edited_jobs.to_dict(orient="records")
valid_jobs = []
for job in jobs_config:
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
    for key in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
        job[key] = bool(job.get(key))
    
    setup = job["Sonstiges (€)"]
    if job.get("Laptop"): setup += st.session_state["price_laptop"]
    if job.get("Smartphone"): setup += st.session_state["price_phone"]
    if job.get("Auto"): setup += st.session_state["price_car"]
    if job.get("LKW"): setup += st.session_state["price_truck"]
    if job.get("Büro"): setup += st.session_state["price_desk"]
    job["_setup_cost_per_head"] = setup
    valid_jobs.append(job)

# 2. Konstanten
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
CHURN = st.session_state["churn"] / 100.0
N_start = 10.0 
revenue_y1 = N_start * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
revenue_per_fte_benchmark = st.session_state["target_rev_per_fte"]

# 3. Simulation
results = []
n_prev = N_start
prev_ftes_by_role = {j["Job Titel"]: j["FTE Jahr 1"] for j in valid_jobs}

cash = 0.0
fixed_assets = 0.0
equity = 0.0
debt = st.session_state["loan_initial"]
retained_earnings = 0.0
wage_factor = 1.0
debt_prev = st.session_state["loan_initial"]

for t in range(1, 11):
    row = {"Jahr": t}
    
    if t == 1: n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    net_rev = n_t * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
    row["Umsatz"] = net_rev
    
    target_total_fte = 0
    if st.session_state["target_rev_per_fte"] > 0:
        target_total_fte = net_rev / st.session_state["target_rev_per_fte"]
        
    if t > 1: wage_factor *= (1 + st.session_state["wage_inc"]/100) * (1 + st.session_state["inflation"]/100)
    
    daily_personnel_cost = 0
    daily_capex_assets = 0
    total_fte_this_year = 0
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
        total_fte_this_year += curr_fte
        if curr_fte > 0: row[f"FTE {role}"] = curr_fte
        else: row[f"FTE {role}"] = 0.0
        
        cost = job["Jahresgehalt (€)"] * curr_fte * wage_factor * (1 + st.session_state["lnk_pct"]/100)
        daily_personnel_cost += cost
        
        prev = prev_ftes_by_role.get(role, 0) if t > 1 else 0
        delta = max(0, curr_fte - prev)
        daily_capex_assets += delta * job["_setup_cost_per_head"]

    row["FTE Total"] = total_fte_this_year
    row["Personalkosten"] = daily_personnel_cost
    row["Investitionen (Assets)"] = daily_capex_assets
    
    cost_mkt = n_t * st.session_state["cac"]
    cost_cogs = net_rev * 0.10
    cost_cons = net_rev * 0.02
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_cons + st.session_state["capex_annual"]
    row["Gesamtkosten (OPEX)"] = total_opex
    ebitda = net_rev - total_opex
    
    capex_now = daily_capex_assets
    deprec = (fixed_assets + capex_now) / st.session_state["depreciation"]
    ebit = ebitda - deprec
    
    interest = debt_prev * (st.session_state["loan_rate"] / 100.0)
    ebt = ebit - interest
    tax = max(0, ebt * (st.session_state["tax_rate"] / 100.0))
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Jahresüberschuss"] = net_income
    
    ar_end = net_rev * (st.session_state["dso"]/365.0)
    ap_end = total_opex * (st.session_state["dpo"]/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    cf_op = net_income + deprec - (ar_end - ar_prev) + (ap_end - ap_prev)
    cf_inv = -capex_now
    
    cash_start = results[-1]["Kasse"] if t > 1 else 0.0
    equity_in = st.session_state["equity"] if t == 1 else 0.0
    cash_pre_fin = cash_start + cf_op + cf_inv + equity_in
    
    gap = st.session_state["min_cash"] - cash_pre_fin
    borrow_amount = gap if gap > 0 else 0
    repay_amount = min(debt_prev, abs(gap)) if gap < 0 else 0
        
    cf_fin = equity_in + borrow_amount - repay_amount
    delta_cash = cf_op + cf_inv + cf_fin
    
    cash = cash_start + delta_cash
    debt = debt_prev + borrow_amount - repay_amount
    
    fixed_assets = max(0, fixed_assets + capex_now - deprec)
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
    
    row["Zinsaufwand"] = interest
    row["Kreditaufnahme"] = borrow_amount
    row["Tilgung"] = repay_amount
    
    results.append(row)
    n_prev = n_t
    prev_ftes_by_role = current_ftes_by_role
    debt_prev = debt

df = pd.DataFrame(results)

# --- BUTTONS FÜR PDF DOWNLOAD ---
# PDF Erstellung
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
with tab_dash:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz J10", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA J10", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs J10", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse J10", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    st.line_chart(df.set_index("Jahr")[["Kasse", "Bankdarlehen"]])
    
    c1, c2 = st.columns(2)
    with c1: st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])
    with c2: 
        job_cols = [c for c in df.columns if c.startswith("FTE ") and c != "FTE Total"]
        active_job_cols = [c for c in job_cols if df[c].sum() > 0]
        st.bar_chart(df.set_index("Jahr")[active_job_cols], stack=True)

# Transponierte Tabellen
with tab_guv: 
    cols = ["Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_cf:
    cols = ["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    st.dataframe(df.set_index("Jahr")[cols].T.style.format("€ {:,.0f}"))

with tab_bilanz:
    st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Forderungen", "Eigenkapital", "Bankdarlehen", "Verb. LL"]].T.style.format("€ {:,.0f}"))
