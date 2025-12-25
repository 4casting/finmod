import streamlit as st
import pandas as pd
import json
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime

# ==========================================
# 0. HILFSFUNKTIONEN & LOGIN
# ==========================================

def safe_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value): 
            return default
        return float(value)
    except: 
        return default

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("## 🔒 Finanzmodell - Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        user = st.text_input("Benutzername")
        pwd = st.text_input("Passwort", type="password")
        if st.button("Anmelden", type="primary"):
            if user == "admin" and pwd == "123":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Zugangsdaten falsch.")
    return False

if not check_password():
    st.stop()

st.set_page_config(page_title="Finanzmodell Pro (Master)", layout="wide")
st.sidebar.success("Eingeloggt als Admin")

# ==========================================
# 1. CONFIG & STATE
# ==========================================

DEFAULTS = {
    # Markt (Basis)
    "sam": 50000.0, "cap_pct": 5.0, "p_pct": 0.03, "q_pct": 0.38, "churn": 5.0, "manual_arpu": 1500.0,
    # ROA Strategie Defaults
    "roa_std_p_min": 0.005, "roa_std_p_max": 0.010,
    "roa_std_q_min": 0.150, "roa_std_q_max": 0.250,
    "roa_std_c_min": 0.030, "roa_std_c_max": 0.050,
    
    "roa_fight_p_min": 0.030, "roa_fight_p_max": 0.050,
    "roa_fight_q_min": 0.200, "roa_fight_q_max": 0.300,
    "roa_fight_c_min": 0.080, "roa_fight_c_max": 0.120,
    "roa_fight_discount": 25.0,

    # Finanzierung
    "equity": 50000.0, "loan_initial": 0.0, "min_cash": 10000.0, "loan_rate": 5.0,
    # Personal
    "wage_inc": 2.0, "inflation": 2.0, "lnk_pct": 25.0, "target_rev_per_fte": 120000.0,
    # Ops
    "tax_rate": 25.0, "dso": 30, "dpo": 30, "cac": 250.0,
    "capex_annual": 2000, "depreciation_misc": 5,
    # Hardware Preise
    "price_laptop": 1500, "ul_laptop": 3,
    "price_phone": 800, "ul_phone": 2,
    "price_car": 35000, "ul_car": 6,
    "price_truck": 50000, "ul_truck": 8,
    "price_desk": 1000, "ul_desk": 10,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

# Tabellen Init
if "current_jobs_df" not in st.session_state:
    roles = [
        {"Job Titel": "CEO", "Jahresgehalt (€)": 100000, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 0},
        {"Job Titel": "Sales", "Jahresgehalt (€)": 60000, "FTE Jahr 1": 1.0, "Laptop": True, "Smartphone": True, "Auto": True, "LKW": False, "Büro": True, "Sonstiges (€)": 500},
        {"Job Titel": "Tech", "Jahresgehalt (€)": 55000, "FTE Jahr 1": 2.0, "Laptop": True, "Smartphone": False, "Auto": False, "LKW": False, "Büro": True, "Sonstiges (€)": 200},
    ]
    for i in range(1, 10): roles.append({"Job Titel": f"Rolle {i}", "Jahresgehalt (€)": 0, "FTE Jahr 1": 0.0, "Laptop": False, "Smartphone": False, "Auto": False, "LKW": False, "Büro": False, "Sonstiges (€)": 0})
    st.session_state["current_jobs_df"] = pd.DataFrame(roles)

if "products_df" not in st.session_state:
    st.session_state["products_df"] = pd.DataFrame([
        {"Produkt": "Basis Abo", "Preis (€)": 50.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 5.0, "Take Rate (%)": 70.0, "Wiederkauf Rate (%)": 95.0, "Wiederkauf alle (Monate)": 1},
        {"Produkt": "Pro Abo", "Preis (€)": 150.0, "Avg. Rabatt (%)": 5.0, "Herstellungskosten (COGS €)": 20.0, "Take Rate (%)": 30.0, "Wiederkauf Rate (%)": 90.0, "Wiederkauf alle (Monate)": 1},
        {"Produkt": "Onboarding", "Preis (€)": 500.0, "Avg. Rabatt (%)": 0.0, "Herstellungskosten (COGS €)": 100.0, "Take Rate (%)": 50.0, "Wiederkauf Rate (%)": 0.0, "Wiederkauf alle (Monate)": 0},
    ])

if "cost_centers_df" not in st.session_state:
    st.session_state["cost_centers_df"] = pd.DataFrame([
        {"Kostenstelle": "Server & IT", "Grundwert Jahr 1 (€)": 1200, "Umsatz-Kopplung (%)": 10},
        {"Kostenstelle": "Marketing (Fix)", "Grundwert Jahr 1 (€)": 5000, "Umsatz-Kopplung (%)": 0},
        {"Kostenstelle": "Logistik", "Grundwert Jahr 1 (€)": 0, "Umsatz-Kopplung (%)": 5},
    ])

# ==========================================
# 2. PDF GENERATOR (ROBUST)
# ==========================================
class PDFReport(FPDF):
    def fix_text(self, text):
        if isinstance(text, (int, float)): return str(text)
        if text is None: return ""
        text = str(text).replace("€", "EUR").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        return text.encode('latin-1', 'replace').decode('latin-1')

    def header(self):
        self.set_font('Arial', 'B', 16); self.set_text_color(44, 62, 80)
        self.cell(0, 10, self.fix_text('Business Plan & Finanzmodell'), 0, 1, 'L')
        self.set_font('Arial', 'I', 9); self.set_text_color(100, 100, 100)
        self.cell(0, 5, self.fix_text(f'Generiert am: {datetime.now().strftime("%d.%m.%Y")}'), 0, 1, 'L')
        self.set_draw_color(200, 200, 200); self.line(10, 25, 287, 25); self.ln(10)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, self.fix_text(f'Seite {self.page_no()}/{{nb}}'), 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Arial', 'B', 14); self.set_text_color(0, 51, 102); self.set_fill_color(230, 240, 255)
        self.cell(0, 10, self.fix_text(title), 0, 1, 'L', 1); self.ln(4)

    def sub_title(self, title):
        self.set_font('Arial', 'B', 11); self.set_text_color(0, 0, 0)
        self.cell(0, 8, self.fix_text(title), 0, 1, 'L')

    def add_key_value_table(self, data_dict, title="Parameter"):
        self.sub_title(title); self.set_font('Arial', '', 9)
        col_width = 80; row_height = 6
        for k, v in data_dict.items():
            self.set_font('Arial', 'B', 9); self.cell(col_width, row_height, self.fix_text(str(k)), 1)
            self.set_font('Arial', '', 9)
            val = f"{v:,.2f}" if isinstance(v, float) else str(v)
            self.cell(col_width, row_height, self.fix_text(val), 1); self.ln()
        self.ln(5)

    def add_dataframe_table(self, df, col_widths=None):
        self.set_font('Arial', 'B', 8); self.set_fill_color(240, 240, 240)
        if not col_widths: col_width = 277 / len(df.columns); widths = [col_width] * len(df.columns)
        else: widths = col_widths
        for i, col in enumerate(df.columns): self.cell(widths[i], 7, self.fix_text(str(col)), 1, 0, 'C', 1)
        self.ln(); self.set_font('Arial', '', 8)
        for _, row in df.iterrows():
            for i, col in enumerate(df.columns):
                val = row[col]; txt = f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)
                self.cell(widths[i], 6, self.fix_text(txt), 1, 0, 'R' if isinstance(val, (int, float)) else 'L')
            self.ln()
        self.ln(5)

    def add_chart(self, fig):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            fig.savefig(tmpfile.name, dpi=150, bbox_inches='tight')
            self.image(tmpfile.name, x=30, w=230)
        self.ln(5)

def create_detailed_pdf(df_results, session_data, jobs_data, products_data, cc_data, title_prefix=""):
    pdf = PDFReport(orientation='L', unit='mm', format='A4'); pdf.alias_nb_pages()
    
    # 1. Summary
    pdf.add_page(); pdf.section_title(f"1. Management Summary {title_prefix}")
    if not df_results.empty:
        last = df_results.iloc[-1]
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, pdf.fix_text(f"Jahr 10: Umsatz {last['Umsatz']:,.0f} EUR | EBITDA {last['EBITDA']:,.0f} EUR | Cash {last['Kasse']:,.0f} EUR"), 0, 1); pdf.ln(5)
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(df_results["Jahr"], df_results["Umsatz"], label="Umsatz", marker='o')
        ax1.plot(df_results["Jahr"], df_results["Gesamtkosten (OPEX)"]+df_results["Wareneinsatz (COGS)"], label="Kosten", linestyle='--', color='red')
        ax1.bar(df_results["Jahr"], df_results["EBITDA"], label="EBITDA", alpha=0.3, color='green')
        ax1.legend(); ax1.grid(True, alpha=0.3); pdf.add_chart(fig1); plt.close(fig1)

    # 2. Inputs
    pdf.add_page(); pdf.section_title("2. Eingaben")
    pdf.add_key_value_table({
        "SAM": session_data.get("sam"), "Marktanteil Ziel": session_data.get("cap_pct"),
        "Equity": session_data.get("equity"), "Min Cash": session_data.get("min_cash")
    }, "Markt & Finanz")
    if jobs_data is not None: pdf.sub_title("Personal"); pdf.add_dataframe_table(jobs_data[["Job Titel", "Jahresgehalt (€)", "FTE Jahr 1"]].head(10))
    if products_data is not None: pdf.sub_title("Produkte"); pdf.add_dataframe_table(products_data[["Produkt", "Preis (€)", "Herstellungskosten (COGS €)"]])

    # 3. GuV (Fix für fehlende Spalten)
    pdf.add_page(); pdf.section_title("3. GuV")
    cols = ["Jahr", "Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "Abschreibungen", "EBIT", "Steuern", "Jahresüberschuss"]
    # SAFETY CHECK: Nur vorhandene Spalten drucken
    exist = [c for c in cols if c in df_results.columns]; widths = [15] + [30]*(len(exist)-1)
    pdf.add_dataframe_table(df_results[exist], col_widths=widths)
    
    # 4. Cashflow (Fix für fehlende Spalten)
    pdf.add_page(); pdf.section_title("4. Cashflow & Bilanz")
    cols_cf = ["Jahr", "Jahresüberschuss", "Investitionen (Assets)", "Kreditaufnahme", "Tilgung", "Net Cash Change", "Kasse"]
    # SAFETY CHECK
    exist_cf = [c for c in cols_cf if c in df_results.columns]
    pdf.add_dataframe_table(df_results[exist_cf])
    
    pdf.ln(5)
    # Bilanz Spalten checken
    cols_bil = ["Jahr", "Eigenkapital", "Bankdarlehen", "Verb. LL", "Summe Passiva"]
    exist_bil = [c for c in cols_bil if c in df_results.columns]
    if exist_bil:
        pdf.sub_title("Bilanz Passiva")
        pdf.add_dataframe_table(df_results[exist_bil])

    fig2, ax2 = plt.subplots(figsize=(10, 3.5))
    ax2.fill_between(df_results["Jahr"], df_results["Kasse"], color="skyblue", alpha=0.4, label="Kasse")
    ax2.plot(df_results["Jahr"], df_results["Bankdarlehen"], color="red", linestyle="--", label="Kredit")
    ax2.legend(); pdf.add_chart(fig2); plt.close(fig2)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 3. UI LAYOUT
# ==========================================
st.title("Integriertes Finanzmodell (V3 Robust + ROA)")

col_top1, col_top2 = st.columns([1, 3])
with col_top1:
    if st.button("🔄 NEU BERECHNEN", type="primary", use_container_width=True): st.rerun()

# Import/Export
with st.expander("📂 Import / Export", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        config = {k: st.session_state[k] for k in DEFAULTS}
        if "current_jobs_df" in st.session_state:
            df = pd.DataFrame(st.session_state["current_jobs_df"])
            for c in ["Laptop", "Smartphone", "Auto", "LKW", "Büro"]: 
                if c in df.columns: df[c] = df[c].apply(bool)
            config["jobs"] = df.to_dict('records')
        if "products_df" in st.session_state: config["prod"] = pd.DataFrame(st.session_state["products_df"]).to_dict('records')
        if "cost_centers_df" in st.session_state: config["cc"] = pd.DataFrame(st.session_state["cost_centers_df"]).to_dict('records')
        st.download_button("JSON Speichern", json.dumps(config, indent=2), "config.json")
    with c2:
        up = st.file_uploader("JSON Laden", type=["json"])
        if up and st.button("Importieren"):
            d = json.load(up)
            for k,v in d.items(): 
                if k in DEFAULTS: st.session_state[k] = v
            if "jobs" in d: st.session_state["current_jobs_df"] = pd.DataFrame(d["jobs"])
            if "prod" in d: st.session_state["products_df"] = pd.DataFrame(d["prod"])
            if "cc" in d: st.session_state["cost_centers_df"] = pd.DataFrame(d["cc"])
            st.rerun()

# Tabs
tab_input, tab_prod, tab_assets, tab_jobs, tab_cc, tab_dash, tab_guv, tab_cf, tab_bilanz = st.tabs([
    "📝 Markt", "📦 Produkte", "📉 Assets", "👥 Personal", "🏢 Kostenstellen", "📊 Dashboard", "📑 GuV", "💰 Cashflow", "⚖️ Bilanz"
])

# --- TAB INHALTE ---
with tab_input:
    # --- Standard Markt Inputs ---
    st.subheader("Markt & Bass-Modell (Manuelle Basis)")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("SAM (Gesamtmarkt)", step=1000.0, key="sam")
        st.number_input("Marktanteil Ziel %", step=0.1, key="cap_pct")
        st.info("Bass Diffusions Parameter (Basis):")
        st.number_input("Innovatoren (p) %", step=0.01, format="%.3f", key="p_pct")
        st.number_input("Imitatoren (q) %", step=0.1, format="%.3f", key="q_pct")
        st.number_input("Churn Rate %", step=0.5, key="churn")
        st.number_input("Manueller ARPU (Fallback)", step=50.0, key="manual_arpu")
    with c2:
        st.subheader("Finanzierung")
        st.number_input("Eigenkapital (€)", step=5000.0, key="equity")
        st.number_input("Mindest-Cash (€)", step=1000.0, key="min_cash")
        st.number_input("Start-Kredit (€)", step=5000.0, key="loan_initial")
        st.number_input("Kredit-Zins %", step=0.1, key="loan_rate")
        st.markdown("---")
        st.number_input("Steuersatz %", step=1.0, key="tax_rate")
        st.number_input("Lohnsteigerung %", step=0.1, key="wage_inc")
        st.number_input("Inflation %", step=0.1, key="inflation")

    # --- ROA STRATEGIE PARAMETER ---
    st.divider()
    st.header("ROA Strategie Parameter (Standard vs. Fighter)")
    st.caption("Diese Werte definieren die Ranges für die Best/Worst Case Berechnung im PDF Report.")
    
    col_std, col_fight = st.columns(2)
    
    with col_std:
        st.subheader("Option A: Standard")
        c_p1, c_p2 = st.columns(2)
        with c_p1: st.number_input("p Min", format="%.3f", step=0.001, key="roa_std_p_min")
        with c_p2: st.number_input("p Max", format="%.3f", step=0.001, key="roa_std_p_max")
        
        c_q1, c_q2 = st.columns(2)
        with c_q1: st.number_input("q Min", format="%.3f", step=0.01, key="roa_std_q_min")
        with c_q2: st.number_input("q Max", format="%.3f", step=0.01, key="roa_std_q_max")
        
        c_c1, c_c2 = st.columns(2)
        with c_c1: st.number_input("C Min (Share %)", format="%.3f", step=0.01, key="roa_std_c_min")
        with c_c2: st.number_input("C Max (Share %)", format="%.3f", step=0.01, key="roa_std_c_max")

    with col_fight:
        st.subheader("Option B: Fighter")
        f_p1, f_p2 = st.columns(2)
        with f_p1: st.number_input("p Min ", format="%.3f", step=0.001, key="roa_fight_p_min")
        with f_p2: st.number_input("p Max ", format="%.3f", step=0.001, key="roa_fight_p_max")
        
        f_q1, f_q2 = st.columns(2)
        with f_q1: st.number_input("q Min ", format="%.3f", step=0.01, key="roa_fight_q_min")
        with f_q2: st.number_input("q Max ", format="%.3f", step=0.01, key="roa_fight_q_max")
        
        f_c1, f_c2 = st.columns(2)
        with f_c1: st.number_input("C Min (Share %) ", format="%.3f", step=0.01, key="roa_fight_c_min")
        with f_c2: st.number_input("C Max (Share %) ", format="%.3f", step=0.01, key="roa_fight_c_max")
        
        st.number_input("Fighter Preis-Discount (%)", step=1.0, key="roa_fight_discount")


with tab_prod:
    st.info("Produkte steuern Umsatz & COGS.")
    st.session_state["products_df"] = st.data_editor(st.session_state["products_df"], num_rows="dynamic", use_container_width=True, key="ed_prod")

with tab_assets:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("IT"); st.number_input("Laptop Preis", key="price_laptop"); st.number_input("Laptop Jahre", key="ul_laptop")
        st.number_input("Handy Preis", key="price_phone"); st.number_input("Handy Jahre", key="ul_phone")
    with c2:
        st.caption("Fahrzeuge"); st.number_input("PKW Preis", key="price_car"); st.number_input("PKW Jahre", key="ul_car")
        st.number_input("LKW Preis", key="price_truck"); st.number_input("LKW Jahre", key="ul_truck")
    with c3:
        st.caption("Sonstiges"); st.number_input("Büro Preis", key="price_desk"); st.number_input("Büro Jahre", key="ul_desk")
        st.number_input("Capex p.a.", key="capex_annual"); st.number_input("AfA Jahre Sonst.", key="depreciation_misc")

with tab_jobs:
    st.number_input("Ziel-Umsatz pro FTE", step=5000.0, key="target_rev_per_fte")
    st.session_state["current_jobs_df"] = st.data_editor(st.session_state["current_jobs_df"], num_rows="dynamic", use_container_width=True, key="ed_jobs")

with tab_cc:
    st.info("Gemeinkosten & Variable Kostenstellen")
    st.session_state["cost_centers_df"] = st.data_editor(st.session_state["cost_centers_df"], num_rows="dynamic", use_container_width=True, key="ed_cc")

# ==========================================
# 4. BERECHNUNGSLOGIK (FUNKTION)
# ==========================================

def calculate_scenario(p_input, q_input, market_share_input, discount_pct=0.0):
    """
    Führt die komplette Finanzsimulation für gegebene Bass-Parameter und Preis-Discount durch.
    """
    
    # Inputs vorbereiten
    prods = pd.DataFrame(st.session_state["products_df"]).to_dict('records')
    jobs = pd.DataFrame(st.session_state["current_jobs_df"]).to_dict('records')
    ccs = pd.DataFrame(st.session_state["cost_centers_df"]).to_dict('records')

    # 1. Produkt-Mix berechnen (Gewichteter ARPU & COGS)
    w_arpu, w_cogs = 0.0, 0.0
    has_prod = False
    for p in prods:
        pr = safe_float(p.get("Preis (€)"))
        if pr > 0:
            has_prod = True
            c = safe_float(p.get("Herstellungskosten (COGS €)"))
            take = safe_float(p.get("Take Rate (%)"))/100
            months = safe_float(p.get("Wiederkauf alle (Monate)"))
            rep = safe_float(p.get("Wiederkauf Rate (%)"))/100
            freq = 1.0
            if months > 0:
                cycles = 12.0/months
                freq = 1.0 + (rep * (cycles - 1)) if cycles >= 1 else 1.0
            w_arpu += pr*take*freq
            w_cogs += c*take*freq

    # Base ARPU ermitteln
    base_arpu = w_arpu if has_prod and w_arpu > 0 else st.session_state["manual_arpu"]
    base_cogs_ratio = (w_cogs/w_arpu) if (has_prod and w_arpu > 0) else 0.15
    
    # DISCOUNT ANWENDEN (Fighter Strategie)
    calc_arpu = base_arpu * (1 - (discount_pct / 100.0))
    # Wir nehmen an COGS bleiben absolut gleich -> Ratio steigt wenn Preis sinkt
    calc_cogs_abs = base_arpu * base_cogs_ratio 
    
    # Konstanten
    P = p_input
    Q = q_input
    market_pot = st.session_state["sam"] * market_share_input # C als % von SAM
    N_start = 10.0

    n_prev = N_start
    debt = st.session_state["loan_initial"]
    cash = st.session_state["equity"]
    loss_carry = 0.0
    retained = 0.0
    fixed_assets = 0.0
    results = []
    prev_cc = {}
    asset_reg = {"Laptop":[], "Smartphone":[], "Auto":[], "LKW":[], "Büro":[], "Misc":[]}
    as_conf = {
        "Laptop": ("price_laptop", "ul_laptop"), "Smartphone": ("price_phone", "ul_phone"),
        "Auto": ("price_car", "ul_car"), "LKW": ("price_truck", "ul_truck"), "Büro": ("price_desk", "ul_desk")
    }

    for t in range(1, 11):
        row = {"Jahr": t}
        
        # 1. BASS MODELL
        if t == 1:
            n_t = N_start
        else:
            M = market_pot
            if M > 0:
                adoption = P * (M - n_prev) + Q * (n_prev/M) * (M - n_prev)
            else: adoption = 0
            n_t = n_prev * (1 - st.session_state["churn"]/100) + adoption
            n_t = min(n_t, M) # Cap
        
        row["Kunden"] = n_t
        rev = n_t * calc_arpu
        row["Umsatz"] = rev
        
        prev_rev = results[-1]["Umsatz"] if t > 1 else rev
        growth = (rev - prev_rev)/prev_rev if t > 1 and prev_rev > 0 else 0.0
        
        # Kosten
        # COGS sind absolut pro Einheit gleich, also Ratio auf neuen Umsatz anpassen oder absolut rechnen
        # Hier: Absolut per Kunde berechnet (genauer bei Preisänderung)
        # Wenn Fighter: Preis sinkt, Marge sinkt. COGS pro Kunde bleiben gleich.
        cogs = n_t * calc_cogs_abs
        row["Wareneinsatz (COGS)"] = cogs
        
        # Personal
        wage_idx = (1 + st.session_state["wage_inc"]/100)**(t-1)
        pers_cost = 0.0
        hw_needs = {k: 0.0 for k in as_conf}
        base_ftes = sum(safe_float(j.get("FTE Jahr 1")) for j in jobs)
        target_fte = rev / st.session_state["target_rev_per_fte"] if st.session_state["target_rev_per_fte"] > 0 else 0
        
        curr_total_fte = 0
        for j in jobs:
            base = safe_float(j.get("FTE Jahr 1"))
            sal = safe_float(j.get("Jahresgehalt (€)"))
            fte = max(base, target_fte * (base/base_ftes)) if base_ftes > 0 else 0
            curr_total_fte += fte
            pers_cost += sal * fte * wage_idx * (1 + st.session_state["lnk_pct"]/100)
            
            for hw in hw_needs:
                if j.get(hw): hw_needs[hw] += fte
        
        row["Personalkosten"] = pers_cost
        row["FTE Total"] = curr_total_fte
        
        # Kostenstellen
        cc_sum = 0.0
        for c in ccs:
            nm = c.get("Kostenstelle"); base = safe_float(c.get("Grundwert Jahr 1 (€)")); coup = safe_float(c.get("Umsatz-Kopplung (%)"))/100
            last = prev_cc.get(nm, base)
            curr = base if t==1 else last * (1 + growth*coup)
            prev_cc[nm] = curr; cc_sum += curr
        
        opex = pers_cost + cc_sum + (n_t * st.session_state["cac"]) + (rev * 0.02)
        row["Gesamtkosten (OPEX)"] = opex
        
        # Ergebnis
        ebitda = rev - cogs - opex
        row["EBITDA"] = ebitda
        
        # Assets & AfA
        capex = 0.0; afa = 0.0
        misc_p = st.session_state["capex_annual"]; misc_ul = st.session_state["depreciation_misc"]
        asset_reg["Misc"].append({"y":t, "v":misc_p, "ul":misc_ul})
        capex += misc_p
        
        for k, (pk, uk) in as_conf.items():
            needed = hw_needs[k]
            price = st.session_state[pk]; ul = st.session_state[uk]
            have = sum(x["amt"] for x in asset_reg[k] if (t - x["y"]) < x["ul"])
            buy = max(0, needed - have)
            if buy > 0:
                cost = buy * price; capex += cost
                asset_reg[k].append({"y":t, "amt":buy, "v":cost, "ul":ul})
                
        for k in asset_reg:
            for x in asset_reg[k]:
                if 0 <= (t - x["y"]) < x["ul"]: afa += x["v"] / x["ul"]
                
        row["Abschreibungen"] = afa; row["Investitionen (Assets)"] = capex
        ebit = ebitda - afa
        row["EBIT"] = ebit
        
        intr = debt * (st.session_state["loan_rate"]/100)
        ebt = ebit - intr
        
        # Steuer
        tax = 0.0
        if ebt < 0: loss_carry += abs(ebt)
        else:
            use = min(ebt, loss_carry); loss_carry -= use
            tax = (ebt - use) * (st.session_state["tax_rate"]/100)
        
        row["Steuern"] = tax
        net = ebt - tax
        row["Jahresüberschuss"] = net
        
        # Cashflow
        cf_op = net + afa
        cf_inv = -capex
        
        cash_start = results[-1]["Kasse"] if t > 1 else st.session_state["equity"]
        pre_fin = cash_start + cf_op + cf_inv
        
        min_c = st.session_state["min_cash"]
        borrow = 0.0; repay = 0.0
        if pre_fin < min_c: borrow = min_c - pre_fin
        elif pre_fin > min_c and debt > 0: repay = min(debt, pre_fin - min_c)
        
        cash_end = pre_fin + borrow - repay
        debt_end = debt + borrow - repay
        
        row["Kasse"] = cash_end
        row["Bankdarlehen"] = debt_end
        row["Net Cash Change"] = cf_op + cf_inv + borrow - repay
        row["Kreditaufnahme"] = borrow
        row["Tilgung"] = repay
        
        cash = cash_end; debt = debt_end; n_prev = n_t
        fixed_assets = max(0, fixed_assets + capex - afa)
        retained += net
        
        # Bilanz Check
        row["Anlagevermögen"] = fixed_assets
        row["Eigenkapital"] = st.session_state["equity"] + retained
        row["Summe Aktiva"] = fixed_assets + cash_end
        row["Summe Passiva"] = row["Eigenkapital"] + debt_end
        
        results.append(row)

    return pd.DataFrame(results)

# --- BERECHNUNG DES DASHBOARD SZENARIOS (Basis Werte aus Tab 1) ---
df_main = calculate_scenario(
    p_input=st.session_state["p_pct"], 
    q_input=st.session_state["q_pct"], 
    market_share_input=st.session_state["cap_pct"]/100.0, 
    discount_pct=0.0
)

# ==========================================
# 5. OUTPUTS
# ==========================================

with col_top2:
    st.write("**PDF Reports (Strategie Szenarien):**")
    c_pdf1, c_pdf2, c_pdf3, c_pdf4 = st.columns(4)
    
    # 1. Standard Best Case
    df_std_best = calculate_scenario(st.session_state["roa_std_p_max"], st.session_state["roa_std_q_max"], st.session_state["roa_std_c_max"], 0.0)
    pdf_b_std_best = create_detailed_pdf(df_std_best, st.session_state, pd.DataFrame(st.session_state["current_jobs_df"]), pd.DataFrame(st.session_state["products_df"]), pd.DataFrame(st.session_state["cost_centers_df"]), "Standard (Best Case)")
    with c_pdf1: st.download_button("Standard BEST", pdf_b_std_best, "std_best.pdf", "application/pdf")

    # 2. Standard Worst Case
    df_std_worst = calculate_scenario(st.session_state["roa_std_p_min"], st.session_state["roa_std_q_min"], st.session_state["roa_std_c_min"], 0.0)
    pdf_b_std_worst = create_detailed_pdf(df_std_worst, st.session_state, pd.DataFrame(st.session_state["current_jobs_df"]), pd.DataFrame(st.session_state["products_df"]), pd.DataFrame(st.session_state["cost_centers_df"]), "Standard (Worst Case)")
    with c_pdf2: st.download_button("Standard WORST", pdf_b_std_worst, "std_worst.pdf", "application/pdf")

    # 3. Fighter Best Case
    df_fight_best = calculate_scenario(st.session_state["roa_fight_p_max"], st.session_state["roa_fight_q_max"], st.session_state["roa_fight_c_max"], st.session_state["roa_fight_discount"])
    pdf_b_fight_best = create_detailed_pdf(df_fight_best, st.session_state, pd.DataFrame(st.session_state["current_jobs_df"]), pd.DataFrame(st.session_state["products_df"]), pd.DataFrame(st.session_state["cost_centers_df"]), "Fighter (Best Case)")
    with c_pdf3: st.download_button("Fighter BEST", pdf_b_fight_best, "fight_best.pdf", "application/pdf")

    # 4. Fighter Worst Case
    df_fight_worst = calculate_scenario(st.session_state["roa_fight_p_min"], st.session_state["roa_fight_q_min"], st.session_state["roa_fight_c_min"], st.session_state["roa_fight_discount"])
    pdf_b_fight_worst = create_detailed_pdf(df_fight_worst, st.session_state, pd.DataFrame(st.session_state["current_jobs_df"]), pd.DataFrame(st.session_state["products_df"]), pd.DataFrame(st.session_state["cost_centers_df"]), "Fighter (Worst Case)")
    with c_pdf4: st.download_button("Fighter WORST", pdf_b_fight_worst, "fight_worst.pdf", "application/pdf")


with tab_dash:
    k1, k2, k3 = st.columns(3)
    k1.metric("Umsatz J10 (Basis)", f"{df_main.iloc[-1]['Umsatz']:,.0f} €")
    k2.metric("EBITDA J10 (Basis)", f"{df_main.iloc[-1]['EBITDA']:,.0f} €")
    k3.metric("Kasse J10 (Basis)", f"{df_main.iloc[-1]['Kasse']:,.0f} €")
    st.line_chart(df_main.set_index("Jahr")[["Umsatz", "Gesamtkosten (OPEX)", "EBITDA"]])

with tab_guv: st.dataframe(df_main.set_index("Jahr")[["Umsatz", "Wareneinsatz (COGS)", "Gesamtkosten (OPEX)", "EBITDA", "EBIT", "Steuern", "Jahresüberschuss"]].T.style.format("{:,.0f}"))
with tab_cf: st.dataframe(df_main.set_index("Jahr")[["Jahresüberschuss", "Abschreibungen", "Investitionen (Assets)", "Net Cash Change", "Kasse"]].T.style.format("{:,.0f}"))
with tab_bilanz: st.dataframe(df_main.set_index("Jahr")[["Anlagevermögen", "Kasse", "Summe Aktiva", "Eigenkapital", "Bankdarlehen", "Summe Passiva"]].T.style.format("{:,.0f}"))
