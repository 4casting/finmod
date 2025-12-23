import streamlit as st
import pandas as pd
import math
import json
import numpy as np

# --- KONFIGURATION ---
st.set_page_config(page_title="Finanzmodell Pro: Custom Jobs", layout="wide")
st.title("Integriertes Finanzmodell: Custom Jobs & Ressourcen")

# --- INITIALISIERUNG (STATE) ---
if "current_jobs_df" not in st.session_state:
    # Standard-Datenstruktur
    default_data = [
        {"Job Titel": "Geschäftsführer", "Jahresgehalt (€)": 120000, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0},
        {"Job Titel": "Vertriebsleiter", "Jahresgehalt (€)": 80000, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0},
        {"Job Titel": "Sales Manager", "Jahresgehalt (€)": 50000, "FTE Jahr 1": 3.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500},
        {"Job Titel": "Marketing", "Jahresgehalt (€)": 45000, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 2000},
        {"Job Titel": "Techniker", "Jahresgehalt (€)": 40000, "FTE Jahr 1": 2.0, "Laptop": False, "Smartphone": True, "Auto": False, "LKW": True, "Büro": False, "Sonstiges (€)": 1000},
        {"Job Titel": "Buchhaltung", "Jahresgehalt (€)": 42000, "FTE Jahr 1": 0.5, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 0},
    ]
    st.session_state["current_jobs_df"] = pd.DataFrame(default_data)

# --- HILFSFUNKTIONEN ---

def safe_float(value, default=0.0):
    """Konvertiert Input sicher in Float, fängt None/NaN ab."""
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        if pd.isna(value): # Fängt numpy.nan ab
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def calculate_loan_schedule(principal, rate, years):
    """Berechnet einen Tilgungsplan für ein Annuitätendarlehen."""
    principal = safe_float(principal)
    rate = safe_float(rate)
    years = safe_float(years)
    
    if principal <= 0 or years <= 0:
        return pd.DataFrame()
    
    if rate > 0:
        annuity = principal * (rate * (1 + rate)**years) / ((1 + rate)**years - 1)
    else:
        annuity = principal / years
        
    schedule = []
    remaining_balance = principal
    
    for t in range(1, int(years) + 1):
        interest = remaining_balance * rate
        repayment = annuity - interest
        if t == years:
            repayment = remaining_balance
            annuity = repayment + interest
        remaining_balance -= repayment
        
        schedule.append({
            "Jahr_Index": t,
            "Zinsen": interest,
            "Tilgung": repayment,
            "Restschuld": max(0, remaining_balance)
        })
    return pd.DataFrame(schedule)

# --- SZENARIO MANAGER ---
simple_input_keys = [
    "sam", "cap_pct", "p_pct", "q_pct", "churn",
    "arpu", "discount",
    "wage_inc", "inflation", "lnk_pct", "cac",
    "equity", "loan", "loan_rate", "loan_years",
    "capex_annual", "depreciation",
    "dso", "dpo", "tax_rate",
    "price_laptop", "price_phone", "price_car", "price_truck", "price_desk"
]

with st.expander("📂 Szenario Manager (Speichern & Laden)", expanded=False):
    col_io1, col_io2 = st.columns(2)
    
    with col_io1:
        st.markdown("### Inputs exportieren")
        config_data = {key: st.session_state.get(key) for key in simple_input_keys if key in st.session_state}
        
        if "current_jobs_df" in st.session_state:
             # DataFrame sicher in Liste von Dicts umwandeln
             df_export = st.session_state["current_jobs_df"].replace({np.nan: None})
             config_data["jobs_data"] = df_export.to_dict(orient="records")

        json_string = json.dumps(config_data, indent=2)
        
        st.download_button(
            label="💾 Konfiguration herunterladen (JSON)",
            data=json_string,
            file_name="finanzmodell_custom_config.json",
            mime="application/json"
        )

    with col_io2:
        st.markdown("### Inputs importieren")
        uploaded_file = st.file_uploader("Konfigurationsdatei hochladen", type=["json"])
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                for key, value in data.items():
                    if key in simple_input_keys:
                        st.session_state[key] = value
                
                if "jobs_data" in data:
                    st.session_state["current_jobs_df"] = pd.DataFrame(data["jobs_data"])
                
                st.success("Erfolgreich geladen! Bitte warten...")
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
        SAM = st.number_input("SAM (Markt)", value=39000.0, step=1000.0, key="sam")
        CAP_percent = st.number_input("Marktanteil Ziel %", value=2.3, step=0.1, key="cap_pct")
        SOM = SAM * (CAP_percent / 100.0)
        st.info(f"SOM: {int(SOM)} Kunden")
        p_percent = st.number_input("Innovatoren (p) %", value=2.5, step=0.1, key="p_pct")
        q_percent = st.number_input("Imitatoren (q) %", value=38.0, step=1.0, key="q_pct")
        churn_percent = st.number_input("Churn Rate %", value=10.0, step=1.0, key="churn")
        
        st.subheader("Umsatz")
        ARPU = st.number_input("ARPU (€/Jahr)", value=3000.0, step=100.0, key="arpu")
        discount_total = st.slider("Rabatte %", 0.0, 20.0, 0.0, key="discount")

    with col2:
        st.subheader("2. Finanzierung & Globales")
        equity_initial = st.number_input("Eigenkapital (€)", value=100000.0, step=5000.0, key="equity")
        loan_amount = st.number_input("Kredit (€)", value=100000.0, step=5000.0, key="loan")
        loan_rate = st.number_input("Zins %", value=5.0, step=0.1, key="loan_rate") / 100.0
        loan_years = st.number_input("Laufzeit (Jahre)", value=10, step=1, key="loan_years")
        
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
    st.header("Personalplanung & Ressourcenbedarf")
    
    col_r1, col_r2 = st.columns([1, 2])
    
    with col_r1:
        st.subheader("Kosten der Assets (Anschaffung)")
        st.caption("Einmalige Kosten pro neuem Mitarbeiter (CAPEX)")
        p_desk = st.number_input("Arbeitsplatz/Möbel (€)", value=2500, key="price_desk")
        p_laptop = st.number_input("Laptop/IT (€)", value=2000, key="price_laptop")
        p_phone = st.number_input("Smartphone (€)", value=800, key="price_phone")
        p_car = st.number_input("Dienstwagen (€)", value=40000, key="price_car")
        p_truck = st.number_input("LKW/Transporter (€)", value=60000, key="price_truck")
        
        st.markdown("---")
        st.subheader("Laufende Kosten")
        capex_annual = st.number_input("Laufende Instandhaltung p.a. (€)", value=5000, key="capex_annual")
        depreciation_period = st.number_input("Abschreibungsdauer (Jahre)", value=5, key="depreciation")
        
    with col_r2:
        st.subheader("Definition der Jobs (Jahr 1)")
        st.markdown("Definieren Sie hier Ihre Rollen. Das Modell skaliert die Anzahl in Zukunft basierend auf dem Umsatzwachstum.")
        
        df_for_editor = st.session_state["current_jobs_df"]
        
        edited_jobs = st.data_editor(
            df_for_editor,
            num_rows="dynamic",
            key="job_editor_widget",
            column_config={
                "Job Titel": st.column_config.TextColumn("Rolle / Titel", required=True),
                "Jahresgehalt (€)": st.column_config.NumberColumn("Jahresgehalt (Brutto)", min_value=0, format="%d €"),
                "FTE Jahr 1": st.column_config.NumberColumn("FTEs (Start)", min_value=0.0, step=0.1, format="%.1f"),
                "Sonstiges (€)": st.column_config.NumberColumn("Sonstiges (Setup)", min_value=0, format="%d €"),
            },
            hide_index=True
        )
        st.session_state["current_jobs_df"] = edited_jobs

# --- BERECHNUNGS-LOGIK ---

jobs_config = edited_jobs.to_dict(orient="records")

# Safety-Check: Leere Zeilen rausfiltern & Werte säubern
valid_jobs = []
for job in jobs_config:
    # Mindestens ein Job Titel muss da sein, sonst ignorieren
    if job.get("Job Titel") and str(job.get("Job Titel")).strip() != "":
        # Bereinigte Werte speichern
        job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
        job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
        job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
        valid_jobs.append(job)

# Initialkosten pro Rolle berechnen
for job in valid_jobs:
    setup_cost = job["Sonstiges (€)"]
    if job.get("Laptop", False): setup_cost += p_laptop
    if job.get("Smartphone", False): setup_cost += p_phone
    if job.get("Auto", False): setup_cost += p_car
    if job.get("LKW", False): setup_cost += p_truck
    if job.get("Büro", False): setup_cost += p_desk
    job["_setup_cost_per_head"] = setup_cost

# Basis-Metriken Jahr 1
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)

# Umsatz Jahr 1
P_bass = st.session_state.get("p_pct", 2.5) / 100.0
Q_bass = st.session_state.get("q_pct", 38.0) / 100.0
CHURN = st.session_state.get("churn", 10.0) / 100.0
N_start = 10.0 
revenue_y1 = N_start * ARPU * (1 - discount_total/100)

if total_fte_y1 > 0:
    revenue_per_fte_benchmark = revenue_y1 / total_fte_y1
else:
    revenue_per_fte_benchmark = 0

# Kredit
loan_df = calculate_loan_schedule(loan_amount, loan_rate, int(loan_years))
loan_map = loan_df.set_index("Jahr_Index").to_dict("index") if not loan_df.empty else {}

# --- SIMULATION ---
results = []
n_prev = N_start
prev_ftes_by_role = {j["Job Titel"]: j["FTE Jahr 1"] for j in valid_jobs}

cash = 0.0
fixed_assets = 0.0
equity = 0.0
debt = 0.0
retained_earnings = 0.0
wage_factor = 1.0

for t in range(1, 11):
    row = {"Jahr": t}
    
    # 1. Kunden & Umsatz
    if t == 1:
        n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P_bass + Q_bass * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    
    row["Kunden"] = n_t
    net_rev = n_t * ARPU * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 2. Personalbedarf
    if revenue_per_fte_benchmark > 0:
        target_total_fte = net_rev / revenue_per_fte_benchmark
    else:
        target_total_fte = 0
    
    # 3. Iteration über Jobs
    daily_personnel_cost = 0
    daily_capex_assets = 0
    total_fte_this_year = 0
    
    if t > 1: wage_factor *= (1 + wage_inc) * (1 + inflation)
    
    current_ftes_by_role = {}
    
    for job in valid_jobs:
        role_name = job["Job Titel"]
        base_fte = job["FTE Jahr 1"]
        base_salary = job["Jahresgehalt (€)"]
        
        if t == 1:
            curr_fte = base_fte
        else:
            share = base_fte / total_fte_y1 if total_fte_y1 > 0 else 0
            req_fte = target_total_fte * share
            curr_fte = max(req_fte, prev_ftes_by_role.get(role_name, 0))
        
        current_ftes_by_role[role_name] = curr_fte
        total_fte_this_year += curr_fte
        row[f"FTE {role_name}"] = curr_fte
        
        # HIER WAR DER FEHLER: Wir nutzen jetzt die bereinigten Werte (safe_float)
        salaries = base_salary * curr_fte * wage_factor * (1 + lnk_pct)
        daily_personnel_cost += salaries
        
        prev_fte = prev_ftes_by_role.get(role_name, 0) if t > 1 else 0
        delta_fte = max(0, curr_fte - prev_fte)
        
        new_assets_cost = delta_fte * job["_setup_cost_per_head"]
        daily_capex_assets += new_assets_cost

    row["FTE Total"] = total_fte_this_year
    row["Personalkosten"] = daily_personnel_cost
    row["Investitionen (Assets)"] = daily_capex_assets
    
    # 4. Andere Kosten
    cost_mkt = n_t * marketing_cac
    cost_cogs = net_rev * 0.10
    cost_consulting = net_rev * 0.02
    
    total_opex = daily_personnel_cost + cost_mkt + cost_cogs + cost_consulting + capex_annual
    row["Gesamtkosten (OPEX)"] = total_opex
    
    ebitda = net_rev - total_opex
    
    # 5. Abschreibungen & Finanzen
    capex_now = daily_capex_assets
    depreciation = (fixed_assets + capex_now) / depreciation_period
    
    ebit = ebitda - depreciation
    
    loan_data = loan_map.get(t, {"Zinsen": 0, "Tilgung": 0, "Restschuld": 0})
    interest = loan_data["Zinsen"]
    
    ebt = ebit - interest
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Jahresüberschuss"] = net_income
    row["Abschreibungen"] = depreciation
    
    # 6. Cashflow
    ar_end = net_rev * (dso/365.0)
    ap_end = total_opex * (dpo/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    delta_ar = ar_end - ar_prev
    delta_ap = ap_end - ap_prev
    
    cf_op = net_income + depreciation - delta_ar + delta_ap
    cf_inv = -capex_now
    
    inflow_equity = equity_initial if t == 1 else 0
    inflow_loan = loan_amount if t == 1 else 0
    outflow_repay = loan_data["Tilgung"]
    cf_fin = inflow_equity + inflow_loan - outflow_repay
    
    delta_cash = cf_op + cf_inv + cf_fin
    
    # 7. Bilanz Update
    fixed_assets = fixed_assets + capex_now - depreciation
    fixed_assets = max(0, fixed_assets)
    
    if t == 1:
        cash = delta_cash
        retained_earnings = net_income
        equity_curr = equity_initial + retained_earnings
    else:
        cash = results[-1]["Kasse"] + delta_cash
        retained_earnings += net_income
        equity_curr = equity_initial + retained_earnings
        
    row["Kasse"] = cash
    row["Anlagevermögen"] = fixed_assets
    row["Forderungen"] = ar_end
    row["Summe Aktiva"] = cash + fixed_assets + ar_end
    
    row["Verb. LL"] = ap_end
    row["Bankdarlehen"] = loan_data["Restschuld"]
    row["Eigenkapital"] = equity_curr
    row["Summe Passiva"] = equity_curr + loan_data["Restschuld"] + ap_end
    
    row["Bilanz Check"] = row["Summe Aktiva"] - row["Summe Passiva"]
    
    results.append(row)
    
    n_prev = n_t
    prev_ftes_by_role = current_ftes_by_role

df = pd.DataFrame(results)

# --- OUTPUT DASHBOARD ---
with tab_dash:
    st.markdown("### Management Summary (Jahr 10)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("Mitarbeiter (Total)", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse", f"€ {df['Kasse'].iloc[-1]:,.0f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Umsatz vs. Personalkosten")
        st.line_chart(df.set_index("Jahr")[["Umsatz", "Personalkosten", "EBITDA"]])
    with c2:
        st.subheader("Entwicklung der Job-Rollen")
        job_cols = [c for c in df.columns if c.startswith("FTE ") and c != "FTE Total"]
        st.bar_chart(df.set_index("Jahr")[job_cols], stack=True)
        
    st.markdown("### Export")
    csv = df.to_csv(sep=";", decimal=",").encode('utf-8')
    st.download_button("📊 Report herunterladen (CSV)", csv, "finanzplan_custom.csv", "text/csv")

# --- TABELLEN ---
with tab_guv:
    st.dataframe(df.set_index("Jahr")[["Umsatz", "Personalkosten", "Gesamtkosten (OPEX)", "EBITDA", "Jahresüberschuss"]].style.format("€ {:,.0f}"))

with tab_cf:
    st.dataframe(df.set_index("Jahr")[["Jahresüberschuss", "Investitionen (Assets)", "Kasse"]].style.format("€ {:,.0f}"))
    
with tab_bilanz:
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown("**Aktiva**")
        st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Forderungen"]].style.format("€ {:,.0f}"))
    with col_b2:
        st.markdown("**Passiva**")
        st.dataframe(df.set_index("Jahr")[["Eigenkapital", "Bankdarlehen", "Verb. LL"]].style.format("€ {:,.0f}"))
    
    check = df["Bilanz Check"].abs().max()
    if check > 1.0:
        st.error(f"Bilanz-Differenz: {check:.2f} €")
    else:
        st.success("Bilanz ist ausgeglichen.")
