import streamlit as st
import pandas as pd

# --- Konfiguration der Seite ---
st.set_page_config(page_title="Finanzmodell Simulation", layout="wide")

st.title("Finanzmodell & Personalplanung (Bass-Diffusion)")
st.markdown("""
Dieses Tool simuliert die Kundenentwicklung basierend auf dem **Bass-Diffusionsmodell** und berechnet 
darauf basierend Umsatz und Personalbedarf gemäß den Formeln aus dem PDF.
""")

# --- Sidebar: Eingabeparameter ---
st.sidebar.header("1. Markt & Wachstum")

# Variablen aus PDF [Source: 6, 7]
SAM = st.sidebar.number_input("Serviceable Addressable Market (SAM)", value=39000, step=1000, help="Gesamtmarktgröße")
CAP_percent = st.sidebar.slider("Maximaler Marktanteil (CAP) in %", min_value=0.0, max_value=20.0, value=2.3, step=0.1)
CAP = CAP_percent / 100.0

SOM = SAM * CAP
st.sidebar.info(f"Effektives Marktpotenzial (SOM): {int(SOM)} Kunden")

# Bass Parameter
p_percent = st.sidebar.slider("Innovatoren (p) in %", min_value=0.0, max_value=10.0, value=2.5, step=0.1)
q_percent = st.sidebar.slider("Imitatoren (q) in %", min_value=0.0, max_value=100.0, value=38.0, step=1.0)
churn_percent = st.sidebar.slider("Jährlicher Churn in %", min_value=0.0, max_value=50.0, value=10.0, step=1.0)

P = p_percent / 100.0
Q = q_percent / 100.0
CHURN_RATE = churn_percent / 100.0

st.sidebar.header("2. Finanzen (Umsatz)")
# Variablen aus PDF [Source: 16, 21]
ARPU = st.sidebar.number_input("ARPU (€)", value=3000, step=100)
DISCOUNT_RATE = st.sidebar.slider("Standard Rabatt (%)", 0.0, 20.0, 0.0) / 100.0
SKONTO_RATE = st.sidebar.slider("Skonto (%)", 0.0, 5.0, 0.0) / 100.0

st.sidebar.header("3. Start-Personal (Jahr 1)")
st.sidebar.markdown("_Definiert das Verhältnis Umsatz pro Mitarbeiter_")

# Initiale FTEs [Source: 1]
c1, c2 = st.sidebar.columns(2)
with c1:
    fte_exec = st.number_input("Executives", value=1.0, step=0.5)
    fte_field = st.number_input("Field Service", value=0.25, step=0.125)
    fte_acc = st.number_input("Accounting", value=0.125, step=0.125)
with c2:
    fte_internal = st.number_input("Internal Sales", value=0.5, step=0.5)
    fte_mark = st.number_input("Marketing", value=0.125, step=0.125)
    fte_mgmt = st.number_input("Managing Dir.", value=0.0, step=0.5)

# Struktur Dictionary
fte_structure_y1 = {
    "Managing Director": fte_mgmt,
    "Executives": fte_exec,
    "Field Service": fte_field,
    "Internal Sales": fte_internal,
    "Marketing/Graphics": fte_mark,
    "Accounting": fte_acc
}

# --- Berechnung ---

# Initialisierung Jahr 1
N_YEAR_1 = 10.0  # [Source: 3]
total_fte_y1 = sum(fte_structure_y1.values())

# Ziel-Umsatz pro Mitarbeiter berechnen (Basis Jahr 1) [Source: 35]
revenue_y1 = N_YEAR_1 * ARPU
if total_fte_y1 > 0:
    target_rev_per_employee = revenue_y1 / total_fte_y1
else:
    target_rev_per_employee = 0

st.sidebar.metric("Impliziter Umsatzziel / FTE", f"{target_rev_per_employee:,.0f} €")

# Simulations-Loop (Jahre 1-10)
years = range(1, 11)
results = []

n_prev = N_YEAR_1
employees_prev = total_fte_y1

for t in years:
    row = {"Jahr": t}
    
    # 1. Kundenbasis (Bass Diffusion) [Source: 7]
    if t == 1:
        n_t = N_YEAR_1
    else:
        # N(t) = N(t-1)*(1-C) + (p + q * N(t-1)/SOM) * (SOM - N(t-1))
        term_retention = n_prev * (1 - CHURN_RATE)
        adoption_rate = (P + Q * (n_prev / SOM))
        potential_pool = (SOM - n_prev)
        
        # Sättigungsschutz
        if potential_pool < 0: 
            potential_pool = 0
            
        n_t = term_retention + (adoption_rate * potential_pool)

    row["Kunden (N)"] = n_t
    
    # 2. Umsatz [Source: 19, 21]
    net_revenue = n_t * ARPU
    tot_net_revenue = net_revenue * (1 - SKONTO_RATE) * (1 - DISCOUNT_RATE)
    
    row["Netto Umsatz"] = net_revenue
    row["Gesamtumsatz (nach Rabatten)"] = tot_net_revenue
    
    # 3. Personalplanung [Source: 35, 33]
    if target_rev_per_employee > 0:
        req_employees = tot_net_revenue / target_rev_per_employee
    else:
        req_employees = 0
    
    # Bedingung: Nicht weniger Angestellte als in t-1
    employees_total = max(req_employees, employees_prev)
    row["Total FTEs"] = employees_total
    
    # Aufteilung nach Positionen [Source: 37]
    for role, fte_val in fte_structure_y1.items():
        ratio = fte_val / total_fte_y1 if total_fte_y1 > 0 else 0
        row[role] = employees_total * ratio

    # Update für nächste Iteration
    n_prev = n_t
    employees_prev = employees_total
    
    results.append(row)

df = pd.DataFrame(results)

# --- Darstellung der Ergebnisse ---

# KPI Übersicht
col1, col2, col3 = st.columns(3)
col1.metric("Kunden in Jahr 10", f"{df['Kunden (N)'].iloc[-1]:,.0f}")
col2.metric("Umsatz in Jahr 10", f"€ {df['Gesamtumsatz (nach Rabatten)'].iloc[-1]:,.0f}")
col3.metric("Mitarbeiter in Jahr 10", f"{df['Total FTEs'].iloc[-1]:.1f}")

# Tabs für Grafiken und Daten
tab1, tab2, tab3 = st.tabs(["📈 Grafiken", "📄 Datentabelle", "ℹ️ Formeln"])

with tab1:
    st.subheader("Entwicklung Kundenstamm")
    st.line_chart(df.set_index("Jahr")[["Kunden (N)"]])
    
    st.subheader("Entwicklung Umsatz")
    st.area_chart(df.set_index("Jahr")[["Gesamtumsatz (nach Rabatten)"]], color="#85bb65")
    
    st.subheader("Entwicklung Personal (FTEs)")
    # Stacked Bar Chart für FTEs
    fte_cols = list(fte_structure_y1.keys())
    st.bar_chart(df.set_index("Jahr")[fte_cols])

with tab2:
    st.subheader("Detaillierte Jahrestabelle")
    # Formatierung für die Anzeige
    st.dataframe(df.style.format({
        "Kunden (N)": "{:.1f}",
        "Netto Umsatz": "€ {:,.0f}",
        "Gesamtumsatz (nach Rabatten)": "€ {:,.0f}",
        "Total FTEs": "{:.2f}",
        "Executives": "{:.2f}",
        "Internal Sales": "{:.2f}",
        "Field Service": "{:.2f}",
        "Marketing/Graphics": "{:.2f}",
        "Accounting": "{:.2f}"
    }))
    
    # CSV Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Daten als CSV herunterladen",
        data=csv,
        file_name='finanzmodell_simulation.csv',
        mime='text/csv',
    )

with tab3:
    st.subheader("Verwendete mathematische Modelle")
    st.markdown(r"""
    **1. Bass-Diffusion mit Churn:**
    $$N(t) = N(t-1) \cdot (1-C) + \left(p + q \cdot \frac{N(t-1)}{SOM}\right) \cdot (SOM - N(t-1))$$
    
    **2. Umsatzberechnung:**
    $$Revenue(t) = N(t) \cdot ARPU \cdot (1 - Skonto) \cdot (1 - Discount)$$
    
    **3. Personalplanung:**
    $$FTE_{total}(t) = \frac{Revenue(t)}{TargetRevenuePerEmployee}$$
    *(Mit der Bedingung: Keine Entlassungen, $FTE(t) \geq FTE(t-1)$)*
    """)