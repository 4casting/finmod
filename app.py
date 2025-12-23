import streamlit as st
import pandas as pd

# --- Konfiguration ---
st.set_page_config(page_title="Finanzmodell Pro", layout="wide")
st.title("Finanzmodell: Umsatz, Personal & Kosten (EBITDA)")

# --- 1. SIDEBAR: EINGABEN ---

st.sidebar.header("1. Markt & Wachstum")
SAM = st.sidebar.number_input("SAM (Gesamtmarkt)", 39000, step=1000)
CAP_percent = st.sidebar.slider("Marktanteil (CAP) %", 0.0, 10.0, 2.3, 0.1)
SOM = SAM * (CAP_percent / 100.0)
st.sidebar.caption(f"Ziel-Markt (SOM): {int(SOM)} Kunden")

p_percent = st.sidebar.slider("Innovatoren (p) %", 0.0, 10.0, 2.5, 0.1)
q_percent = st.sidebar.slider("Imitatoren (q) %", 0.0, 100.0, 38.0, 1.0)
churn_percent = st.sidebar.slider("Churn Rate %", 0.0, 30.0, 10.0, 1.0)

st.sidebar.header("2. Revenue & COGS")
ARPU = st.sidebar.number_input("ARPU (€/Jahr)", value=3000, step=100)
cogs_percent = st.sidebar.slider("COGS / RHB (% vom Umsatz)", 0.0, 80.0, 10.0, 5.0, help="Kosten für Wareneinsatz/Hosting etc.")
discount_total = st.sidebar.slider("Rabatte & Skonto gesamt %", 0.0, 20.0, 0.0, 0.5)

st.sidebar.header("3. Personal-Parameter")
wage_increase = st.sidebar.number_input("Jährl. Gehaltserhöhung %", 0.0, 10.0, 1.5, 0.1) / 100.0
inflation = st.sidebar.number_input("Inflation %", 0.0, 10.0, 2.0, 0.1) / 100.0
lohnnebenkosten = st.sidebar.slider("Lohnnebenkosten %", 0.0, 50.0, 25.0, 1.0) / 100.0

st.sidebar.subheader("Stundensätze (Basis Jahr 1)")
h_rate_layer1 = st.sidebar.number_input("Layer 1 (Mgmt) €/h", value=80)
h_rate_layer2 = st.sidebar.number_input("Layer 2 (Exec) €/h", value=50)
h_rate_layer3 = st.sidebar.number_input("Layer 3 (Staff) €/h", value=40)

# Start-FTEs (Jahr 1)
fte_y1 = {
    "Managing Director": 0.0,  # Layer 1
    "Executives": 1.0,         # Layer 2
    "Field Service": 0.25,     # Layer 3
    "Internal Sales": 0.5,     # Layer 3
    "Marketing": 0.125,        # Layer 3
    "Accounting": 0.125        # Layer 3
}

# Mapping Rollen zu Gehalts-Layer
role_layer_map = {
    "Managing Director": 1,
    "Executives": 2,
    "Field Service": 3,
    "Internal Sales": 3,
    "Marketing": 3,
    "Accounting": 3
}

st.sidebar.header("4. Sonstige Kosten (Treiber)")
marketing_per_cust = st.sidebar.number_input("Marketingkosten pro Kunde (€)", value=3590, help="Initial hoch (CAC), ggf. anpassen")
office_per_fte = st.sidebar.number_input("Büro/Miete pro FTE (€)", value=4044)
tech_per_fte = st.sidebar.number_input("IT/Lizenzen pro FTE (€)", value=1011)
consulting_pct = st.sidebar.slider("Beratung (Recht/Steuer) % v. Ums.", 0.0, 20.0, 5.0, 0.5) / 100.0
car_cost_per_relevant_fte = st.sidebar.number_input("Kfz-Kosten p.a. (€)", value=10000, help="Angenommen für Execs & Field Service")

# --- BERECHNUNG ---

# Konstanten
HOURS_PER_MONTH = 160
MONTHS = 12
N_YEAR_1 = 10.0
P = p_percent / 100.0
Q = q_percent / 100.0
CHURN = churn_percent / 100.0

# Initialisierung
total_fte_y1 = sum(fte_y1.values())
revenue_y1 = N_YEAR_1 * ARPU * (1 - discount_total/100)
target_rev_per_employee = revenue_y1 / total_fte_y1 if total_fte_y1 > 0 else 0

results = []
n_prev = N_YEAR_1
employees_prev = total_fte_y1

# Lohnfaktor initial (wächst mit Inflation/Erhöhung)
wage_factor = 1.0 

for t in range(1, 11):
    row = {"Jahr": t}
    
    # 1. Kunden (Bass)
    if t == 1:
        n_t = N_YEAR_1
    else:
        term_ret = n_prev * (1 - CHURN)
        # Bass Formel
        potential = max(0, SOM - n_prev)
        adoption = (P + Q * (n_prev / SOM))
        n_t = term_ret + (adoption * potential)
    
    row["Kunden"] = n_t

    # 2. Umsatz
    gross_rev = n_t * ARPU
    net_rev = gross_rev * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 3. Personalbedarf (Headcount)
    if target_rev_per_employee > 0:
        req_fte = net_rev / target_rev_per_employee
    else:
        req_fte = 0
    
    # "Ratchet"-Effekt: Keine Entlassungen im Modell
    curr_fte_total = max(req_fte, employees_prev)
    row["FTE Total"] = curr_fte_total
    
    # FTE Verteilung auf Rollen
    ftes_by_role = {}
    for role, val in fte_y1.items():
        share = val / total_fte_y1 if total_fte_y1 > 0 else 0
        ftes_by_role[role] = curr_fte_total * share
        row[f"FTE_{role}"] = ftes_by_role[role]

    # 4. KOSTEN BERECHNUNG
    
    # A) Personalkosten
    # Formel: FTE * Rate * Stunden * 12 * (1+LNK) * Wachstumsfaktor
    
    # Faktor update für dieses Jahr (kumulativ)
    if t > 1:
        wage_factor *= (1 + wage_increase) * (1 + inflation)
    
    personnel_cost_total = 0
    for role, count in ftes_by_role.items():
        layer = role_layer_map[role]
        if layer == 1: base_h = h_rate_layer1
        elif layer == 2: base_h = h_rate_layer2
        else: base_h = h_rate_layer3
        
        # Jahresgehalt pro Kopf (Brutto + LNK)
        yearly_cost_per_head = base_h * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
        
        role_cost = count * yearly_cost_per_head
        personnel_cost_total += role_cost
        
    row["Personalkosten"] = personnel_cost_total
    
    # B) Sonstige Kosten (OPEX)
    # Marketing (getrieben durch Kundenanzahl)
    # Hinweis: Im PDF war Y1 Marketing extrem hoch pro Kunde. Wir nehmen hier den Input-Wert.
    cost_marketing = n_t * marketing_per_cust
    
    # Büro & IT (getrieben durch FTEs)
    cost_office = curr_fte_total * office_per_fte
    cost_tech = curr_fte_total * tech_per_fte
    
    # Beratung (getrieben durch Umsatz)
    cost_consulting = net_rev * consulting_pct
    
    # Fahrzeuge (nur für Execs und Field Service)
    relevant_car_ftes = ftes_by_role["Executives"] + ftes_by_role["Field Service"]
    cost_cars = relevant_car_ftes * car_cost_per_relevant_fte
    
    # Sonstiges / Website (Pauschale Annahme oder Wartung)
    cost_misc = 3000 if t > 1 else 13000 # Beispiel aus PDF (Webseite)
    
    # COGS / RHB
    cost_cogs = net_rev * (cogs_percent / 100.0)
    
    opex_total = cost_marketing + cost_office + cost_tech + cost_consulting + cost_cars + cost_misc
    total_costs = personnel_cost_total + opex_total + cost_cogs
    
    row["COGS"] = cost_cogs
    row["OPEX (Andere)"] = opex_total
    row["Gesamtkosten"] = total_costs
    
    # 5. EBITDA
    ebitda = net_rev - total_costs
    row["EBITDA"] = ebitda
    row["Marge %"] = (ebitda / net_rev * 100) if net_rev > 0 else 0

    # State update
    n_prev = n_t
    employees_prev = curr_fte_total
    results.append(row)

df = pd.DataFrame(results)

# --- ANZEIGE ---

# KPI Karten
col1, col2, col3, col4 = st.columns(4)
col1.metric("Umsatz (Jahr 10)", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
col2.metric("EBITDA (Jahr 10)", f"€ {df['EBITDA'].iloc[-1]:,.0f}", delta=f"{df['Marge %'].iloc[-1]:.1f}% Marge")
col3.metric("FTEs (Jahr 10)", f"{df['FTE Total'].iloc[-1]:.1f}")
col4.metric("Personalkosten (Jahr 10)", f"€ {df['Personalkosten'].iloc[-1]:,.0f}")

# Tabs
tab1, tab2 = st.tabs(["📊 Analyse & Charts", "📄 Daten-Details"])

with tab1:
    st.subheader("Umsatz vs. Kosten vs. EBITDA")
    st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten", "EBITDA"]])
    
    st.subheader("Kostenstruktur (Stacked)")
    st.bar_chart(df.set_index("Jahr")[["Personalkosten", "OPEX (Andere)", "COGS"]])

with tab2:
    st.dataframe(df.style.format("{:,.0f}"))
    st.download_button("Excel/CSV Export", df.to_csv(index=False), "planungsrechnung.csv")
