import streamlit as st
import pandas as pd
import math
import json
import numpy as np

# --- KONFIGURATION ---
st.set_page_config(page_title="Finanzmodell Pro", layout="wide")

# --- 1. DEFINITION DER STANDARDS (ZENTRAL) ---
# WICHTIG: Alle Variablen hier werden gespeichert/geladen!
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
    # Assets NUTZUNGSDAUER (Jahre) - NEU HINZUGEFÜGT
    "ul_desk": 13, "ul_laptop": 3, "ul_phone": 2, "ul_car": 6, "ul_truck": 8,
    # Sonstiges Capex
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

# --- HEADER & GLOBAL BUTTONS ---
st.title("Integriertes Finanzmodell: Asset Management & Abschreibungen")

col_main_act1, col_main_act2 = st.columns([1, 3])
with col_main_act1:
    if st.button("🔄 MODELL JETZT NEU BERECHNEN", type="primary", use_container_width=True):
        st.rerun()
with col_main_act2:
    st.info("💡 Definieren Sie Abschreibungsdauern im Tab 'Abschreibungen'. Abgelaufene Geräte werden automatisch neu gekauft.")

# --- SZENARIO MANAGER ---
with st.expander("📂 Datei Speichern & Laden (Import/Export)", expanded=False):
    col_io1, col_io2 = st.columns(2)
    with col_io1:
        st.markdown("##### 1. Aktuellen Stand sichern")
        # Hier werden jetzt ALLE Werte aus DEFAULTS gezogen, inkl. Nutzungsdauern
        config_data = {key: st.session_state[key] for key in DEFAULTS.keys()}
        if "current_jobs_df" in st.session_state:
             df_export = st.session_state["current_jobs_df"].fillna(0).copy()
             for c in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
                 if c in df_export.columns: df_export[c] = df_export[c].apply(bool)
             config_data["jobs_data"] = df_export.to_dict(orient="records")
        st.download_button("💾 Als JSON herunterladen", json.dumps(config_data, indent=2), "finanzmodell_config.json", "application/json")

    with col_io2:
        st.markdown("##### 2. Stand wiederherstellen")
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
    "📝 Markt & Finanzen", "📉 Abschreibungen & Assets", "👥 Jobs & Personal", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
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

# --- TAB 2: ABSCHREIBUNGEN & ASSETS ---
with tab_assets:
    st.header("Asset Management & AfA")
    st.markdown("Hier definieren Sie Preise und **Nutzungsdauer (Jahre)**. Abgelaufene Assets werden automatisch ersetzt.")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        st.subheader("IT & Kommunikation")
        st.number_input("Laptop Preis (€)", key="price_laptop")
        st.number_input("Laptop Dauer (Jahre)", key="ul_laptop", min_value=1)
        st.markdown("---")
        st.number_input("Smartphone Preis (€)", key="price_phone")
        st.number_input("Smartphone Dauer (Jahre)", key="ul_phone", min_value=1)
        
    with col_a2:
        st.subheader("Mobilität")
        st.number_input("PKW Preis (€)", key="price_car")
        st.number_input("PKW Dauer (Jahre)", key="ul_car", min_value=1)
        st.markdown("---")
        st.number_input("LKW/Transporter Preis (€)", key="price_truck")
        st.number_input("LKW Dauer (Jahre)", key="ul_truck", min_value=1)

    with col_a3:
        st.subheader("Einrichtung & Sonstiges")
        st.number_input("Büroplatz Preis (€)", key="price_desk")
        st.number_input("Büro Dauer (Jahre)", key="ul_desk", min_value=1)
        st.markdown("---")
        st.number_input("Sonstiges Capex p.a. (Pauschale €)", key="capex_annual")
        st.number_input("AfA Dauer Sonstiges (Jahre)", key="depreciation_misc")

# --- TAB 3: JOBS ---
with tab_jobs:
    st.header("Personalplanung")
    
    col_scale1, col_scale2 = st.columns([1, 2])
    with col_scale1:
        st.number_input("Ziel-Umsatz je FTE (€/Jahr)", step=5000.0, key="target_rev_per_fte", help="Steuert den Personalbedarf.")
        
    st.markdown("### Job Definitionen (15 Slots)")
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

# --- BERECHNUNGS-LOGIK ---

# 1. Jobs parsen
jobs_config = edited_jobs.to_dict(orient="records")
valid_jobs = []
for job in jobs_config:
    job["FTE Jahr 1"] = safe_float(job.get("FTE Jahr 1"))
    job["Jahresgehalt (€)"] = safe_float(job.get("Jahresgehalt (€)"))
    job["Sonstiges (€)"] = safe_float(job.get("Sonstiges (€)"))
    for key in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]:
        job[key] = bool(job.get(key))
    valid_jobs.append(job)

# 2. Konstanten
total_fte_y1 = sum(j["FTE Jahr 1"] for j in valid_jobs)
P = st.session_state["p_pct"] / 100.0
Q = st.session_state["q_pct"] / 100.0
CHURN = st.session_state["churn"] / 100.0
N_start = 10.0 
revenue_y1 = N_start * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
revenue_per_fte_benchmark = st.session_state["target_rev_per_fte"]

# 3. Asset Register Initialisieren
asset_types = {
    "Laptop": {"price_key": "price_laptop", "ul_key": "ul_laptop"},
    "Smartphone": {"price_key": "price_phone", "ul_key": "ul_phone"},
    "Auto": {"price_key": "price_car", "ul_key": "ul_car"},
    "LKW": {"price_key": "price_truck", "ul_key": "ul_truck"},
    "Büro": {"price_key": "price_desk", "ul_key": "ul_desk"},
    "Misc": {"price_key": None, "ul_key": "depreciation_misc"} 
}
asset_register = {k: [] for k in asset_types.keys()}

# 4. Simulation Loop
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

asset_details_log = []

for t in range(1, 11):
    row = {"Jahr": t}
    
    # --- A. Markt ---
    if t == 1: n_t = N_start
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    net_rev = n_t * st.session_state["arpu"] * (1 - st.session_state["discount"]/100)
    row["Umsatz"] = net_rev
    
    # --- B. Personal ---
    target_total_fte = 0
    if st.session_state["target_rev_per_fte"] > 0:
        target_total_fte = net_rev / st.session_state["target_rev_per_fte"]
        
    if t > 1: wage_factor *= (1 + st.session_state["wage_inc"]/100) * (1 + st.session_state["inflation"]/100)
    
    daily_personnel_cost = 0
    setup_opex = 0
    current_ftes_by_role = {}
    asset_needs = {k: 0.0 for k in asset_types.keys() if k != "Misc"}
    
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
        if curr_fte > 0: row[f"FTE {role}"] = curr_fte
        else: row[f"FTE {role}"] = 0.0
        
        cost = job["Jahresgehalt (€)"] * curr_fte * wage_factor * (1 + st.session_state["lnk_pct"]/100)
        daily_personnel_cost += cost
        
        prev = prev_ftes_by_role.get(role, 0) if t > 1 else 0
        delta = max(0, curr_fte - prev)
        setup_opex += delta * job["Sonstiges (€)"]
        
        if job["Laptop"]: asset_needs["Laptop"] += curr_fte
        if job["Smartphone"]: asset_needs["Smartphone"] += curr_fte
        if job["Auto"]: asset_needs["Auto"] += curr_fte
        if job["LKW"]: asset_needs["LKW"] += curr_fte
        if job["Büro"]: asset_needs["Büro"] += curr_fte

    total_fte_this_year = sum(current_ftes_by_role.values())
    row["FTE Total"] = total_fte_this_year
    row["Personalkosten"] = daily_personnel_cost
    
    # --- C. Asset Management (Invest & AfA) ---
    capex_now = 0.0
    depreciation_now = 0.0
    
    # 1. Pauschales Capex (Misc)
    capex_misc = st.session_state["capex_annual"]
    asset_register["Misc"].append({
        "year": t, "amount": 1, "price": capex_misc, "total_cost": capex_misc, 
        "ul": st.session_state["depreciation_misc"]
    })
    capex_now += capex_misc
    
    # 2. Job-Assets
    for atype, needed_count in asset_needs.items():
        price = st.session_state[asset_types[atype]["price_key"]]
        ul = st.session_state[asset_types[atype]["ul_key"]]
        
        valid_assets = 0
        for purchase in asset_register[atype]:
            age = t - purchase["year"]
            if age < purchase["ul"]:
                valid_assets += purchase["amount"]
        
        buy_count = max(0, needed_count - valid_assets)
        if buy_count > 0:
            total_cost = buy_count * price
            capex_now += total_cost
            asset_register[atype].append({
                "year": t, "amount": buy_count, "price": price, "total_cost": total_cost, "ul": ul
            })
            
    # 3. Abschreibung
    for atype, purchases in asset_register.items():
        type_depr = 0
        for p in purchases:
            age = t - p["year"]
            if 0 <= age < p["ul"]:
                charge = p["total_cost"] / p["ul"]
                type_depr += charge
        
        depreciation_now += type_depr
        asset_details_log.append({
            "Jahr": t, "Typ": atype, "Invest (€)": sum(p["total_cost"] for p in purchases if p["year"]==t), 
            "AfA (€)": type_depr
        })

    row["Investitionen (Assets)"] = capex_now
    row["Abschreibungen"] = depreciation_now
    
    # --- D. GuV ---
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
    row["Jahresüberschuss"] = net_income
    
    # --- E. Cashflow ---
    ar_end = net_rev * (st.session_state["dso"]/365.0)
    ap_end = total_opex * (st.session_state["dpo"]/365.0)
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    cf_op = net_income + depreciation_now - (ar_end - ar_prev) + (ap_end - ap_prev)
    cf_inv = -capex_now
    
    # Cash Sweep
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
    
    # --- F. Bilanz ---
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
    
    row["Zinsaufwand"] = interest
    row["Kreditaufnahme"] = borrow_amount
    row["Tilgung"] = repay_amount
    
    results.append(row)
    n_prev = n_t
    prev_ftes_by_role = current_ftes_by_role
    debt_prev = debt

df = pd.DataFrame(results)
df_assets_log = pd.DataFrame(asset_details_log)

# --- VISUALISIERUNG ---

with tab_assets:
    st.subheader("Detailauswertung Anlagevermögen")
    if not df_assets_log.empty:
        col_log1, col_log2 = st.columns(2)
        with col_log1:
            st.markdown("**Investitionen pro Jahr (€)**")
            pivot_inv = df_assets_log.pivot(index="Jahr", columns="Typ", values="Invest (€)")
            st.dataframe(pivot_inv.style.format("{:,.0f}"))
        with col_log2:
            st.markdown("**Abschreibungen pro Jahr (€)**")
            pivot_afa = df_assets_log.pivot(index="Jahr", columns="Typ", values="AfA (€)")
            st.dataframe(pivot_afa.style.format("{:,.0f}"))

with tab_dash:
    st.markdown("### KPIs Jahr 10")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("FTEs", f"{df['FTE Total'].iloc[-1]:.1f}")
    k4.metric("Kasse", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    st.markdown("### Finanzierung")
    st.line_chart(df.set_index("Jahr")[["Kasse", "Bankdarlehen"]])
    
    c1, c2 = st.columns(2)
    with c1:
        st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])
    with c2:
        st.subheader("Asset-Entwicklung")
        st.line_chart(df.set_index("Jahr")[["Investitionen (Assets)", "Abschreibungen"]])
    
    export_cols = [
        "Umsatz", "Gesamtkosten (OPEX)", "Personalkosten", "EBITDA", "Abschreibungen", "EBIT", "Jahresüberschuss",
        "Investitionen (Assets)", "Kasse", "Bankdarlehen", "Bilanz Check", "Anlagevermögen"
    ]
    csv = df.set_index("Jahr")[export_cols].T.to_csv(sep=";", decimal=",").encode('utf-8')
    st.download_button("📊 Report herunterladen", csv, "report_complete.csv", "text/csv")

with tab_guv: st.dataframe(df.set_index("Jahr")[["Umsatz", "Personalkosten", "Zinsaufwand", "Abschreibungen", "EBITDA", "Jahresüberschuss"]].style.format("€ {:,.0f}"))
with tab_cf: st.dataframe(df.set_index("Jahr")[["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Kasse"]].style.format("€ {:,.0f}"))
with tab_bilanz:
    c1, c2 = st.columns(2)
    with c1: st.dataframe(df.set_index("Jahr")[["Anlagevermögen", "Kasse", "Forderungen"]].style.format("€ {:,.0f}"))
    with c2: st.dataframe(df.set_index("Jahr")[["Eigenkapital", "Bankdarlehen", "Verb. LL"]].style.format("€ {:,.0f}"))
    if df["Bilanz Check"].abs().max() > 1: st.error("Bilanzfehler!")
    else: st.success("Bilanz OK")
