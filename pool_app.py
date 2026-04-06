# Copyright © 2026 FairPool v/Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.
# E-mail: tommywchristensen@gmail.com
# Denne app og dens underliggende kode/koncept er udviklet af FairPool v/Tommy Christensen.
# Alle rettigheder forbeholdes FairPool v/Tommy Christensen.
# Service-teknikere ansat hos Sol og Strand har tilladelse til at bruge appen uden beregning i forbindelse med deres arbejde.
# Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes kommercielt eller deles offentligt
# uden skriftlig tilladelse fra FairPool v/Tommy Christensen.

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ────────────────────────────────────────────────
# Google Sheets opsætning
# ────────────────────────────────────────────────
POOL_SHEET_ID = "1J7hqPcK7rpRwrjaYAhKh5jDpk8tNYKhfM3_7FWCY2rA"
POOL_WORKSHEET_NAME = "Ark1"

SPA_SHEET_ID = "16PLyJjec6WX-6Z5SQD1B_tl8qZYObKRx5Nt9ZRBHgRU"
SPA_WORKSHEET_NAME = "Ark1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)

pool_sheet = client.open_by_key(POOL_SHEET_ID).worksheet(POOL_WORKSHEET_NAME)
spa_sheet = client.open_by_key(SPA_SHEET_ID).worksheet(SPA_WORKSHEET_NAME)

# ────────────────────────────────────────────────
# Load funktioner
# ────────────────────────────────────────────────
def load_pools():
    values = pool_sheet.get_all_values()
    if not values:
        return {}, {}
 
    headers = [h.strip() for h in values[0]] if values else []
 
    pools = {}
    pool_info = {}
 
    for row in values[1:]:
        if not row or not row[0].strip(): continue
     
        name = row[0].strip()
        if not name or name.startswith("-"): continue
     
        vol_idx = headers.index("Volumen (m3)") if "Volumen (m3)" in headers else 1
        vol_str = row[vol_idx] if vol_idx < len(row) else "0"
        try:
            vol = float(vol_str)
        except (ValueError, TypeError):
            vol = 0.0
     
        pools[name] = vol
     
        extra = {}
        adresse_idx = headers.index("Adresse") if "Adresse" in headers else 2
        pumpetype_idx = headers.index("Pumpetype") if "Pumpetype" in headers else 3
        returskyl_idx = headers.index("Returskyl (5 min)") if "Returskyl (5 min)" in headers else 4
        nøglebokskode_idx = headers.index("Nøglebokskode") if "Nøglebokskode" in headers else 5
        he_idx = headers.index("HE telefonnummer") if "HE telefonnummer" in headers else 6
     
        if adresse_idx < len(row): extra["Adresse"] = row[adresse_idx] or "Ikke angivet"
        if pumpetype_idx < len(row): extra["Pumpetype"] = row[pumpetype_idx] or "Ikke angivet"
        if returskyl_idx < len(row) and row[returskyl_idx]:
            try:
                liter = float(row[returskyl_idx])
                kubik = liter / 1000
                extra["Returskyl (5 min)"] = f"{int(liter)} liter / {kubik:.1f} m³"
            except (ValueError):
                extra["Returskyl (5 min)"] = row[returskyl_idx]
        else:
            extra["Returskyl (5 min)"] = "Ikke angivet"
        if nøglebokskode_idx < len(row): extra["Nøglebokskode"] = row[nøglebokskode_idx] or "Ikke angivet"
        if he_idx < len(row): extra["HE telefonnummer"] = row[he_idx] or "Ikke angivet"
     
        pool_info[name] = extra
 
    return pools, pool_info


def load_spas():
    values = spa_sheet.get_all_values()
    if not values or len(values) < 1:
        return []
    
    headers = [h.strip() for h in values[0]]
    
    spas = []
    for row in values[1:]:
        if not row or not row[0].strip():
            continue
            
        spa_dict = {}
        for i, header in enumerate(headers):
            if i < len(row):
                spa_dict[header] = str(row[i]).strip() if row[i] else "Ikke angivet"
            else:
                spa_dict[header] = "Ikke angivet"
        
        display_name = f"{spa_dict.get('ObjektNummer', '')} - {spa_dict.get('Adresse', '')}".strip(" -")
        if display_name:
            spa_dict['display_name'] = display_name
            spas.append(spa_dict)
    
    return spas


def add_pool(name, vol):
    pool_sheet.append_row([name, vol, "", name, "", "", ""])

# ────────────────────────────────────────────────
# Service Type valg ved første opstart
# ────────────────────────────────────────────────
if "service_type" not in st.session_state:
    st.session_state.service_type = None

if st.session_state.service_type is None:
    st.set_page_config(page_title="FairPool – Vælg type", layout="centered")
    
    col_logo, _ = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    
    st.title("Velkommen til FairPool")
    st.subheader("Hvad skal du servicere i dag?")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🏊 Swimmingpool", use_container_width=True, type="primary"):
            st.session_state.service_type = "pool"
            st.rerun()
    
    with col2:
        if st.button("🛁 SPA / Boblebad", use_container_width=True, type="primary"):
            st.session_state.service_type = "spa"
            st.rerun()
    
    st.stop()

# ────────────────────────────────────────────────
# Hoved-app
# ────────────────────────────────────────────────
service_type = st.session_state.service_type

if service_type == "pool":
    # ==================== POOL DEL (din originale kode) ====================
    st.set_page_config(page_title="Pool Dosering", layout="wide")
    
    col_logo, col_empty = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    
    pools, pool_info = load_pools()
    pool_list = list(pools.keys())
    
    if pool_list:
        selected = st.selectbox("Vælg pool fra listen", pool_list)
        volume = pools[selected]
        info = pool_info.get(selected, {})
    else:
        st.info("Ingen pools fundet i Google Sheet – tilføj nogle i Sheetet først")
        selected = None
        volume = 0.0
        info = {}
    
    with st.expander("Tilføj ny pool", expanded=False):
        col1, col2 = st.columns([3, 2])
        with col1:
            new_name = st.text_input("Nyt pool-navn")
        with col2:
            new_vol = st.number_input("Volumen (m³)", min_value=0.0, value=0.0, step=1.0)
     
        if st.button("Gem ny pool"):
            if new_name.strip():
                add_pool(new_name.strip(), new_vol)
                st.success(f"{new_name.strip()} tilføjet til Google Sheet (Adresse sat til samme som navn)")
                st.rerun()
            else:
                st.error("Du skal indtaste et pool-navn")
    
    if not pool_list:
        st.stop()
    
    st.header(f"{selected} - {volume:.1f} m³")
    
    if selected:
        info_lines = []
        ordered_keys = ["Adresse", "Nøglebokskode", "HE telefonnummer", "Pumpetype", "Returskyl (5 min)"]
        for key in ordered_keys:
            if key in info:
                info_lines.append(f"{key}: {info[key]}")
        for key in info:
            if key not in ordered_keys:
                info_lines.append(f"{key}: {info[key]}")
        if info_lines:
            st.caption(" | ".join(info_lines))
    
    leased = st.radio("Husets status", ["Ikke udlejet", "Udlejet"], horizontal=True)
    colA, colB = st.columns(2)
    with colA:
        current_ph = st.number_input("Nuværende pH", min_value=0.0, value=7.0, step=0.1)
    with colB:
        current_cl = st.number_input("Nuværende frit klor (mg/l)", min_value=0.0, value=0.0, step=0.1)
    
    # ────────────────────────────────────────────────
    # KLORGAS-ADVARSEL + din originale doseringslogik
    # ────────────────────────────────────────────────
    target_ph = 7.0
    target_cl_leave = 4.0
    if current_cl < target_cl_leave:
        if current_ph < 6.5:
            st.error(
                "**STOP! ALVORLIG RISIKO FOR DØDELIG KLORGAS!**\n\n"
                "pH er under 6.5 og du skal tilsætte klor → der kan dannes **giftig klorgas (Cl₂)** øjeblikkeligt!\n"
                "Klorgas er farlig og kan være **dødelig** selv i små mængder.\n\n"
                "**GØR IKKE noget med klor før pH er hævet!**\n"
                "- Hæv pH til mindst 7.0–7.2 med pH-plus **FØR** du overvejer klor.\n"
                "- Mål pH igen efter hævning – fortsæt kun hvis pH er over 6.8.\n"
                "- Arbejd i godt ventileret område, brug åndedrætsværn hvis nødvendigt.\n"
                "- Ved tvivl: kontakt fagperson eller giftlinjen."
            )
        elif current_ph < 7.0:
            st.warning(
                "**Advarsel – lav pH og klor-tilsætning**\n\n"
                "pH er under 7.0 og der skal tilsættes klor → der er risiko for dannelse af **klorgas**.\n"
                "Risikoen stiger jo lavere pH er.\n\n"
                "**Anbefaling:**\n"
                "- Hæv pH til mindst 7.0–7.2 med pH-plus **før** du tilsætter klor.\n"
                "- Tilsæt klor langsomt og med god cirkulation.\n"
                "- Sørg for god ventilation i poolrummet.\n"
                "- Mål pH igen efter hævning, før du fortsætter."
            )
    
    st.markdown(
        """
        <div style="font-size: 1.05rem; color: #444; margin-bottom: 0.8rem;">
        <strong>Vigtigt om Tempo Sticks:</strong><br>
        - Afkryds kun feltet hvis der er mindst 0.5 stick tilbage<br>
        - Tempo Sticks skal altid placeres i KLORINATOREN eller i SKIMMEREN via en Tempo Stick Dispenser - aldrig direkte i skimmeren eller poolen!<br>
        - Ved eksisterende sticks skal du vælge 1 eller 2
        </div>
        """,
        unsafe_allow_html=True
    )
    
    has_existing_stick = st.checkbox("**Der ligger allerede en Tempo Stick i skimmer/klorinator**", value=False)
    
    st.markdown(
        """
        <div style="font-size: 0.9rem; color: #666; margin-top: -8px; margin-bottom: 0.5rem;">
        - Afkryds kun feltet hvis der er mindst 0.5 stick tilbage
        </div>
        """,
        unsafe_allow_html=True
    )
    
    existing_sticks = None
    if has_existing_stick:
        existing_sticks = st.selectbox(
            "Antal eksisterende Tempo Sticks",
            options=[1, 2],
            index=0,
            help="Du skal vælge 1 eller 2 – 0 er ikke muligt når feltet er afkrydset"
        )
        if existing_sticks is None:
            st.markdown(
                """
                <div style="background-color: #ffebee; color: #b71c1c; padding: 1rem; border-radius: 6px; margin: 1rem 0; border: 1px solid #ef9a9a;">
                <strong>Fejl:</strong> Du skal vælge 1 eller 2 eksisterende Tempo Sticks for at fortsætte.
                </div>
                """,
                unsafe_allow_html=True
            )
    
    target_ph = 7.0
    target_cl_leave = 4.0
    target_cl_maintenance = 5.5 if leased == "Udlejet" else 3.8
    delta_ph = current_ph - target_ph
    target_klor_op = 6.0 if current_cl <= 0.3 else 4.0
    delta_cl_leave = max(0, target_klor_op - current_cl)
    new_cl_after_leave = current_cl + delta_cl_leave
    delta_cl_maint = 0.0
    sticks_needed = 0.0
    ph_rise_from_sticks = 0.0
    if not has_existing_stick and leased == "Udlejet":
        if new_cl_after_leave <= 4.0:
            delta_cl_maint = max(0, target_cl_maintenance - new_cl_after_leave)
            if delta_cl_maint > 0:
                klor_per_stick_25m3 = 8.0
                raise_here = klor_per_stick_25m3 * (25.0 / volume)
                sticks_needed = delta_cl_maint / raise_here
                sticks_needed = max(1, round(sticks_needed))
                ph_rise_from_sticks = 0.4 * sticks_needed * (25.0 / volume)
            else:
                sticks_needed = 1
                ph_rise_from_sticks = 0.4 * sticks_needed * (25.0 / volume)
        else:
            sticks_needed = 0
    
    ph_rise_from_briqs = delta_cl_leave * 0.05
    total_ph_rise_from_klor = ph_rise_from_briqs + ph_rise_from_sticks
    expected_ph_after_klor = current_ph + total_ph_rise_from_klor
    delta_ph_eff = expected_ph_after_klor - target_ph
    
    st.markdown(
        """
        <div style="background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.15rem; color: #664d03;">
        <strong>GØR DETTE FØRST - trin for trin</strong><br><br>
        1. Juster pH først (opløs Saniklar PH Minus i en spand med poolvand og tilsæt blandingen langsomt, gerne ud for dyserne)<br>
        2. Tilsæt HTH Briquetter/Daytabs hvis nødvendigt for at nå ~4 mg/l ved afgang fra poolhus.<br>
        3. Tilsæt Tempo Sticks i KLORINATOREN eller i SKIMMERKURVEN via en Tempo Stick Dispenser (kun hvis der ingen Tempo Sticks er i forvejen og huset er udlejet)
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.header("Anbefalet dosering")
    
    if current_ph > 7.0 or expected_ph_after_klor > 7.0:
        delta_to_reduce = max(current_ph - target_ph, expected_ph_after_klor - target_ph)
        ml_minus = 35 * delta_to_reduce * volume
        st.subheader(f"Sænk pH med {delta_to_reduce:.2f} (efter klor)")
        st.markdown(f"**pH-minus → {ml_minus:.0f} ml**")
    elif current_ph < 7.0 and expected_ph_after_klor < 7.0:
        delta_to_raise = target_ph - expected_ph_after_klor
        ml_plus = 49 * delta_to_raise * volume
        st.subheader(f"Hæv pH med {delta_to_raise:.2f} (efter klor)")
        st.markdown(f"**pH-plus → {ml_plus:.0f} ml**")
    else:
        st.success("pH er på eller tæt på målet efter klor – ingen PH-justering nødvendig")
    
    if current_cl > 6.0:
        mg_to_lower = current_cl - target_cl_leave
        antiklor_per_m3_per_mg = 0.83
        antiklor_total = antiklor_per_m3_per_mg * mg_to_lower * volume
     
        st.subheader(f"Sænkning af klor (for højt: {current_cl:.1f} mg/l)")
        st.markdown(f"**Anti-klor: {antiklor_total:.0f} gram/ml**")
        st.caption(f"→ sænker klor fra {current_cl:.1f} mg/l til {target_cl_leave} mg/l")
        st.warning("Vent 1-2 timer efter antiklor, mål igen før yderligere klor-tilsætning!")
    else:
        if delta_cl_leave < 0.3:
            st.info("Klor OK ved afgang - ingen Briquetter/Daytabs nødvendige")
        else:
            briqs = 0.21 * delta_cl_leave * volume
            briqs_round = round(briqs)
            new_cl = current_cl + delta_cl_leave
         
            st.subheader(f"Opkloring til {target_klor_op} mg/l ved afgang")
            st.markdown(f"**HTH Briquetter/Daytabs: {briqs:.1f} stk → afrund til {briqs_round} stk**")
            st.caption(f"→ doserer klor fra {current_cl:.1f} mg/l til {new_cl:.1f} mg/l")
    
    st.subheader("Vedligehold - Tempo Sticks (5-7 dage)")
    if has_existing_stick:
        st.info(f"Der ligger allerede {existing_sticks} stk → ingen nye sticks foreslået")
    elif leased == "Ikke udlejet":
        st.info("Huset er ikke udlejet → ingen Tempo Sticks nødvendige")
    elif new_cl_after_leave <= 4.0:
        added_cl = sticks_needed * 8.0 * (25.0 / volume)
        st.markdown(f"**HTH Tempo Sticks: {sticks_needed} stk**")
        st.caption(f"→ giver ca. +{added_cl:.1f} mg/l klor og +{ph_rise_from_sticks:.2f} pH-stigning")
        st.caption("Tempo Sticks skal altid placeres i KLORINATOREN eller i SKIMMEREN via en Tempo Stick Dispenser - aldrig direkte i skimmeren eller poolen!")
    else:
        st.info("Klor efter opkloring er over 4.0 mg/l – ingen nye Tempo Sticks nødvendige til vedligehold.")

else:  # ==================== SPA DEL ====================
    st.set_page_config(page_title="SPA Dosering", layout="wide")
    
    col_logo, _ = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    
    st.title("🛁 SPA / Boblebad Service")
    
    spas = load_spas()
    
    if not spas:
        st.error("Ingen SPA'er fundet i Google Sheet. Tjek SHEET_ID eller arket.")
        st.stop()
    
    spa_options = [spa['display_name'] for spa in spas]
    selected_spa_display = st.selectbox("Vælg SPA fra listen", spa_options)
    
    selected_spa = next((spa for spa in spas if spa['display_name'] == selected_spa_display), None)
    
    if selected_spa:
        st.header(f"{selected_spa.get('ObjektNummer', 'SPA')} – {selected_spa.get('Adresse', '')}")
        
        st.subheader("Information")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ObjektNummer", selected_spa.get('ObjektNummer', '—'))
        with col2:
            st.metric("NøgleKode", selected_spa.get('NøgleKode', '—'))
        
        st.write(f"**Adresse:** {selected_spa.get('Adresse', 'Ikke angivet')}")
        
        # Status: Tomt eller Fuldt
        status = st.radio("SPA status", ["Tomt", "Fuldt"], horizontal=True)
        
        # Målinger
        colA, colB, colC = st.columns(3)
        with colA:
            current_ph = st.number_input("Nuværende pH", min_value=0.0, value=7.4, step=0.1)
        with colB:
            current_cl = st.number_input("Nuværende frit klor (mg/l)", min_value=0.0, value=2.0, step=0.1)
        with colC:
            current_temp = st.number_input("Temperatur (°C)", min_value=20.0, value=38.0, step=0.5)
        
        # Anbefalinger (baseret på standard SPA-værdier)
        target_ph_low = 7.2
        target_ph_high = 7.8
        target_cl_min = 2.0 if status == "Tomt" else 3.0
        target_cl_max = 5.0
        
        st.subheader("Anbefalet dosering og status")
        
        if current_ph < target_ph_low:
            st.error(f"**pH for lav ({current_ph:.1f})** – Hæv med pH-plus")
        elif current_ph > target_ph_high:
            st.error(f"**pH for høj ({current_ph:.1f})** – Sænk med pH-minus")
        else:
            st.success(f"pH er god ({current_ph:.1f})")
        
        if current_cl < target_cl_min:
            st.warning(f"**Klor for lav** – Tilsæt klor for at nå mindst {target_cl_min:.1f} mg/l")
        elif current_cl > target_cl_max:
            st.warning(f"**Klor for høj** – Vent eller brug anti-klor")
        else:
            st.success(f"Klor-niveau OK ({current_cl:.1f} mg/l)")
        
        if 36.5 <= current_temp <= 40:
            st.success(f"Temperatur OK ({current_temp:.1f} °C)")
        else:
            st.info("Anbefalet spa-temperatur: 37–39 °C")
        
        st.caption("Mål altid efter god cirkulation og opvarmning. Brug pålidelig testmetode.")

# ────────────────────────────────────────────────
# Sidebar – skift type
# ────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄 Skift mellem Pool og SPA"):
        if "service_type" in st.session_state:
            del st.session_state.service_type
        st.rerun()
