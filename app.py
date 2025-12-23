import streamlit as st
import pandas as pd
import math
import json
import numpy as np

# --- KONFIGURATION ---
st.set_page_config(page_title="Finanzmodell Pro", layout="wide")
st.title("Integriertes Finanzmodell: Cash Sweep & Import/Export")

# --- 1. DEFINITION DER STANDARDS (ZENTRAL) ---
# Damit der Export immer funktioniert, definieren wir alle Inputs und ihre Startwerte hier.
DEFAULTS = {
    # Markt & Wachstum
    "sam": 39000.0,
    "cap_pct": 2.3,
    "p_pct": 2.5,
    "q_pct": 38.0,
    "churn": 10.0,
    "arpu": 3000.0,
    "discount": 0.0,
    # Finanzierung
    "equity": 100000.0,
    "loan_initial": 0.0,
    "min_cash": 100000.0,
    "loan_rate": 5.0,
    # Personal Global
    "wage_inc": 1.5,
    "inflation": 2.0,
    "lnk_pct": 25.0,
    "target_rev_per_fte": 150000.0,
    # Working Capital & Tax
    "dso": 30,
    "dpo": 30,
    "tax_rate": 30.0,
    "cac": 3590.0,
    # Assets
    "price_desk": 2500,
    "price_laptop": 2000,
    "price_phone": 800,
    "price_car": 40000,
    "price_truck": 60000,
    "capex_annual": 5000,
    "depreciation": 5
}

# --- 2. INITIALISIERUNG STATE ---
# Wir stellen sicher, dass ALLE Werte im Session State existieren, BEVOR wir exportieren.
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

# --- SZENARIO MANAGER ---
with st.expander("📂 Szenario Manager (Speichern & Laden)", expanded=False):
    col_io1, col_io2 = st.columns(2)
    with col_io1:
        st.markdown("### Export")
        # Wir holen die Daten direkt aus dem State, der oben garantiert befüllt wurde
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        
        # Job Tabelle hinzufügen
        if "current_jobs_df" in st.session_state:
             df_export = st.session_state["current_jobs_df"].fillna(0)
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
                for key, val in data.items():
                    if key in DEFAULTS: 
                        st.session_state[key] = val
                
                # 2. Job Tabelle wiederherstellen
                if "jobs_data" in data:
                    st.session_state["current_jobs_df"] = pd.DataFrame(data["jobs_data"])
                    # Cache des Editors löschen erzwingt Neuladen
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
        # WICHTIG: Wir nutzen keinen 'value=' Parameter mehr, da der State oben initialisiert wurde.
        # Streamlit nimmt automatisch den Wert aus st.session_state[key].
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
        st.markdown("Automatischer Ausgleich der Liquidität über Kreditlinie.")
        st.number_input("Eigenkapital Start (€)", step=5000.0, key="equity")
        st.number_input("Start-Schuldenstand (€)", step=5000.0, key="loan_initial", help="Bereits bestehende Kredite.")
        st.number_input("Mindest-Liquidität (Puffer) €", step=5000.0, key="min_cash", help="Ziel-Kontostand.")
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
    
    st.subheader("⚙️ Skalierung & Produktivität")
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
        
        # Typ-Sicherheit
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
    # Setup Kosten pro Kopf berechnen
    setup = safe_float(job.get("Sonstiges (€)"))
    if job.get("Laptop"): setup += st.session_state["price_laptop"]
    if job.get("Smartphone"): setup += st.session_state["price_phone"]
    if job.get("Auto"): setup += st.session_state["price_car"]
    if job.get("LKW"): setup += st.session_state["price_truck"]
    if job.get("Büro"): setup += st.session_state["price_desk"]
    job["_setup_cost_per_head"] = setup
    
    # Werte säubern
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    valid_jobs.append(job)

# 2. Konstanten aus State
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
CHURN = st.session_state["churn"] / 100.0
N_start = 10.0 
revenue_y1 = N_start * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)

# 3. Simulation
results = []
n_prev = N_start
prev_ftes_by_role = {j["Job Titel"]: j["FTE Jahr 1"] for j in valid_jobs}

# Startwerte
cash = 0.0 # Wird T1 berechnet
fixed_assets = 0.0
equity = 0.0
debt = st.session_state["loan_initial"]
retained_earnings = 0.0
wage_factor = 1.0
debt_prev = st.session_state["loan_initial"]

for t in range(1, 11):
    row = {"Jahr": t}
    
    # --- Markt ---
    if t == 1: n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    net_rev = n_t * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
    row["Umsatz"] = net_rev
    
    # --- Personal ---
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
        
        cost = job["Jahresgehalt (€)"] * curr_fte * wage_factor * (1 + st.session_state["lnk_pct"]/100)
        daily_personnel_cost += cost
        
        prev = prev_ftes_by_role.get(role, 0) if t > 1 else 0
        delta = max(0, curr_fte - prev)
        daily_capex_assets += delta * job["_setup_cost_per_head"]

    row["FTE Total"] = total_fte_this_year
    row["Personalkosten"] = daily_personnel_cost
    row["Investitionen (Assets)"] = daily_capex_assets
    
    # --- GuV ---
    cost_mkt = n_t * st.session_state["cac"]
    # Vereinfachte Annahmen für sonstige Kosten
    cost_cogs = net_rev * 0.10
    cost_cons = net_rev * 0.02
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_cons + st.session_state["capex_annual"]
    row["Gesamtkosten (OPEX)"] = total_opex
    ebitda = net_rev - total_opex
    
    capex_now = daily_capex_assets
    deprec = (fixed_assets + capex_now) / st.session_state["depreciation"]
    ebit = ebitda - deprec
    
    # Zinsen
    interest = debt_prev * (st.session_state["loan_rate"] / 100.0)
    ebt = ebit - interest
    tax = max(0, ebt * (st.session_state["tax_rate"] / 100.0))
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Jahresüberschuss"] = net_income
    
    # --- Cashflow & Finanzierung ---
    ar_end = net_rev * (st.session_state["dso"]/365.0)
    ap_end = total_opex * (st.session_state["dpo"]/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    cf_op = net_income + deprec - (ar_end - ar_prev) + (ap_end - ap_prev)
    cf_inv = -capex_now
    
    # Cash Sweep
    cash_start = results[-1]["Kasse"] if t > 1 else 0.0
    equity_in = st.session_state["equity"] if t == 1 else 0.0
    
    cash_pre_fin = cash_start + cf_op + cf_inv + equity_in
    
    # Lücke zum Mindestbestand
    gap = st.session_state["min_cash"] - cash_pre_fin
    
    borrow_amount = 0.0
    repay_amount = 0.0
    
    if gap > 0:
        borrow_amount = gap
    else:
        # Überschuss zum Tilgen nutzen
        surplus = abs(gap)
        repay_amount = min(debt_prev, surplus)
        
    cf_fin = equity_in + borrow_amount - repay_amount
    delta_cash = cf_op + cf_inv + cf_fin
    
    # Endbestände
    cash = cash_start + delta_cash
    debt = debt_prev + borrow_amount - repay_amount
    
    # --- Bilanz ---
    fixed_assets = max(0, fixed_assets + capex_now - deprec)
    if t==1:
        retained_earnings = net_income
        eq_curr = st.session_state["equity"] + retained_earnings
    else:
        retained_earnings += net_income
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

# --- DASHBOARD ---
with tab_dash:
    st.markdown("### KPIs Jahr 10")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    st.markdown("### Finanzierung (Cash Sweep)")
    st.caption("Das Modell regelt automatisch Kreditaufnahme/Tilgung, um die Mindestliquidität zu halten.")
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
    
    export_cols = [
        "Umsatz", "Gesamtkosten (OPEX)", "EBITDA", "EBIT", "Zinsaufwand", "Jahresüberschuss",
        "Kasse", "Bankdarlehen", "Kreditaufnahme", "Tilgung", "Eigenkapital", "Bilanz Check"
    ]
    csv = df.set_index("Jahr")[export_cols].T.to_csv(sep=";", decimal=",").encode('utf-8')
    st.download_button("📊 Report herunterladen (Jahre horizontal)", csv, "report_horizontal.csv", "text/csv")

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
