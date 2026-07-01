# Copyright © 2026 FairPool v/Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.
# E-mail: info@fairpool.dk
# Denne app og dens underliggende kode/koncept er udviklet af FairPool v/Tommy Christensen.
# Alle rettigheder forbeholdes FairPool v/Tommy Christensen.
# Service Teknikere ansat hos Sol og Strand har tilladelse til at bruge appen uden beregning i forbindelse med deres arbejde.
# Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes kommercielt eller deles offentligt
# uden skriftlig tilladelse fra FairPool v/Tommy Christensen.

import streamlit as st
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

# ────────────────────────────────────────────────
# Firebase Authentication (API key fra secrets)
# ────────────────────────────────────────────────
FIREBASE_API_KEY = st.secrets["firebase"]["api_key"]

FIREBASE_SIGN_IN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_RESET_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
FIREBASE_SET_PW_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={FIREBASE_API_KEY}"
FIREBASE_LOOKUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"

def firebase_sign_in(email, password):
    r = requests.post(FIREBASE_SIGN_IN_URL, json={
        "email": email, "password": password, "returnSecureToken": True
    })
    data = r.json()
    if "idToken" in data:
        return data["idToken"], None
    msg = data.get("error", {}).get("message", "Ukendt fejl")
    return None, msg

def firebase_send_reset(email):
    requests.post(FIREBASE_RESET_URL, json={"requestType": "PASSWORD_RESET", "email": email})

def firebase_set_password(id_token, new_password):
    r = requests.post(FIREBASE_SET_PW_URL, json={"idToken": id_token, "password": new_password, "returnSecureToken": True})
    data = r.json()
    return "idToken" in data, data.get("error", {}).get("message", "")

def firebase_needs_password_set(id_token):
    r = requests.post(FIREBASE_LOOKUP_URL, json={"idToken": id_token})
    data = r.json()
    users = data.get("users", [])
    if not users:
        return False
    user = users[0]
    return user.get("lastLoginAt") == user.get("createdAt")

def show_login():
    force_light_mode()
    col_logo, _ = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    st.title("FairPool – Log ind")
    st.markdown("Log ind med din arbejds-email og adgangskode.")
    tab_login, tab_reset = st.tabs(["Log ind", "Glemt adgangskode"])
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Adgangskode", type="password", key="login_password")
        if st.button("Log ind", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Udfyld både email og adgangskode.")
            else:
                token, err = firebase_sign_in(email.strip(), password)
                if token:
                    if firebase_needs_password_set(token):
                        st.session_state["pending_token"] = token
                        st.session_state["pending_email"] = email.strip()
                        st.rerun()
                    else:
                        st.session_state["auth_token"] = token
                        st.session_state["auth_email"] = email.strip()
                        st.rerun()
                else:
                    if "EMAIL_NOT_FOUND" in err or "INVALID_PASSWORD" in err or "INVALID_LOGIN_CREDENTIALS" in err:
                        st.error("Forkert email eller adgangskode.")
                    elif "TOO_MANY_ATTEMPTS" in err:
                        st.error("For mange forsøg – prøv igen senere.")
                    else:
                        st.error(f"Login fejlede: {err}")
    with tab_reset:
        reset_email = st.text_input("Din email", key="reset_email")
        if st.button("Send nulstillingsmail", use_container_width=True):
            if reset_email.strip():
                firebase_send_reset(reset_email.strip())
                st.success("Hvis emailen er registreret, er der sendt en nulstillingsmail.")
            else:
                st.error("Indtast din email.")

def show_set_password():
    force_light_mode()
    col_logo, _ = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    st.title("Vælg din adgangskode")
    st.markdown("Velkommen! Da dette er dit første login, skal du vælge din egen adgangskode.")
    pw1 = st.text_input("Ny adgangskode (mindst 6 tegn)", type="password", key="new_pw1")
    pw2 = st.text_input("Gentag adgangskode", type="password", key="new_pw2")
    if st.button("Gem adgangskode", type="primary", use_container_width=True):
        if len(pw1) < 6:
            st.error("Adgangskoden skal være mindst 6 tegn.")
        elif pw1 != pw2:
            st.error("Adgangskoderne er ikke ens.")
        else:
            ok, err = firebase_set_password(st.session_state["pending_token"], pw1)
            if ok:
                st.session_state["auth_token"] = st.session_state.pop("pending_token")
                st.session_state["auth_email"] = st.session_state.pop("pending_email")
                st.success("Adgangskode gemt – du er nu logget ind!")
                st.rerun()
            else:
                st.error(f"Kunne ikke gemme adgangskode: {err}")


# ────────────────────────────────────────────────
# Google Sheets opsætning
# ────────────────────────────────────────────────
POOL_SHEET_ID = "1J7hqPcK7rpRwrjaYAhKh5jDpk8tNYKhfM3_7FWCY2rA"
POOL_WORKSHEET_NAME = "Sheet1"

SPA_SHEET_ID = "16PLyJjec6WX-6Z5SQD1B_tl8qZYObKRx5Nt9ZRBHgRU"
SPA_WORKSHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_sheets_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_pool_sheet():
    return get_sheets_client().open_by_key(POOL_SHEET_ID).worksheet(POOL_WORKSHEET_NAME)

@st.cache_resource
def get_spa_sheet():
    return get_sheets_client().open_by_key(SPA_SHEET_ID).worksheet(SPA_WORKSHEET_NAME)

# ────────────────────────────────────────────────
# Load funktioner
# ────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_pools():
    values = get_pool_sheet().get_all_values()
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
        instruktioner_idx = headers.index("Instruktioner") if "Instruktioner" in headers else None
     
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
        if instruktioner_idx is not None and instruktioner_idx < len(row):
            extra["Instruktioner"] = row[instruktioner_idx] or ""
     
        pool_info[name] = extra
 
    return pools, pool_info


@st.cache_data(ttl=300)
def load_spas():
    values = get_spa_sheet().get_all_values()
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
    get_pool_sheet().append_row([name, vol, "", name, "", "", ""])

def force_light_mode():
    st.markdown(
        """<style>
        :root { color-scheme: light only; }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            color-scheme: light only !important;
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        </style>""",
        unsafe_allow_html=True
    )

# ────────────────────────────────────────────────
# Login gate
# ────────────────────────────────────────────────
if "auth_token" not in st.session_state:
    if "pending_token" in st.session_state:
        st.set_page_config(page_title="FairPool – Vælg adgangskode", layout="centered")
        show_set_password()
    else:
        st.set_page_config(page_title="FairPool – Log ind", layout="centered")
        show_login()
    st.stop()

# ────────────────────────────────────────────────
# Valg af Pool eller SPA ved første opstart
# ────────────────────────────────────────────────
if "service_type" not in st.session_state:
    st.session_state.service_type = None

if st.session_state.service_type is None:
    st.set_page_config(page_title="FairPool – Vælg type", layout="centered")
    force_light_mode()
    
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
    # ==================== POOL DEL ====================
    st.set_page_config(page_title="Pool Dosering", layout="wide")
    force_light_mode()
    
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
            if key not in ordered_keys and key != "Instruktioner":
                info_lines.append(f"{key}: {info[key]}")
        if info_lines:
            st.caption(" | ".join(info_lines))

        # Instruktioner (udfoldelig sektion)
        instruktioner = info.get("Instruktioner", "")
        if instruktioner and instruktioner.strip().lower() not in ("", "ikke angivet", "—"):
            with st.expander("➕ Se arbejdsinstruktioner for denne pool"):
                st.markdown(
                    f'<div style="font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap;">{instruktioner}</div>',
                    unsafe_allow_html=True
                )
    
    leased = st.radio("Husets status", ["Ikke udlejet", "Udlejet"], horizontal=True)
    colA, colB = st.columns(2)
    with colA:
        current_ph = st.number_input("Nuværende pH", min_value=0.0, value=7.0, step=0.1)
    with colB:
        current_cl = st.number_input("Nuværende frit klor (mg/l)", min_value=0.0, value=0.0, step=0.1)
    
    # KLORGAS-ADVARSEL
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
    
    target_ph = 7.0
    target_cl_leave = 4.0
    target_cl_maintenance = 5.5 if leased == "Udlejet" else 3.8
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
    force_light_mode()
    
    col_logo, _ = st.columns([1, 5])
    with col_logo:
        st.image("https://iili.io/qai6KmJ.jpg", width=180)
    
    st.title("🛁 SPA / Boblebad Service")

    # ── Generelle retningslinjer som dropdown ────────────────────────────────
    with st.expander("📋 Generelle retningslinjer – gælder alle SPA-besøg", expanded=False):
        st.markdown(
            """
            <div style="font-size: 1.05rem; color: #1a1a1a; padding: 0.2rem 0;">
            🌨️ <strong>Vinter:</strong> SPA der ikke har AKTIV frostbeskyttelse indstilles på <em>rest / range down / slp</em>
            (eller tilsvarende indstilling på den pågældende SPA), og tømmes <strong>ikke</strong> for vand.<br><br>
            💧 <strong>Vandskift:</strong> Vand skiftes hvis måling af klor og pH fordrer dette.<br><br>
            🔄 <strong>Filtre – skift/rens ALTID</strong> – også ved midtvejstjek:<br>
            &nbsp;&nbsp;&nbsp;• Sluk SPA inden filtrene tages ud (hvis muligt). Har SPA'en flere filtre, kan ét tages ud ad gangen.<br>
            &nbsp;&nbsp;&nbsp;• Udskift til nye eller rensede filtre.<br>
            &nbsp;&nbsp;&nbsp;• Alternativt renses filtrene <em>on location</em> med højtryksrenser og sættes tilbage i SPA.<br>
            &nbsp;&nbsp;&nbsp;• Eller sættes i renserør – renserør findes i skuret ved kontoret (hvis HE ikke selv har et).<br>
            &nbsp;&nbsp;&nbsp;• Filtre der i forvejen har stået i rens: spules og isættes SPA.
            </div>
            """,
            unsafe_allow_html=True
        )
    # ─────────────────────────────────────────────────────────────────────────

    spas = load_spas()
    
    if not spas:
        st.error("Ingen SPA'er fundet i Google Sheet.")
        st.stop()
    
    spa_options = [spa['display_name'] for spa in spas]
    selected_spa_display = st.selectbox("Vælg SPA fra listen", spa_options)
    
    selected_spa = next((spa for spa in spas if spa['display_name'] == selected_spa_display), None)
    
    if selected_spa:
        st.header(selected_spa.get('Adresse', 'SPA'))
        
        # Vis felter – kun hvis der er data
        fields = [
            ("ObjektNummer", selected_spa.get('ObjektNummer', '')),
            ("Model",        selected_spa.get('Model', '')),
            ("NøgleKode",    selected_spa.get('NøgleKode', '')),
            ("Styresystem",  selected_spa.get('Styresystem', '')),
            ("Liter",        selected_spa.get('Liter', '')),
        ]
        visible = [(label, val) for label, val in fields
                   if val and val.lower() not in ("", "ikke angivet", "—")]

        if visible:
            items_html = "".join(
                f'<span style="margin-right:1.8rem;"><span style="color:#888;font-size:0.78rem;">{label}</span>'
                f'&nbsp;<span style="font-size:0.92rem;font-weight:600;">{val}</span></span>'
                for label, val in visible
            )
            st.markdown(
                f'<div style="margin: 0.3rem 0 0.5rem 0; line-height: 2;">{items_html}</div>',
                unsafe_allow_html=True
            )

        # Fyldning, Fyldes, Fyldetid og Tømning
        fyldning = selected_spa.get('Fyldning', '')
        fyldes   = selected_spa.get('Fyldes', '')
        fyldetid = selected_spa.get('Fyldetid', '')
        tomning  = selected_spa.get('Tømning', '')

        import re as _re

        # Byg info-bokse som én samlet flex-række uden mellemrum
        info_items = []

        if fyldning and fyldning.lower() not in ("", "ikke angivet", "—"):
            fyldning_ren = _re.sub(r'\s*(min\.?|minutter)\s*$', '', fyldning.strip(), flags=_re.IGNORECASE)
            info_items.append(
                f'<div style="background:#f0f7ff; border-radius:8px; padding:0.7rem 1rem; flex:1; min-width:0;">'
                f'<div style="color:#888; font-size:0.75rem;">Fyldning</div>'
                f'<div style="font-size:0.95rem; font-weight:600;">💧 {fyldning_ren} minutter</div>'
                f'</div>'
            )

        if fyldes and fyldes.lower() not in ("", "ikke angivet", "—"):
            fyldes_lower = fyldes.lower()
            if "automatisk" in fyldes_lower:
                fyldes_ikon, fyldes_farve = "🤖", "#f0fff4"
            elif "kuglehane" in fyldes_lower or "semi" in fyldes_lower:
                fyldes_ikon, fyldes_farve = "🔧", "#fff8f0"
            elif "vandslange" in fyldes_lower:
                fyldes_ikon, fyldes_farve = "🪣", "#f0f7ff"
            else:
                fyldes_ikon, fyldes_farve = "💧", "#f0f7ff"
            info_items.append(
                f'<div style="background:{fyldes_farve}; border-radius:8px; padding:0.7rem 1rem; flex:1; min-width:0;">'
                f'<div style="color:#888; font-size:0.75rem;">Fyldes</div>'
                f'<div style="font-size:0.95rem; font-weight:600;">{fyldes_ikon} {fyldes}</div>'
                f'</div>'
            )

        if fyldetid and fyldetid.lower() not in ("", "ikke angivet", "—"):
            fyldetid_ren = _re.sub(r'\s*(min\.?|minutter)\s*$', '', fyldetid.strip(), flags=_re.IGNORECASE)
            info_items.append(
                f'<div style="background:#f0f7ff; border-radius:8px; padding:0.7rem 1rem; flex:1; min-width:0;">'
                f'<div style="color:#888; font-size:0.75rem;">Fyldetid</div>'
                f'<div style="font-size:0.95rem; font-weight:600;">⏱ {fyldetid_ren} minutter</div>'
                f'</div>'
            )

        if tomning and tomning.lower() not in ("", "ikke angivet", "—"):
            tomning_lower = tomning.lower()
            if "automatisk" in tomning_lower:
                ikon, farve = "🤖", "#f0fff4"
            elif "kuglehane" in tomning_lower or "semi" in tomning_lower:
                ikon, farve = "🔧", "#fff8f0"
            elif "dykpumpe" in tomning_lower or "manuel" in tomning_lower:
                ikon, farve = "🪣", "#fff0f0"
            elif "ikke" in tomning_lower or "tømmes ikke" in tomning_lower:
                ikon, farve = "🚫", "#f5f5f5"
            else:
                ikon, farve = "🔽", "#f9f9f9"
            info_items.append(
                f'<div style="background:{farve}; border-radius:8px; padding:0.7rem 1rem; flex:1; min-width:0;">'
                f'<div style="color:#888; font-size:0.75rem;">Tømning</div>'
                f'<div style="font-size:0.95rem; font-weight:600;">{ikon} {tomning}</div>'
                f'</div>'
            )

        if info_items:
            st.markdown(
                f'<div style="display:flex; flex-direction:row; gap:6px; margin-bottom:0.8rem;">'
                + "".join(info_items) +
                f'</div>',
                unsafe_allow_html=True
            )


        # Link knap
        link = selected_spa.get('Link', '')
        if link and link.lower() != "ikke angivet" and link.strip():
            if st.button("🔗 Åbn Link / Manual", type="primary"):
                st.markdown(f'<a href="{link}" target="_blank">Åbn link i ny fane</a>', unsafe_allow_html=True)

        # Billede(r)
        billede = selected_spa.get('Billede', '')
        if billede and billede.lower() not in ("", "ikke angivet", "—"):
            import re
            billede_links = [b.strip() for b in re.split(r'[,\n]+', billede) if b.strip()]
            thumbs_html = "".join(
                f'<a href="{b}" target="_blank">'
                f'<img src="{b}" style="height:160px; width:auto; border-radius:8px; '
                f'border:1px solid #ddd; cursor:pointer; margin: 0.5rem 0.5rem 1rem 0;" '
                f'title="Klik for fuld størrelse"/>'
                f'</a>'
                for b in billede_links
            )
            st.markdown(
                f'<div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin: 0.5rem 0 1rem 0;">{thumbs_html}</div>',
                unsafe_allow_html=True
            )

        # Instruktioner (udfoldelig sektion)
        instruktioner = selected_spa.get('Instruktioner', '')
        if instruktioner and instruktioner.strip().lower() not in ("", "ikke angivet", "—"):
            with st.expander("➕ Se arbejdsinstruktioner for denne SPA"):
                st.markdown(
                    f'<div style="font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap;">{instruktioner}</div>',
                    unsafe_allow_html=True
                )
        
        colA, colB = st.columns(2)
        with colA:
            ph_indtastet = st.checkbox("pH målt", value=False)
            current_ph = st.number_input("Nuværende pH", min_value=0.0, value=7.0, step=0.1, disabled=not ph_indtastet)
        with colB:
            klor_indtastet = st.checkbox("Klor målt", value=False)
            current_cl = st.number_input("Nuværende frit klor (mg/l)", min_value=0.0, value=0.0, step=0.1, disabled=not klor_indtastet)

        service_mode = st.radio(
            "Hvilken service skal udføres?",
            ["Tømme", "Fylde", "Tømme + Fylde (skift af vand)"],
            horizontal=True
        )
        
        target_ph = 7.0
        target_cl = 4.0

        if service_mode == "Tømme":
            st.markdown(
                """
                <div style="background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.05rem; color: #664d03;">
                <strong>⚠️ Husk ved tømning:</strong><br><br>
                🚽 SPA vand KUN må udledes til <strong>kloak</strong>!<br><br>
                🚰 Husk at <strong>deaktivere</strong> en evt. automatisk vandpåfyldning.<br><br>
                🔌 Husk at <strong>slukke for SPA</strong> hvis du tømmer den, hvis ikke SPA selv gør dette.<br><br>
                🪬 Husk at sætte <strong>termocover på igen</strong> inden du kører.
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            if not ph_indtastet or not klor_indtastet:
                st.info("Indtast pH og klor-måling for at se kemianbefalinger.")
            else:
                st.subheader("Anbefalet kemi ved afrejse")
                st.markdown(f"**Målværdier ved afrejse:** pH = **{target_ph}** | Frit klor = **{target_cl} mg/l**")

                try:
                    spa_liter = float(selected_spa.get('Liter', '0').replace(',', '.'))
                except (ValueError, AttributeError):
                    spa_liter = 0.0

                # pH-justering
                delta_ph = current_ph - target_ph
                if delta_ph > 0.2:
                    liter_ref = spa_liter if spa_liter > 0 else 1000.0
                    ph_trin = delta_ph / 0.1
                    spacare_ml = round(25 * ph_trin * (liter_ref / 1000))
                    saniklar_g = round(15 * ph_trin * (liter_ref / 1000))
                    st.error(
                        f"**Sænk pH med {delta_ph:.1f} – vælg ét produkt:**\n\n"
                        f"💧 **SpaCare pH Down Liquid:** ca. **{spacare_ml} ml**\n\n"
                        f"🧂 **Saniklar pH-Minus (granulat):** ca. **{saniklar_g} gram**"
                    )
                elif delta_ph < -0.2:
                    ml_ph_plus = round(25 * abs(delta_ph) * 1.5)
                    st.error(f"**Brug pH-plus:** ca. **{ml_ph_plus} ml**")
                else:
                    st.success("pH er inden for godt område")

                # Klor-justering
                delta_cl = current_cl - target_cl
                if delta_cl < -0.5:
                    if spa_liter > 0 and spa_liter > 1000:
                        sunwac_antal = max(1, round(spa_liter / 1000))
                        sunwac_navn = "SunWac 12"
                    else:
                        sunwac_antal = max(1, round((spa_liter if spa_liter > 0 else 500) / 500))
                        sunwac_navn = "SunWac 9"

                    st.error("**Hurtig opkloring (gæster samme dag):**")
                    st.markdown(f"**{sunwac_navn} (Saniklar):** {sunwac_antal} stk")

                    tab_twenty = max(2, round((spa_liter if spa_liter > 0 else 2500) / 2500) * 2)
                    st.error("**Langtids-klor (holder ca. 7 dage):**")
                    st.markdown(f"**Tab Twenty:** {tab_twenty} stk")
                    st.caption("Placer i floater eller klorinator for langsom frigivelse over 7 dage.")

                elif delta_cl > 1.5:
                    st.warning("**Klor for højt** – vent eller fortynd hvis muligt.")
                else:
                    st.success(f"Klor-niveau er godt ({current_cl:.1f} mg/l)")
                    tab_twenty = max(2, round((spa_liter if spa_liter > 0 else 2500) / 2500) * 2)
                    st.caption(f"Til vedligehold: Brug **{tab_twenty} Tab Twenty** til ca. 7 dages klor.")

            if service_mode == "Tømme + Fylde (skift af vand)":
                st.markdown(
                    """
                    <div style="background-color: #e8f4fd; border-left: 6px solid #1a73e8; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.05rem; color: #1a1a1a;">
                    <strong>🧼 Fremgangsmåde – Pipe Cleaner / Pipe Cleaner Plus</strong><br>
                    <em>(Plus anvendes til SPA over 1000 liter)</em><br><br>
                    <ol style="margin: 0; padding-left: 1.2rem; line-height: 2;">
                    <li>Fjern først filtre <strong>(vigtigt!)</strong></li>
                    <li>Hæld <strong>Pipe Cleaner / Pipe Cleaner Plus</strong> i SPA (en hel flaske) i det eksisterende vand.</li>
                    <li>Sprøjt <strong>Spa Clean Spray</strong> rundt i kanten, og lad det virke i et par minutter.</li>
                    <li>Tænd herefter alle JETS og sørg for at alle dysserne er åbne – tænd evt. for luft (kan undlades hvis SPA skummer for meget).</li>
                    <li>Brug en nu kantsvamp / børste i kanten hele vejen rundt, mens spaen kører.</li>
                    <li>Lad SPA køre til den selv slår JETS fra (typisk 20 minutter). Der vil genereres meget skum. Hvis skummet er ved at løbe over, luk for nogle af dysserne.</li>
                    <li>Når JETS stopper, skal SPA tømmes. Imens SPA tømmer, kan man med fordel spule kanterne med højtryksrenseren, således at alt skidt nedfældes.</li>
                    <li>Når SPA er tom, støvsuges restvand og skidt op.</li>
                    <li>SPA fyldes igen.</li>
                    <li>Når SPA er fuld, køres JETS igen indtil de stopper. Dette skyller systemet igennem.</li>
                    <li>Når JETS stopper, tømmes SPA og denne støvsuges og tørres efter med klud.</li>
                    <li>Isæt nye / rene filtre.</li>
                    </ol><br>
                    <strong>Spaen er nu klar til at blive fyldt, så den er klar til de nye gæster!</strong>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.markdown(
                    """
                    <div style="background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.05rem; color: #664d03;">
                    <strong>⚠️ Husk ved tømning:</strong><br><br>
                    🚽 SPA vand KUN må udledes til <strong>kloak</strong>!<br><br>
                    🚰 Husk at <strong>deaktivere</strong> en evt. automatisk vandpåfyldning.<br><br>
                    🔌 Husk at <strong>slukke for SPA</strong> hvis du tømmer den, hvis ikke SPA selv gør dette.<br><br>
                    🪬 Husk at sætte <strong>termocover på igen</strong> inden du kører.<br><br>
                    <strong>⚠️ Husk ved fyldning:</strong><br><br>
                    🔄 Husk ikke at fylde før du har isat <strong>RENE eller NYE filtre</strong>.<br><br>
                    🚰 Husk at kontrollere om <strong>afløb er lukket</strong>.<br><br>
                    ⚙️ Husk at kontrollere at <strong>SPA er korrekt indstillet</strong>.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif service_mode == "Fylde":
                st.markdown(
                    """
                    <div style="background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.05rem; color: #664d03;">
                    <strong>⚠️ Husk ved fyldning:</strong><br><br>
                    🔄 Husk ikke at fylde før du har isat <strong>RENE eller NYE filtre</strong>.<br><br>
                    🚰 Husk at kontrollere om <strong>afløb er lukket</strong>.<br><br>
                    ⚙️ Husk at kontrollere at <strong>SPA er korrekt indstillet</strong>.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ────────────────────────────────────────────────
# Sidebar – skift type (log ud håndteres i login gate ovenfor)
# ────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄 Skift mellem Pool og SPA"):
        if "service_type" in st.session_state:
            del st.session_state.service_type
        st.rerun()
    st.divider()
    if st.button("🔒 Log ud"):
        for key in ["auth_token", "auth_email", "service_type"]:
            st.session_state.pop(key, None)
        st.rerun()
