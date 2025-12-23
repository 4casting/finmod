import streamlit as st
import pandas as pd
import math
import json
import numpy as np

# --- KONFIGURATION ---
st.set_page_config(page_title="Finanzmodell Pro", layout="wide")
st.title("Integriertes Finanzmodell: Cash Sweep & Import/Export")

# --- INITIALISIERUNG (STATE) ---
if "current_jobs_df" not in st.session_state:
    # 1. Standard-Rollen
    defined_roles = [
        {"Job Titel": "Geschäftsführer", "Jahresgehalt (€)": 120000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Vertriebsleiter", "Jahresgehalt (€)": 80000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
        {"Job Titel": "Sales Manager", "Jahresgehalt (€)": 50000.0, "FTE Jahr 1": 3.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500.0},
        {"Job Titel": "Marketing", "Jahresgehalt (€)": 45000.0, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 2000.0},
        {"Job Titel": "Techniker", "Jahresgehalt (€)": 40000.0, "FTE Jahr 1": 2.0, "Laptop": False, "Smartphone": True, "Auto": False, "LKW": True, "Büro": False, "Sonstiges (€)": 1000.0},
        {"Job Titel": "Buchhaltung", "Jahresgehalt (€)": 42000.0, "FTE Jahr 1": 0.5, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 0.0},
    ]
    
    # 2. Auffüllen auf 15 Slots
    total_slots = 15
    current_count = len(defined_roles)
    for i in range(current_count + 1, total_slots + 1):
        defined_roles.append({
            "Job Titel": f"Position {i} (Platzhalter)", 
            "Jahresgehalt (€)": 0.0, 
            "FTE Jahr 1": 0.0, 
            "Laptop": False, 
            "Smartphone": False, 
            "Auto": False, 
            "LKW": False, 
            "Büro": False, 
            "Sonstiges (€)": 0.0
        })
        
    st.session_state["current_jobs_df"] = pd.DataFrame(defined_roles)

# --- HILFSFUNKTIONEN ---
def safe_float(value, default=0.0):
    """Konvertiert Input sicher in Float."""
    try:
        if value is None: return default
        if isinstance(value, str) and not value.strip(): return default
        if pd.isna(value): return default
        return float(value)
    except (ValueError, TypeError):
        return default

# --- SZENARIO MANAGER (Alle Inputs müssen hier gelistet sein!) ---
input_keys = [
    # Markt
    "sam", "cap_pct", "p_pct", "q_pct", "churn", "arpu", "discount",
    # Finanzierung
    "equity", "loan_initial", "min_cash", "loan_rate",
    # Personal Global
    "wage_inc", "inflation", "lnk_pct", "target_rev_per_fte",
    # Working Capital & Tax
    "dso", "dpo", "tax_rate", "cac",
    # Assets
    "price_laptop", "price_phone", "price_car", "price_truck", "price_desk",
    "capex_annual", "depreciation"
]

with st.expander("📂 Szenario Manager (Speichern & Laden)", expanded=False):
    col_io1, col_io2 = st.columns(2)
    with col_io1:
        st.markdown("### Export")
        # Alle Keys abfragen
        config_data = {key: st.session_state.get(key) for key in input_keys if key in st.session_state}
        
        # Job Tabelle hinzufügen
        if "current_jobs_df" in st.session_state:
             # NaN durch 0 ersetzen für valides JSON
             df_export = st.session_state["current_jobs_df"].fillna(0)
             # DateTime/Bool Objekte sicherstellen
             config_data["jobs_data"] = df_export.to_dict(orient="records")
             
        st.download_button(
            label="💾 Konfiguration speichern (JSON)", 
            data=json.dumps(config_data, indent=2), 
            file_name="finanzmodell_config.json", 
            mime="application/json"
        )

    with col_io2:
        st.markdown("### Import")
        uploaded_file = st.file_uploader("Konfigurationsdatei laden", type=["json"])
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                
                # 1. Simple Keys wiederherstellen
                for key, value in data.items():
                    if key in input_keys: 
                        st.session_state[key] = value
                
                # 2. Job Tabelle wiederherstellen
                if "jobs_data" in data:
                    st.session_state["current_jobs_df"] = pd.DataFrame(data["jobs_data"])
                    # WICHTIG: Cache des Editors löschen, damit er die neuen Daten anzeigt!
                    if "job_editor_widget" in st.session_state:
                        del st.session_state["job_editor_widget"]
                
                st.success("Daten erfolgreich geladen!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Import: {e}")

# --- TABS ---
tab_input, tab_res, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt & Finanzen", "👥 Jobs & Ressourcen", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# --- TAB 1: MARKT & BASIS-FINANZEN ---
with tab_input:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Markt & Wachstum")
        SAM = st.number_input("SAM (Marktpotenzial)", value=39000.0, step=1000.0, key="sam")
        CAP_percent = st.number_input("Marktanteil Ziel %", value=2.3, step=0.1, key="cap_pct")
        SOM = SAM * (CAP_percent / 100.0)
        st.info(f"SOM: {int(SOM)} Kunden")
        p_percent = st.number_input("Innovatoren (p) %", value=2.5, step=0.1, key="p_pct")
        q_percent = st.number_input("Imitatoren (q) %", value=38.0, step=1.0, key="q_pct")
        churn_percent = st.number_input("Churn Rate %", value=10.0, step=1.0, key="churn")
        st.subheader("Umsatz")
        ARPU = st.number_input("ARPU (€)", value=3000.0, step=100.0, key="arpu")
        discount_total = st.slider("Rabatte %", 0.0, 20.0, 0.0, key="discount")

    with col2:
        st.subheader("2. Finanzierung (Cash Sweep)")
        st.markdown("Automatischer Ausgleich der Liquidität über Kreditlinie.")
        equity_initial = st.number_input("Eigenkapital Start (€)", value=100000.0, step=5000.0, key="equity")
        loan_initial = st.number_input("Start-Schuldenstand (€)", value=0.0, step=5000.0, key="loan_initial", help="Bereits bestehende Kredite.")
        min_cash = st.number_input("Mindest-Liquidität (Puffer) €", value=100000.0, step=5000.0, key="min_cash", help="Ziel-Kontostand.")
        loan_rate = st.number_input("Soll-Zins Kredit %", value=5.0, step=0.1, key="loan_rate") / 100.0
        
        st.markdown("---")
        wage_inc = st.number_input("Lohnsteigerung %", value=1.5, step=0.1, key="wage_inc") / 100.0
        inflation = st.number_input("Inflation %", value=2.0, step=0.1, key="inflation") / 100.0
        lnk_pct = st.number_input("Lohnnebenkosten %", value=25.0, step=1.0, key="lnk_pct") / 100.0
        st.markdown("---")
        dso = st.number_input("DSO (Tage)", value=30, key="dso")
        dpo = st.number_input("DPO (Tage)", value=30, key="dpo")
        tax_rate = st.number_input("Steuersatz %", value=30.0, key="tax_rate") / 100.0
        marketing_cac = st.number_input("Marketing CAC (€)", value=3590.0, key="cac")

# --- TAB 2: JOBS & RESSOURCEN ---
with tab_res:
    st.header("Personal & Assets")
    
    st.subheader("⚙️ Skalierung & Produktivität")
    col_scale1, col_scale2 = st.columns([1, 2])
    with col_scale1:
        target_rev_per_fte = st.number_input(
            "Ziel-Umsatz je FTE (€/Jahr)", 
            value=150000.0, 
            step=5000.0, 
            key="target_rev_per_fte",
            help="Steuert den Personalbedarf."
        )
    
    st.markdown("---")
    col_r1, col_r2 = st.columns([1, 2])
    
    with col_r1:
        st.subheader("Asset-Preise")
        p_desk = st.number_input("Büro/Möbel (€)", value=2500, key="price_desk")
        p_laptop = st.number_input("Laptop (€)", value=2000, key="price_laptop")
        p_phone = st.number_input("Handy (€)", value=800, key="price_phone")
        p_car = st.number_input("Auto (€)", value=40000, key="price_car")
        p_truck = st.number_input("LKW (€)", value=60000, key="price_truck")
        st.markdown("---")
        capex_annual = st.number_input("Laufende Instandhaltung p.a.", value=5000, key="capex_annual")
        depreciation_period = st.number_input("Abschreibung (Jahre)", value=5, key="depreciation")
        
    with col_r2:
        st.subheader("Job Definitionen (15 Slots)")
        
        df_edit = st.session_state["current_jobs_df"].copy()
        
        # Typ-Sicherheit für den Editor
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

# 1. Jobs parsen
jobs_config = edited_jobs.to_dict(orient="records")
valid_jobs = []
for job in jobs_config:
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
    
    # Checkboxen zu Bool
    for key in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
        job[key] = bool(job.get(key))
    
    # Setup Kosten pro Kopf berechnen
    setup = job["Sonstiges (€)"]
    if job["Laptop"]: setup += p_laptop
    if job["Smartphone"]: setup += p_phone
    if job["Auto"]: setup += p_car
    if job["LKW"]: setup += p_truck
    if job["Büro"]: setup += p_desk
    job["_setup_cost_per_head"] = setup
    
    valid_jobs.append(job)

# 2. Konstanten
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P_bass = st.session_state.get("p_pct", 2.5) / 100.0
Q_bass = st.session_state.get("q_pct", 38.0) / 100.0
CHURN = st.session_state.get("churn", 10.0) / 100.0
N_start = 10.0 
revenue_y1 = N_start * ARPU * (1 - discount_total/100)

revenue_per_fte_benchmark = target_rev_per_fte

# 3. Simulation
results = []
n_prev = N_start
prev_ftes_by_role = {j["Job Titel"]: j["FTE Jahr 1"] for j in valid_jobs}

# Startwerte vor T1
cash = 0.0 # Wird in T1 berechnet
fixed_assets = 0.0
equity = 0.0
debt = loan_initial
retained_earnings = 0.0
wage_factor = 1.0
debt_prev = loan_initial

for t in range(1, 11):
    row = {"Jahr": t}
    
    # --- A. Markt ---
    if t == 1: n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P_bass + Q_bass * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    net_rev = n_t * ARPU * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # --- B. Personal ---
    if revenue_per_fte_benchmark > 0:
        target_total_fte = net_rev / revenue_per_fte_benchmark
    else:
        target_total_fte = 0
        
    if t > 1: wage_factor *= (1 + wage_inc) * (1 + inflation)
    
    daily_personnel_cost = 0
    daily_capex_assets = 0
    total_fte_this_year = 0
    current_ftes_by_role = {}
    
    for job in valid_jobs:
        role = job["Job Titel"]
        base_fte = job["FTE Jahr 1"]
        
        if t == 1:
            curr_fte = base_fte
        else:
            if base_fte > 0 and total_fte_y1 > 0:
                share = base_fte / total_fte_y1
                req = target_total_fte * share
                curr_fte = max(req, prev_ftes_by_role.get(role, 0))
            else:
                curr_fte = 0.0
            
        current_ftes_by_role[role] = curr_fte
        total_fte_this_year += curr_fte
        
        if curr_fte > 0: row[f"FTE {role}"] = curr_fte
        else: row[f"FTE {role}"] = 0.0
        
        cost = job["Jahresgehalt (€)"] * curr_fte * wage_factor * (1 + lnk_pct)
        daily_personnel_cost += cost
        
        prev = prev_ftes_by_role.get(role, 0) if t > 1 else 0
        delta = max(0, curr_fte - prev)
        daily_capex_assets += delta * job["_setup_cost_per_head"]

    row["FTE Total"] = total_fte_this_year
    row["Personalkosten"] = daily_personnel_cost
    row["Investitionen (Assets)"] = daily_capex_assets
    
    # --- C. GuV ---
    cost_mkt = n_t * marketing_cac
    cost_cogs = net_rev * 0.10
    cost_cons = net_rev * 0.02
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_cons + capex_annual
    row["Gesamtkosten (OPEX)"] = total_opex
    ebitda = net_rev - total_opex
    
    capex_now = daily_capex_assets
    deprec = (fixed_assets + capex_now) / depreciation_period
    ebit = ebitda - deprec
    
    # Zinsen auf Basis Vorjahresschulden
    interest = debt_prev * loan_rate
    
    ebt = ebit - interest
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Jahresüberschuss"] = net_income
    
    # --- D. Cashflow & Finanzierung ---
    ar_end = net_rev * (dso/365.0)
    ap_end = total_opex * (dpo/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    cf_op = net_income + deprec - (ar_end - ar_prev) + (ap_end - ap_prev)
    cf_inv = -capex_now
    
    # Cash Sweep Berechnung
    # Verfügbares Geld VOR Kreditmaßnahmen
    cash_start = results[-1]["Kasse"] if t > 1 else 0.0
    equity_in = equity_initial if t == 1 else 0.0
    
    cash_pre_fin = cash_start + cf_op + cf_inv + equity_in
    
    # Differenz zum Zielbestand
    gap = min_cash - cash_pre_fin
    
    borrow_amount = 0.0
    repay_amount = 0.0
    
    if gap > 0:
        # Zu wenig Geld -> Kredit aufnehmen
        borrow_amount = gap
    else:
        # Zu viel Geld -> Kredit tilgen (sofern Schulden da sind)
        surplus = abs(gap)
        repay_amount = min(debt_prev, surplus)
        
    cf_fin = equity_in + borrow_amount - repay_amount
    delta_cash = cf_op + cf_inv + cf_fin
    
    # Endbestände
    cash = cash_start + delta_cash
    debt = debt_prev + borrow_amount - repay_amount
    
    # --- E. Bilanz ---
    fixed_assets = max(0, fixed_assets + capex_now - deprec)
    if t==1:
        retained_earnings = net_income
        eq_curr = equity_initial + retained_earnings
    else:
        retained_earnings += net_income
        eq_curr = equity_initial + retained_earnings
        
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

# --- DASHBOARD ---
with tab_dash:
    st.markdown("### KPIs Jahr 10")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    st.markdown("### Finanzierungsverlauf (Cash Sweep)")
    st.caption("Das Modell hält die Kasse automatisch auf dem Mindest-Level (Linie) und nimmt dafür Kredite auf oder tilgt sie.")
    st.line_chart(df.set_index("Jahr")[["Kasse", "Bankdarlehen"]])
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Umsatz & Kosten")
        st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])
    with c2:
        st.subheader("Job-Entwicklung")
        job_cols = [c for c in df.columns if c.startswith("FTE ") and c != "FTE Total"]
        active_job_cols = [c for c in job_cols if df[c].sum() > 0]
        st.bar_chart(df.set_index("Jahr")[active_job_cols], stack=True)
    
    st.markdown("### Report Export")
    # Transponieren für PDF-ähnliches Format
    export_cols = [
        "Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "EBIT", "Zinsaufwand", "Jahresüberschuss",
        "Kasse", "Bankdarlehen", "Kreditaufnahme", "Tilgung", "Eigenkapital", "Bilanz Check"
    ]
    df_export = df.set_index("Jahr")[export_cols].T
    csv = df_export.to_csv(sep=";", decimal=",").encode('utf-8')
    st.download_button("📊 Report herunterladen (CSV, Jahre horizontal)", csv, "report_horizontal.csv", "text/csv")

# --- TABELLEN ---
with tab_guv: st.dataframe(df.set_index("Jahr")[["Umsatz", "Personalkosten", "Zinsaufwand", "EBITDA", "Jahresüberschuss"]].style.format("€ {:,.0f}"))
with tab_cf: st.dataframe(df.set_index("Jahr")[["Jahresüberschuss", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Kasse"]].style.format("€ {:,.0f}"))
with tab_bilanz:
    c1, c2 = st.columns(2)
    with c1: st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Forderungen"]].style.format("€ {:,.0f}"))
    with c2: st.dataframe(df.set_index("Jahr")[["Eigenkapital", "Bankdarlehen", "Verb. LL"]].style.format("€ {:,.0f}"))
    check = df["Bilanz Check"].abs().max()
    if check > 1: st.error(f"Bilanz Diff: {check:.2f}")
    else: st.success("Bilanz OK")
