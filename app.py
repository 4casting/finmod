import streamlit as st
import pandas as pd
import math
import numpy as np

# --- KONFIGURATION ---
st.set_page_config(page_title="Integrated Financial Model", layout="wide")
st.title("Integriertes Finanzmodell: GuV, Bilanz & Cashflow")

# --- HILFSFUNKTIONEN ---

def calculate_loan_schedule(principal, rate, years):
    """Berechnet einen Tilgungsplan für ein Annuitätendarlehen."""
    if principal <= 0 or years <= 0:
        return pd.DataFrame()
    
    # Jährliche Annuität
    if rate > 0:
        annuity = principal * (rate * (1 + rate)**years) / ((1 + rate)**years - 1)
    else:
        annuity = principal / years
        
    schedule = []
    remaining_balance = principal
    
    for t in range(1, int(years) + 1):
        interest = remaining_balance * rate
        repayment = annuity - interest
        
        # Am Ende glattstellen (Rundungsdifferenzen)
        if t == years:
            repayment = remaining_balance
            annuity = repayment + interest
            
        remaining_balance -= repayment
        
        schedule.append({
            "Jahr_Index": t,
            "Zinsen": interest,
            "Tilgung": repayment,
            "Annuität": annuity,
            "Restschuld": max(0, remaining_balance)
        })
    return pd.DataFrame(schedule)

# --- TABS STRUKTUR ---
tab_input, tab_dash, tab_guv, tab_cf, tab_bilanz, tab_loan = st.tabs([
    "📝 Inputs", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz", "🏦 Kredit"
])

# --- 1. INPUT SECTION ---
with tab_input:
    st.markdown("### Konfiguration der Parameter")
    
    col_main1, col_main2 = st.columns(2)
    
    with col_main1:
        st.subheader("1. Markt & Wachstum (Bass)")
        # Explizite Zuweisung von value und step verhindert Streamlit-Fehler
        SAM = st.number_input("SAM (Gesamtmarkt)", value=39000.0, step=1000.0)
        CAP_percent = st.number_input("Marktanteil Ziel (CAP) %", value=2.3, step=0.1)
        SOM = SAM * (CAP_percent / 100.0)
        st.info(f"Effektiver Zielmarkt (SOM): {int(SOM)} Kunden")
        
        p_percent = st.number_input("Innovatoren (p) %", value=2.5, step=0.1)
        q_percent = st.number_input("Imitatoren (q) %", value=38.0, step=1.0)
        churn_percent = st.number_input("Churn Rate % (jährlich)", value=10.0, step=1.0)
        
        st.subheader("Umsatztreiber")
        ARPU = st.number_input("ARPU (€ pro Kunde/Jahr)", value=3000.0, step=100.0)
        discount_total = st.slider("Rabatte & Skonto gesamt (%)", 0.0, 20.0, 0.0, 0.5)

    with col_main2:
        st.subheader("2. Personal (Startjahr)")
        st.caption("FTEs im Jahr 1. In Folgejahren skaliert das Modell automatisch.")
        
        c1, c2, c3 = st.columns(3)
        with c1: fte_md_y1 = st.number_input("MD (Layer 1)", value=0.0, step=0.5)
        with c2: fte_exec_y1 = st.number_input("Execs (Layer 2)", value=1.0, step=0.5)
        with c3: 
            fte_field = st.number_input("Außendienst", value=0.25, step=0.125)
            fte_int = st.number_input("Innendienst", value=0.5, step=0.125)
            fte_mkt = st.number_input("Marketing", value=0.125, step=0.125)
            fte_acc = st.number_input("Buchhaltung", value=0.125, step=0.125)
        
        fte_l3_total = fte_field + fte_int + fte_mkt + fte_acc
        
        st.subheader("3. Kosten-Parameter")
        wage_inc = st.number_input("Lohnsteigerung p.a. (%)", value=1.5, step=0.1) / 100.0
        inflation = st.number_input("Inflation p.a. (%)", value=2.0, step=0.1) / 100.0
        lnk_pct = st.number_input("Lohnnebenkosten (%)", value=25.0, step=1.0) / 100.0
        marketing_cac = st.number_input("Marketing CAC (€ pro Neukunde)", value=3590.0, step=100.0)

    st.markdown("---")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    
    with col_fin1:
        st.subheader("4. Finanzierung")
        equity_initial = st.number_input("Eigenkapital Einlage (€)", value=100000.0, step=5000.0)
        loan_amount = st.number_input("Bankdarlehen (€)", value=100000.0, step=5000.0)
        loan_rate = st.number_input("Zinssatz Kredit (%)", value=5.0, step=0.1) / 100.0
        loan_years = st.number_input("Laufzeit Kredit (Jahre)", value=10, step=1)
    
    with col_fin2:
        st.subheader("5. Investitionen (CAPEX)")
        capex_initial = st.number_input("Start-Investitionen (IT/Büro) €", value=20000.0, step=1000.0, help="Anschaffungen im Jahr 1")
        capex_annual = st.number_input("Laufende Investitionen p.a. €", value=2000.0, step=500.0)
        depreciation_period = st.number_input("Abschreibungsdauer Ø (Jahre)", value=5, step=1)
        
    with col_fin3:
        st.subheader("6. Working Capital & Steuern")
        dso = st.number_input("DSO (Zahlungsziel Kunden Tage)", value=30, step=1)
        dpo = st.number_input("DPO (Zahlungsziel Lief. Tage)", value=30, step=1)
        tax_rate = st.number_input("Gesamt-Steuersatz (Körp.+Gew.) %", value=30.0, step=1.0) / 100.0

# --- BERECHNUNGS-ENGINE ---

# 1. Kreditplan vorab berechnen
loan_df = calculate_loan_schedule(loan_amount, loan_rate, int(loan_years))
# Mapping für schnellen Zugriff im Loop (Jahr -> Daten)
loan_map = loan_df.set_index("Jahr_Index").to_dict("index") if not loan_df.empty else {}

# Konstanten und Faktoren
P = p_percent / 100.0
Q = q_percent / 100.0
CHURN = churn_percent / 100.0

# Umsatzbasis Jahr 1 berechnen (für Produktivitätsfaktor)
revenue_y1 = 10.0 * ARPU * (1 - discount_total/100)
# Wie viel Umsatz muss ein "Layer 3" Mitarbeiter erwirtschaften? (Skalierungsfaktor)
rev_per_fte = revenue_y1 / fte_l3_total if fte_l3_total > 0 else 0

# Verhältnisse innerhalb Layer 3 speichern
l3_ratios = {
    "Field": fte_field/fte_l3_total if fte_l3_total else 0,
    "Inside": fte_int/fte_l3_total if fte_l3_total else 0,
    "Mkt": fte_mkt/fte_l3_total if fte_l3_total else 0,
    "Acc": fte_acc/fte_l3_total if fte_l3_total else 0
}

# --- SIMULATIONS-SCHLEIFE (Jahre 1-10) ---
results = []

# Status-Variablen für Iteration
n_prev = 10.0 # Start Kunden
l3_prev, exec_prev, md_prev = fte_l3_total, fte_exec_y1, fte_md_y1
wage_factor = 1.0

# Bilanz-Startwerte (vor Jahr 1 sind alle Bestände 0, Zuflüsse passieren in T=1)
cash = 0.0
fixed_assets = 0.0 
equity = 0.0
debt = 0.0
retained_earnings = 0.0

for t in range(1, 11):
    row = {"Jahr": t}
    
    # --- A. OPERATIV (GuV / P&L) ---
    
    # 1. Kundenentwicklung (Bass Model)
    if t == 1: 
        n_t = 10.0
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    
    # 2. Umsatz
    net_rev = n_t * ARPU * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 3. Personalplanung (Hierarchisch & Skaliert)
    if t > 1:
        # Bedarf Layer 3 basierend auf Umsatz
        req_l3 = net_rev / rev_per_fte if rev_per_fte > 0 else 0
        # "Ratchet": Keine Entlassungen (Maximum aus Bedarf und Vorjahr)
        curr_l3 = max(req_l3, l3_prev)
        
        # Bedarf Execs: 1 je 10 Layer 3
        req_exec = math.ceil(curr_l3 / 10.0)
        curr_exec = max(req_exec, exec_prev)
        
        # Bedarf MD: 1 je 5 Execs
        req_md = math.ceil(curr_exec / 5.0)
        curr_md = max(req_md, md_prev)
    else:
        curr_l3, curr_exec, curr_md = fte_l3_total, fte_exec_y1, fte_md_y1
        
    row["FTE Total"] = curr_l3 + curr_exec + curr_md
    
    # 4. Kosten
    
    # Lohninflation anwenden
    if t > 1: wage_factor *= (1 + wage_inc) * (1 + inflation)
    
    # Personalkosten (Rate * Stunden * 12 * Inflation * Nebenkosten)
    # Annahme Stundensätze: MD=80, Exec=50, L3=40
    cost_pers = (curr_md*80 + curr_exec*50 + curr_l3*40) * 160 * 12 * wage_factor * (1 + lnk_pct)
    
    # Marketing Kosten (Driven by Active Customers / New Customers logic simplified)
    cost_mkt = n_t * marketing_cac
    
    # Sonstige OPEX (Büro, IT, Beratung, COGS)
    # Büro (4044) + IT (1011) pro FTE
    cost_opex_fix = row["FTE Total"] * (4044 + 1011)
    # Variable Kosten (% vom Umsatz)
    cost_consulting = net_rev * 0.05
    cost_cogs = net_rev * 0.10 # Standardannahme 10%
    
    # Einmalkosten Setup Jahr 1
    cost_setup = 13000.0 if t == 1 else 0.0
    
    total_opex = cost_pers + cost_mkt + cost_opex_fix + cost_consulting + cost_cogs + cost_setup
    
    # EBITDA
    ebitda = net_rev - total_opex
    
    # 5. Abschreibungen & Zinsen
    
    # Investition dieses Jahr
    capex_now = capex_initial if t == 1 else capex_annual
    
    # Abschreibung (Vereinfacht: Buchwert + Neuzugang / Dauer)
    depreciation = (fixed_assets + capex_now) / depreciation_period
    
    ebit = ebitda - depreciation
    
    # Zinsen aus Kreditplan
    loan_data = loan_map.get(t, {"Zinsen": 0.0, "Tilgung": 0.0, "Restschuld": 0.0})
    interest = loan_data["Zinsen"]
    
    ebt = ebit - interest
    
    # Steuern (nur bei Gewinn)
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax # Jahresüberschuss
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["Jahresüberschuss"] = net_income
    
    # --- B. WORKING CAPITAL (Veränderung) ---
    
    ar_end = net_rev * (dso / 365.0)  # Forderungen
    ap_end = total_opex * (dpo / 365.0) # Verbindlichkeiten
    
    # Vorjahreswerte holen
    if t == 1:
        ar_prev = 0.0
        ap_prev = 0.0
    else:
        # Zugriff auf das letzte Element der Ergebnisliste
        ar_prev = results[-1]["Forderungen"]
        ap_prev = results[-1]["Verb. LL"]
    
    delta_ar = ar_end - ar_prev
    delta_ap = ap_end - ap_prev
    
    row["Forderungen"] = ar_end
    row["Verb. LL"] = ap_end
    
    # --- C. CASHFLOW STATEMENT (Indirekte Methode) ---
    
    # 1. Operativer Cashflow
    # JÜ + Abschreibungen - Zunahme Forderungen + Zunahme Verb.
    cf_op = net_income + depreciation - delta_ar + delta_ap
    
    # 2. Cashflow aus Investition
    cf_inv = -capex_now
    
    # 3. Cashflow aus Finanzierung
    # Zuflüsse (nur Jahr 1)
    inflow_equity = equity_initial if t == 1 else 0.0
    inflow_loan = loan_amount if t == 1 else 0.0
    # Abflüsse (Tilgung)
    outflow_repay = loan_data["Tilgung"]
    
    cf_fin = inflow_equity + inflow_loan - outflow_repay
    
    # Netto Cash Veränderung
    delta_cash = cf_op + cf_inv + cf_fin
    
    # --- D. BILANZ UPDATE (End of Year) ---
    
    # Aktiva Update
    # Anlagevermögen = Alt + Invest - Abschreibung
    fixed_assets = fixed_assets + capex_now - depreciation
    fixed_assets = max(0, fixed_assets) # Darf nicht negativ werden
    
    # Kasse Update
    if t == 1:
        cash = delta_cash
    else:
        cash = results[-1]["Kasse"] + delta_cash
        
    row["Kasse"] = cash
    row["Anlagevermögen"] = fixed_assets
    row["Summe Aktiva"] = cash + ar_end + fixed_assets
    
    # Passiva Update
    # Eigenkapital = Einlage + kumulierte Gewinne
    if t == 1:
        retained_earnings = net_income
        equity_curr = equity_initial + retained_earnings
    else:
        retained_earnings += net_income
        equity_curr = equity_initial + retained_earnings
        
    # Fremdkapital (Restschuld)
    debt_curr = loan_data["Restschuld"]
    
    row["Eigenkapital"] = equity_curr
    row["Bankdarlehen"] = debt_curr
    row["Summe Passiva"] = equity_curr + debt_curr + ap_end
    
    # Bilanz-Check
    row["Bilanz Check"] = row["Summe Aktiva"] - row["Summe Passiva"]
    
    # CF Details für Tabelle speichern
    row["CF Operativ"] = cf_op
    row["CF Invest"] = cf_inv
    row["CF Finanz"] = cf_fin
    row["Net Cash Change"] = delta_cash
    row["Zinsaufwand"] = interest
    row["Tilgung"] = outflow_repay
    row["Steuern"] = tax
    
    results.append(row)
    
    # Variablen für nächsten Loop updaten
    n_prev = n_t
    l3_prev = curr_l3
    exec_prev = curr_exec
    md_prev = curr_md

df = pd.DataFrame(results)

# --- OUTPUT VISUALISIERUNG ---

# 1. Dashboard Tab
with tab_dash:
    st.markdown("### Management Summary (Jahr 10)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("Kasse (Cash)", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    
    # Bilanz Check Indikator
    check_val = df['Bilanz Check'].abs().max()
    k4.metric("Bilanz Integrität", "OK" if check_val < 1.0 else "FEHLER", 
              delta=f"Diff: {check_val:.2f} €", delta_color="inverse")
    
    st.markdown("---")
    
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.subheader("Umsatz- & Gewinnentwicklung")
        st.line_chart(df.set_index("Jahr")[["Umsatz", "Gesamtkosten", "EBITDA"]])
        
    with c_chart2:
        st.subheader("Liquidität (Kassenbestand)")
        st.area_chart(df.set_index("Jahr")["Kasse"], color="#85bb65")

# 2. GuV Tab
with tab_guv:
    st.subheader("Gewinn- und Verlustrechnung")
    cols_guv = ["Umsatz", "EBITDA", "EBIT", "Zinsaufwand", "Steuern", "Jahresüberschuss"]
    st.dataframe(df.set_index("Jahr")[cols_guv].style.format("€ {:,.0f}"))
    
    st.bar_chart(df.set_index("Jahr")["Jahresüberschuss"])

# 3. Cashflow Tab
with tab_cf:
    st.subheader("Kapitalflussrechnung")
    cols_cf = ["Jahresüberschuss", "CF Operativ", "CF Invest", "CF Finanz", "Net Cash Change", "Kasse"]
    st.dataframe(df.set_index("Jahr")[cols_cf].style.format("€ {:,.0f}"))
    
    st.markdown("**Cashflow Komponenten**")
    st.bar_chart(df.set_index("Jahr")[["CF Operativ", "CF Invest", "CF Finanz"]])

# 4. Bilanz Tab
with tab_bilanz:
    st.subheader("Bilanzstruktur")
    
    c_bil1, c_bil2 = st.columns(2)
    with c_bil1:
        st.markdown("#### Aktiva")
        cols_aktiva = ["Kasse", "Forderungen", "Anlagevermögen", "Summe Aktiva"]
        st.dataframe(df.set_index("Jahr")[cols_aktiva].style.format("€ {:,.0f}"))
        
    with c_bil2:
        st.markdown("#### Passiva")
        cols_passiva = ["Verb. LL", "Bankdarlehen", "Eigenkapital", "Summe Passiva"]
        st.dataframe(df.set_index("Jahr")[cols_passiva].style.format("€ {:,.0f}"))
    
    if df['Bilanz Check'].abs().max() > 1.0:
        st.error(f"Warnung: Bilanzdifferenz erkannt! Max Diff: {df['Bilanz Check'].abs().max():.2f} €")
    else:
        st.success("Bilanz ist ausgeglichen.")

# 5. Kredit Tab
with tab_loan:
    st.subheader("Tilgungsplan Bankdarlehen")
    if not loan_df.empty:
        col_l1, col_l2 = st.columns([1, 2])
        with col_l1:
            st.dataframe(loan_df.set_index("Jahr_Index").style.format("€ {:,.2f}"))
        with col_l2:
            st.line_chart(loan_df.set_index("Jahr_Index")[["Zinsen", "Tilgung", "Restschuld"]])
    else:
        st.warning("Kein Kreditbetrag oder Laufzeit eingegeben.")
