import streamlit as st
import pandas as pd
import math

# --- Konfiguration ---
st.set_page_config(page_title="Finanzmodell Pro: GuV & KPIs", layout="wide")
st.title("Finanzmodell: GuV, Cashflow & Planung")

# Tabs definieren
tab_input, tab_sim, tab_guv, tab_data = st.tabs(["📝 Inputs", "📊 Dashboard", "📑 GuV Rechnung", "📄 Rohdaten"])

with tab_input:
    st.header("1. Markt & Wachstum (Bass-Modell)")
    col1, col2, col3 = st.columns(3)
    with col1:
        SAM = st.number_input("SAM (Gesamtmarkt)", value=39000, step=1000)
        CAP_percent = st.number_input("Marktanteil (CAP) %", value=2.3, step=0.1)
        SOM = SAM * (CAP_percent / 100.0)
        st.info(f"SOM (Zielkunden): {int(SOM)}")
    with col2:
        p_percent = st.number_input("Innovatoren (p) %", value=2.5, step=0.1)
        q_percent = st.number_input("Imitatoren (q) %", value=38.0, step=1.0)
    with col3:
        churn_percent = st.number_input("Churn Rate % (pro Jahr)", value=10.0, step=1.0)

    st.markdown("---")
    st.header("2. Finanz-Parameter (Jahr 1)")
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
        ARPU = st.number_input("ARPU (€ Umsatz pro Kunde/Jahr)", value=3000, step=100)
        discount_total = st.slider("Rabatte & Skonto gesamt (%)", 0.0, 20.0, 0.0, 0.5)
    with col_fin2:
        cogs_percent = st.slider("COGS / RHB (% vom Umsatz)", 0.0, 80.0, 10.0, 1.0)
    
    st.markdown("---")
    st.header("3. Personal: Startaufstellung (Jahr 1)")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.subheader("Layer 1: Management")
        fte_md_y1 = st.number_input("Managing Directors (Y1)", value=0.0, step=0.5)
        
    with col_p2:
        st.subheader("Layer 2: Executives")
        fte_exec_y1 = st.number_input("Executives (Y1)", value=1.0, step=0.5)
        
    with col_p3:
        st.subheader("Layer 3: Mitarbeiter")
        fte_field_y1 = st.number_input("Field Service (Y1)", value=0.25, step=0.125)
        fte_internal_y1 = st.number_input("Internal Sales (Y1)", value=0.5, step=0.125)
        fte_mark_y1 = st.number_input("Marketing (Y1)", value=0.125, step=0.125)
        fte_acc_y1 = st.number_input("Accounting (Y1)", value=0.125, step=0.125)

    fte_layer3_y1_total = fte_field_y1 + fte_internal_y1 + fte_mark_y1 + fte_acc_y1
    
    # Ratios speichern
    layer3_ratios = {
        "Field Service": fte_field_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Internal Sales": fte_internal_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Marketing": fte_mark_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Accounting": fte_acc_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0
    }

    st.markdown("---")
    st.header("4. Kosten-Variablen")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.subheader("Gehälter (Brutto)")
        h_rate_layer1 = st.number_input("Stundensatz Layer 1 (€)", value=80)
        h_rate_layer2 = st.number_input("Stundensatz Layer 2 (€)", value=50)
        h_rate_layer3 = st.number_input("Stundensatz Layer 3 (€)", value=40)
        lohnnebenkosten = st.number_input("Lohnnebenkosten (%)", value=25.0, step=1.0) / 100.0
        
    with col_c2:
        st.subheader("Steigerungsraten")
        wage_increase = st.number_input("Lohnsteigerung p.a. (%)", value=1.5, step=0.1) / 100.0
        inflation = st.number_input("Inflation p.a. (%)", value=2.0, step=0.1) / 100.0
        
    with col_c3:
        st.subheader("OPEX Treiber")
        marketing_per_cust = st.number_input("Marketing CAC (€)", value=3590)
        office_per_fte = st.number_input("Büro/Miete pro FTE (€)", value=4044)
        tech_per_fte = st.number_input("IT/Lizenzen pro FTE (€)", value=1011)
        consulting_pct = st.number_input("Beratung (% v. Umsatz)", value=5.0, step=0.5) / 100.0
        car_cost = st.number_input("Kfz p.a. (Exec/Field) €", value=10000)

    st.markdown("---")
    st.header("5. Steuern & Finanzen (GuV)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tax_trade_pct = st.number_input("Gewerbesteuer (%)", value=15.0, step=0.5) / 100.0
        tax_corp_pct = st.number_input("Körperschaftssteuer (%)", value=15.0, step=0.5) / 100.0
    with col_t2:
        depreciation_pa = st.number_input("Abschreibungen p.a. (Pauschale €)", value=5000, step=1000, help="Wertminderung von Anlagevermögen")
        interest_pa = st.number_input("Zinsen p.a. (Finanzergebnis €)", value=0, step=500, help="Zinsaufwand für Kredite")

# --- BERECHNUNG ---

P = p_percent / 100.0
Q = q_percent / 100.0
CHURN = churn_percent / 100.0
HOURS_PER_MONTH = 160
MONTHS = 12
N_YEAR_1 = 10.0

revenue_y1 = N_YEAR_1 * ARPU * (1 - discount_total/100)
revenue_per_layer3_fte = revenue_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0

results = []
n_prev = N_YEAR_1
layer3_prev = fte_layer3_y1_total
exec_prev = fte_exec_y1
md_prev = fte_md_y1
wage_factor = 1.0
kum_jue = 0.0 # Kumulierter Jahresüberschuss

for t in range(1, 11):
    row = {"Jahr": t}
    
    # 1. Bass Diffusion
    if t == 1:
        n_t = N_YEAR_1
    else:
        potential = max(0, SOM - n_prev)
        adoption = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adoption * potential)
    row["Kunden"] = n_t
    
    # 2. Umsatz
    gross_rev = n_t * ARPU
    net_rev = gross_rev * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 3. Personal (Hierarchie)
    if t == 1:
        curr_layer3 = fte_layer3_y1_total
        curr_exec = fte_exec_y1
        curr_md = fte_md_y1
    else:
        req_layer3 = net_rev / revenue_per_layer3_fte if revenue_per_layer3_fte > 0 else 0
        curr_layer3 = max(req_layer3, layer3_prev)
        
        req_exec = math.ceil(curr_layer3 / 10.0)
        curr_exec = max(req_exec, exec_prev)
        
        req_md = math.ceil(curr_exec / 5.0)
        curr_md = max(req_md, md_prev)

    row["FTE Total"] = curr_layer3 + curr_exec + curr_md
    
    # 4. Kosten
    if t > 1: wage_factor *= (1 + wage_increase) * (1 + inflation)
    
    # Personal
    cost_l1 = curr_md * h_rate_layer1 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    cost_l2 = curr_exec * h_rate_layer2 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    cost_l3 = curr_layer3 * h_rate_layer3 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    total_personnel = cost_l1 + cost_l2 + cost_l3
    
    # OPEX
    cost_marketing = n_t * marketing_per_cust
    cost_office = row["FTE Total"] * office_per_fte
    cost_tech = row["FTE Total"] * tech_per_fte
    cost_consulting = net_rev * consulting_pct
    relevant_cars = curr_exec + (curr_layer3 * layer3_ratios["Field Service"])
    cost_cars = relevant_cars * car_cost
    cost_misc = 13000 if t == 1 else 3000
    
    total_opex = cost_marketing + cost_office + cost_tech + cost_consulting + cost_cars + cost_misc
    cost_cogs = net_rev * (cogs_percent / 100.0)
    
    # 5. GuV Stufen
    total_costs = total_personnel + total_opex + cost_cogs
    row["Gesamtkosten"] = total_costs
    
    ebitda = net_rev - total_costs
    row["EBITDA"] = ebitda
    
    ebit = ebitda - depreciation_pa
    row["EBIT"] = ebit
    
    ebt = ebit - interest_pa
    row["EBT"] = ebt
    
    # Steuern (nur auf positive Erträge, kein Verlustvortrag in diesem simplen Modell)
    if ebt > 0:
        taxes = ebt * (tax_trade_pct + tax_corp_pct)
    else:
        taxes = 0
    row["Steuern"] = taxes
    
    jue = ebt - taxes
    row["Jahresüberschuss (JÜ)"] = jue
    
    kum_jue += jue
    row["Kumulierter JÜ"] = kum_jue
    
    # State Updates
    n_prev = n_t
    layer3_prev = curr_layer3
    exec_prev = curr_exec
    md_prev = curr_md
    results.append(row)

df = pd.DataFrame(results)

# --- OUTPUT ---

with tab_sim:
    st.subheader("Management Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz (Jahr 10)", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA (Jahr 10)", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("Jahresüberschuss (Jahr 10)", f"€ {df['Jahresüberschuss (JÜ)'].iloc[-1]:,.0f}")
    k4.metric("Kumulierter Gewinn (J10)", f"€ {df['Kumulierter JÜ'].iloc[-1]:,.0f}")
    
    st.line_chart(df.set_index("Jahr")[["EBITDA", "EBIT", "Jahresüberschuss (JÜ)"]])

with tab_guv:
    st.subheader("Gewinn- und Verlustrechnung (GuV)")
    
    # Auswahl der GuV-Spalten für die saubere Darstellung
    cols_guv = [
        "Umsatz", "Gesamtkosten", "EBITDA", 
        "EBIT", "EBT", "Steuern", 
        "Jahresüberschuss (JÜ)", "Kumulierter JÜ"
    ]
    
    # Transponieren für klassische GuV Ansicht (Jahre als Spalten)
    df_guv = df.set_index("Jahr")[cols_guv].T
    
    st.dataframe(df_guv.style.format("€ {:,.0f}"))
    
    st.markdown("### Kennzahlen Übersicht")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.caption("Steuerlast")
        st.bar_chart(df.set_index("Jahr")["Steuern"])
    with col_g2:
        st.caption("Entwicklung Jahresüberschuss")
        st.bar_chart(df.set_index("Jahr")["Jahresüberschuss (JÜ)"])

with tab_data:
    st.subheader("Vollständiger Datensatz")
    st.dataframe(df.style.format("{:,.0f}"))
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "business_plan_guv.csv")
