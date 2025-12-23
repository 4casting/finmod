import streamlit as st
import pandas as pd
import math
import numpy as np

# --- Konfiguration ---
st.set_page_config(page_title="Integrated Financial Model", layout="wide")
st.title("Integriertes Finanzmodell: GuV, Bilanz & Cashflow")

# Hilfsfunktion: Kreditberechnung (Annuität)
def calculate_loan_schedule(principal, rate, years):
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
        
        # Am Ende glattstellen
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

# --- TABS ---
tab_input, tab_dash, tab_guv, tab_cf, tab_bilanz, tab_loan = st.tabs([
    "📝 Inputs", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz", "🏦 Kredit"
])

# --- 1. INPUTS ---
with tab_input:
    col_main1, col_main2 = st.columns(2)
    
    with col_main1:
        st.subheader("1. Markt & Vertrieb")
        SAM = st.number_input("SAM (Marktgröße)", 39000, 1000)
        CAP_percent = st.number_input("Marktanteil Ziel (CAP) %", 2.3, 0.1)
        SOM = SAM * (CAP_percent / 100.0)
        st.caption(f"SOM: {int(SOM)} Kunden")
        
        p_percent = st.number_input("Innovatoren (p) %", 2.5, 0.1)
        q_percent = st.number_input("Imitatoren (q) %", 38.0, 1.0)
        churn_percent = st.number_input("Churn Rate %", 10.0, 1.0)
        
        ARPU = st.number_input("ARPU (€)", 3000, 100)
        discount_total = st.slider("Rabatte %", 0.0, 20.0, 0.0)

    with col_main2:
        st.subheader("2. Personal (Start)")
        # Eingabe FTE Jahr 1
        c1, c2, c3 = st.columns(3)
        with c1: fte_md_y1 = st.number_input("MD (Y1)", 0.0, 0.5)
        with c2: fte_exec_y1 = st.number_input("Execs (Y1)", 1.0, 0.5)
        with c3: 
            fte_field = st.number_input("Field", 0.25)
            fte_int = st.number_input("Inside Sales", 0.5)
            fte_mkt = st.number_input("Mkt", 0.125)
            fte_acc = st.number_input("Acc", 0.125)
        
        fte_l3_total = fte_field + fte_int + fte_mkt + fte_acc
        
        st.subheader("3. Kosten-Treiber")
        wage_inc = st.number_input("Lohnsteigerung %", 1.5) / 100
        inflation = st.number_input("Inflation %", 2.0) / 100
        lnk_pct = st.number_input("Lohnnebenkosten %", 25.0) / 100
        marketing_cac = st.number_input("Marketing CAC (€)", 3590)

    st.markdown("---")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    
    with col_fin1:
        st.subheader("4. Finanzierung (Jahr 1)")
        equity_initial = st.number_input("Einlage Eigenkapital (€)", 100000)
        loan_amount = st.number_input("Kreditbetrag (€)", 100000)
        loan_rate = st.number_input("Zinssatz Kredit (%)", 5.0) / 100.0
        loan_years = st.number_input("Laufzeit (Jahre)", 10)
    
    with col_fin2:
        st.subheader("5. Investments (CAPEX)")
        capex_initial = st.number_input("Initial Invest (IT/Auto) €", 20000, help="Assets im Jahr 1")
        capex_annual = st.number_input("Jährl. Ersatzinvest €", 2000)
        depreciation_period = st.number_input("Abschreibungsdauer Ø (Jahre)", 5)
        
    with col_fin3:
        st.subheader("6. Working Capital")
        dso = st.number_input("DSO (Zahlungsziel Kunden)", 30, help="Days Sales Outstanding")
        dpo = st.number_input("DPO (Zahlungsziel Lief.)", 30, help="Days Payable Outstanding")
        tax_rate = st.number_input("Steuersatz (KÖSt+GewSt) %", 30.0) / 100.0

# --- BERECHNUNG ---

# 1. Kreditplan erstellen
loan_df = calculate_loan_schedule(loan_amount, loan_rate, int(loan_years))
loan_map = loan_df.set_index("Jahr_Index").to_dict("index") if not loan_df.empty else {}

# Konstanten & Init
P, Q, CHURN = p_percent/100, q_percent/100, churn_percent/100
revenue_y1 = 10.0 * ARPU * (1 - discount_total/100)
rev_per_fte = revenue_y1 / fte_l3_total if fte_l3_total > 0 else 0

# Ratios Layer 3
l3_ratios = {
    "Field": fte_field/fte_l3_total if fte_l3_total else 0,
    "Inside": fte_int/fte_l3_total if fte_l3_total else 0,
    "Mkt": fte_mkt/fte_l3_total if fte_l3_total else 0,
    "Acc": fte_acc/fte_l3_total if fte_l3_total else 0
}

# Simulations-Variablen
results = []
n_prev = 10.0
l3_prev, exec_prev, md_prev = fte_l3_total, fte_exec_y1, fte_md_y1
wage_factor = 1.0

# Bilanz Startwerte (T=0)
cash = equity_initial + loan_amount - capex_initial
fixed_assets = capex_initial
equity = equity_initial
debt = loan_amount
retained_earnings = 0.0

for t in range(1, 11):
    row = {"Jahr": t}
    
    # --- A. OPERATIV (GuV) ---
    
    # 1. Kunden & Umsatz
    if t == 1: n_t = 10.0
    else:
        pot = max(0, SOM - n_prev)
        adopt = (P + Q * (n_prev / SOM))
        n_t = n_prev * (1 - CHURN) + (adopt * pot)
    row["Kunden"] = n_t
    
    net_rev = n_t * ARPU * (1 - discount_total/100)
    row["Umsatz"] = net_rev
    
    # 2. Personal
    if t > 1:
        req_l3 = net_rev / rev_per_fte if rev_per_fte > 0 else 0
        curr_l3 = max(req_l3, l3_prev)
        curr_exec = max(math.ceil(curr_l3/10), exec_prev)
        curr_md = max(math.ceil(curr_exec/5), md_prev)
    else:
        curr_l3, curr_exec, curr_md = fte_l3_total, fte_exec_y1, fte_md_y1
        
    row["FTE Total"] = curr_l3 + curr_exec + curr_md
    
    if t > 1: wage_factor *= (1 + wage_inc) * (1 + inflation)
    
    # Kosten (Vereinfacht zusammengefasst für Übersicht)
    cost_pers = (curr_md*80 + curr_exec*50 + curr_l3*40) * 160 * 12 * wage_factor * (1 + lnk_pct)
    cost_mkt = n_t * marketing_cac
    cost_opex_other = (row["FTE Total"] * (4044 + 1011)) + (net_rev * 0.05) + (net_rev * 0.10) # Büro/IT + Consulting + COGS
    if t == 1: cost_opex_other += 13000 # Einmalig Setup
    
    total_opex = cost_pers + cost_mkt + cost_opex_other
    ebitda = net_rev - total_opex
    
    # Abschreibungen (Linear auf Anlagevermögen Start des Jahres + Capex)
    # Vereinfachung: Capex wird sofort abgeschrieben oder über Dauer. 
    # Hier: Abschreibung auf Bestand.
    depreciation = (fixed_assets + (capex_annual if t>1 else 0)) / depreciation_period
    
    ebit = ebitda - depreciation
    
    # Zinsen (aus Tilgungsplan)
    loan_data = loan_map.get(t, {"Zinsen": 0, "Tilgung": 0, "Restschuld": 0})
    interest = loan_data["Zinsen"]
    
    ebt = ebit - interest
    tax = max(0, ebt * tax_rate)
    net_income = ebt - tax
    
    row["EBITDA"] = ebitda
    row["EBIT"] = ebit
    row["EBT"] = ebt
    row["Steuern"] = tax
    row["Jahresüberschuss"] = net_income
    
    # --- B. WORKING CAPITAL ---
    # Forderungen (AR) = Umsatz * DSO / 365
    ar_end = net_rev * (dso / 365)
    # Verbindlichkeiten (AP) = OPEX * DPO / 365
    ap_end = total_opex * (dpo / 365)
    
    # Delta Berechnung (für Cashflow)
    # Annahme: Vorjahr AR/AP holen, für t=1 sind AR_prev=0
    ar_prev = results[-1]["Forderungen"] if t > 1 else 0
    ap_prev = results[-1]["Verb. LL"] if t > 1 else 0
    
    delta_ar = ar_end - ar_prev # Wenn AR steigt -> Cash Out
    delta_ap = ap_end - ap_prev # Wenn AP steigt -> Cash In
    
    row["Forderungen"] = ar_end
    row["Verb. LL"] = ap_end
    
    # --- C. CASHFLOW (Indirekt) ---
    cf_op = net_income + depreciation - delta_ar + delta_ap
    
    # Invest: Capex (Initial im Jahr 1 schon in Startbilanz berücksichtigt? Nein, Cashflow t=1 betrachtet Bewegung)
    # Wir nehmen an: Initial Capex ist in t=0 passiert (Setup). In t=1 nur laufende.
    # Oder: Alles passiert in t=1. Wir modellieren: t=1 enthält Start-Invest.
    capex_now = capex_initial if t == 1 else capex_annual
    cf_inv = -capex_now
    
    # Finanzierung: 
    # Kreditaufnahme & Eigenkapital in t=1 (oder t=0). 
    # Wir modellieren Zuflüsse in t=1 CF Statement, um Startsaldo zu erklären.
    inflow_equity = equity_initial if t == 1 else 0
    inflow_loan = loan_amount if t == 1 else 0
    outflow_repay = loan_data["Tilgung"]
    
    cf_fin = inflow_equity + inflow_loan - outflow_repay
    
    delta_cash = cf_op + cf_inv + cf_fin
    
    # --- D. BILANZ UPDATE (End of Year) ---
    # Assets
    # Anlagevermögen = Alt + Invest - Abschreibung
    fixed_assets = fixed_assets + capex_now - depreciation
    if fixed_assets < 0: fixed_assets = 0
    
    # Cash = Alt + Delta
    if t == 1:
        # Start Cash war 0 vor Zuflüssen
        cash = delta_cash 
    else:
        cash_prev = results[-1]["Kasse"]
        cash = cash_prev + delta_cash
        
    row["Kasse"] = cash
    row["Anlagevermögen"] = fixed_assets
    row["Summe Aktiva"] = cash + ar_end + fixed_assets
    
    # Passiva
    # EK = Alt + JÜ + Einlage
    # Einlage in t=1 ist in Equity Inflow enthalten
    if t == 1:
        retained_earnings = net_income
        equity_curr = equity_initial + retained_earnings # Equity Initial hier statisch
    else:
        retained_earnings += net_income
        equity_curr = equity_initial + retained_earnings
        
    # Fremdkapital
    debt_curr = loan_data["Restschuld"]
    
    row["Eigenkapital"] = equity_curr
    row["Bankdarlehen"] = debt_curr
    row["Summe Passiva"] = equity_curr + debt_curr + ap_end
    
    # Check
    row["Bilanz Check"] = row["Summe Aktiva"] - row["Summe Passiva"]
    
    # Speichern
    row["CF Operativ"] = cf_op
    row["CF Invest"] = cf_inv
    row["CF Finanz"] = cf_fin
    row["Net Cash Change"] = delta_cash
    row["Zinsaufwand"] = interest
    row["Tilgung"] = outflow_repay
    
    results.append(row)
    
    # Update State for Next Loop
    n_prev = n_t
    l3_prev = curr_l3
    exec_prev = curr_exec
    md_prev = curr_md

df = pd.DataFrame(results)

# --- OUTPUTS ---

with tab_dash:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Umsatz J10", f"€ {df['Umsatz'].iloc[-1]:,.0f}")
    k2.metric("EBITDA J10", f"€ {df['EBITDA'].iloc[-1]:,.0f}")
    k3.metric("Kasse J10", f"€ {df['Kasse'].iloc[-1]:,.0f}")
    check_val = df['Bilanz Check'].iloc[-1]
    k4.metric("Bilanz Check", f"{check_val:.2f}", delta_color="normal" if abs(check_val)<1 else "inverse")
    
    st.subheader("Liquiditätsentwicklung (Cash)")
    st.line_chart(df.set_index("Jahr")["Kasse"])
    
    st.subheader("Umsatz vs. Kosten")
    st.bar_chart(df.set_index("Jahr")[["Umsatz", "EBITDA", "Jahresüberschuss"]])

with tab_guv:
    st.subheader("Gewinn- und Verlustrechnung")
    cols = ["Umsatz", "EBITDA", "EBIT", "Zinsaufwand", "EBT", "Steuern", "Jahresüberschuss"]
    st.dataframe(df.set_index("Jahr")[cols].style.format("€ {:,.0f}"))

with tab_cf:
    st.subheader("Kapitalflussrechnung (Cashflow Statement)")
    cols_cf = ["Jahresüberschuss", "CF Operativ", "CF Invest", "CF Finanz", "Net Cash Change", "Kasse"]
    st.dataframe(df.set_index("Jahr")[cols_cf].style.format("€ {:,.0f}"))
    
    st.bar_chart(df.set_index("Jahr")[["CF Operativ", "CF Invest", "CF Finanz"]])

with tab_bilanz:
    st.subheader("Bilanz (Aktiva & Passiva)")
    
    c_bil1, c_bil2 = st.columns(2)
    with c_bil1:
        st.markdown("**Aktiva**")
        st.dataframe(df.set_index("Jahr")[["Kasse", "Forderungen", "Anlagevermögen", "Summe Aktiva"]].style.format("€ {:,.0f}"))
    with c_bil2:
        st.markdown("**Passiva**")
        st.dataframe(df.set_index("Jahr")[["Verb. LL", "Bankdarlehen", "Eigenkapital", "Summe Passiva"]].style.format("€ {:,.0f}"))
        
    st.error(f"Maximale Abweichung Bilanz: {df['Bilanz Check'].abs().max():.2f} €")

with tab_loan:
    st.subheader("Kredit Tilgungsplan")
    st.dataframe(loan_df.set_index("Jahr_Index").style.format("€ {:,.2f}"))
    
    st.line_chart(loan_df.set_index("Jahr_Index")[["Zinsen", "Tilgung", "Restschuld"]])
