import streamlit as st
import pandas as pd
import math

# --- Konfiguration ---
st.set_page_config(page_title="Finanzmodell: Inputs & Hierarchie", layout="wide")
st.title("Finanzmodell mit dynamischer Personalstruktur")

# Tabs für die Strukturierung
tab_input, tab_sim, tab_data = st.tabs(["📝 Inputs & Konfiguration", "📊 Simulation & Ergebnisse", "📄 Detail-Daten"])

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
    st.caption("Geben Sie hier die FTEs für das erste Jahr ein. Das Modell skaliert die operativen Kräfte nach Umsatz und berechnet Führungskräfte nach der 1:5:10 Regel.")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    # Inputs für jede Position einzeln
    with col_p1:
        st.subheader("Layer 1: Management")
        fte_md_y1 = st.number_input("Managing Directors (Y1)", value=0.0, step=0.5, help="Wird in Folgejahren automatisch berechnet (1 je 5 Execs)")
        
    with col_p2:
        st.subheader("Layer 2: Executives")
        fte_exec_y1 = st.number_input("Executives (Y1)", value=1.0, step=0.5, help="Wird in Folgejahren automatisch berechnet (1 je 10 MA)")
        
    with col_p3:
        st.subheader("Layer 3: Mitarbeiter")
        fte_field_y1 = st.number_input("Field Service (Y1)", value=0.25, step=0.125)
        fte_internal_y1 = st.number_input("Internal Sales (Y1)", value=0.5, step=0.125)
        fte_mark_y1 = st.number_input("Marketing (Y1)", value=0.125, step=0.125)
        fte_acc_y1 = st.number_input("Accounting (Y1)", value=0.125, step=0.125)

    # Zusammenfassung Layer 3 für Berechnung
    fte_layer3_y1_total = fte_field_y1 + fte_internal_y1 + fte_mark_y1 + fte_acc_y1
    
    # Verhältnisse innerhalb Layer 3 speichern (für spätere Verteilung)
    layer3_ratios = {
        "Field Service": fte_field_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Internal Sales": fte_internal_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Marketing": fte_mark_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0,
        "Accounting": fte_acc_y1 / fte_layer3_y1_total if fte_layer3_y1_total > 0 else 0
    }

    st.markdown("---")
    st.header("4. Kosten-Variablen (Jahr 1 Basis)")
    
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
        marketing_per_cust = st.number_input("Marketing pro Neukunde (CAC) €", value=3590)
        office_per_fte = st.number_input("Büro/Miete pro FTE (€/Jahr)", value=4044)
        tech_per_fte = st.number_input("IT/Lizenzen pro FTE (€/Jahr)", value=1011)
        consulting_pct = st.number_input("Beratung (% vom Umsatz)", value=5.0, step=0.5) / 100.0
        car_cost = st.number_input("Kfz-Kosten p.a. (Exec/Field) €", value=10000)

# --- BERECHNUNGS-LOGIK ---

# Konstanten
P = p_percent / 100.0
Q = q_percent / 100.0
CHURN = churn_percent / 100.0
HOURS_PER_MONTH = 160
MONTHS = 12
N_YEAR_1 = 10.0 # Startwert Kunden (aus PDF fix oder anpassbar?) -> Nehmen wir als gegeben an.

# Berechnung Basis-Metriken Jahr 1
revenue_y1 = N_YEAR_1 * ARPU * (1 - discount_total/100)

# Produktivität: Wieviel Umsatz "schafft" ein operativer Mitarbeiter (Layer 3) im Jahr 1?
# Dies ist der Treiber für das Upscaling.
if fte_layer3_y1_total > 0:
    revenue_per_layer3_fte = revenue_y1 / fte_layer3_y1_total
else:
    revenue_per_layer3_fte = 0

# Simulation starten
results = []
n_prev = N_YEAR_1
layer3_prev = fte_layer3_y1_total
exec_prev = fte_exec_y1
md_prev = fte_md_y1

# Lohnfaktor
wage_factor = 1.0

for t in range(1, 11):
    row = {"Jahr": t}
    
    # 1. Kunden (Bass)
    if t == 1:
        n_t = N_YEAR_1
    else:
        # Bass Logik
        potential = max(0, SOM - n_prev)
        adoption = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adoption * potential)
    
    row["Kunden"] = n_t
    
    # 2. Umsatz
    gross_rev = n_t * ARPU
    net_rev = gross_rev * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 3. Personal (Upscaling & Hierarchie)
    
    if t == 1:
        # Im Jahr 1 nehmen wir exakt die Inputs (keine automatische Hierarchie-Korrektur, um User-Input zu ehren)
        curr_layer3 = fte_layer3_y1_total
        curr_exec = fte_exec_y1
        curr_md = fte_md_y1
    else:
        # Schritt A: Operative Mitarbeiter basierend auf Umsatzbedarf
        if revenue_per_layer3_fte > 0:
            req_layer3 = net_rev / revenue_per_layer3_fte
        else:
            req_layer3 = 0
        
        # Ratchet: Keine Entlassungen bei Layer 3
        curr_layer3 = max(req_layer3, layer3_prev)
        
        # Schritt B: Hierarchie-Regeln anwenden
        # Regel: 10 Mitarbeiter -> 1 Executive (d.h. pro angefangene 10 MA einen Exec)
        req_exec = math.ceil(curr_layer3 / 10.0)
        curr_exec = max(req_exec, exec_prev) # Auch hier keine Entlassungen
        
        # Regel: 5 Executives -> 1 MD (d.h. pro angefangene 5 Execs einen MD)
        req_md = math.ceil(curr_exec / 5.0)
        curr_md = max(req_md, md_prev)

    row["FTE Layer 3"] = curr_layer3
    row["FTE Exec"] = curr_exec
    row["FTE MD"] = curr_md
    row["FTE Total"] = curr_layer3 + curr_exec + curr_md
    
    # Aufteilung Layer 3 Rollen (gemäß Verteilung Jahr 1)
    row["FTE Field Service"] = curr_layer3 * layer3_ratios["Field Service"]
    row["FTE Internal Sales"] = curr_layer3 * layer3_ratios["Internal Sales"]
    row["FTE Marketing"] = curr_layer3 * layer3_ratios["Marketing"]
    row["FTE Accounting"] = curr_layer3 * layer3_ratios["Accounting"]
    
    # 4. Kosten
    
    # Lohninflation
    if t > 1:
        wage_factor *= (1 + wage_increase) * (1 + inflation)
        
    # Personalkosten berechnen
    cost_layer1 = curr_md * h_rate_layer1 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    cost_layer2 = curr_exec * h_rate_layer2 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    cost_layer3 = curr_layer3 * h_rate_layer3 * HOURS_PER_MONTH * MONTHS * wage_factor * (1 + lohnnebenkosten)
    
    total_personnel = cost_layer1 + cost_layer2 + cost_layer3
    row["Personalkosten"] = total_personnel
    
    # OPEX
    cost_marketing = n_t * marketing_per_cust
    cost_office = row["FTE Total"] * office_per_fte
    cost_tech = row["FTE Total"] * tech_per_fte
    cost_consulting = net_rev * consulting_pct
    
    # KFZ Kosten (Nur Execs und Field Service)
    relevant_cars = curr_exec + row["FTE Field Service"]
    cost_cars = relevant_cars * car_cost
    
    # COGS
    cost_cogs = net_rev * (cogs_percent / 100.0)
    
    # Sonstiges (Pauschale für Webseite etc.)
    cost_misc = 13000 if t == 1 else 3000
    
    total_opex = cost_marketing + cost_office + cost_tech + cost_consulting + cost_cars + cost_misc
    total_costs = total_personnel + total_opex + cost_cogs
    
    row["COGS"] = cost_cogs
    row["OPEX"] = total_opex
    row["Gesamtkosten"] = total_costs
    row["EBITDA"] = net_rev - total_costs
    
    # State Updates
    n_prev = n_t
    layer3_prev = curr_layer3
    exec_prev = curr_exec
    md_prev = curr_md
    
    results.append(row)

df = pd.DataFrame(results)

# --- OUTPUT TABS ---

with tab_sim:
    st.subheader("Simulations-Ergebnisse")
    
    # KPI Zeile
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Umsatz J10", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    kpi2.metric("EBITDA J10", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    kpi3.metric("FTE Total J10", f"{df['FTE Total'].iloc[-1]:.1f}")
    kpi4.metric("Kunden J10", f"{df['Kunden'].iloc[-1]:.0f}")

    st.markdown("### Personalentwicklung nach Hierarchie")
    st.caption("Das Diagramm zeigt, wie Executives und MDs basierend auf der Anzahl der Mitarbeiter (Layer 3) stufenweise ansteigen.")
    st.bar_chart(df.set_index("Jahr")[["FTE Layer 3", "FTE Exec", "FTE MD"]])
    
    st.markdown("### Finanzübersicht")
    st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten", "EBITDA"]])

with tab_data:
    st.subheader("Detaillierte Datentabelle")
    st.dataframe(df.style.format("{:,.0f}"))
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Daten als CSV herunterladen", csv, "finanzplan.csv", "text/csv")
