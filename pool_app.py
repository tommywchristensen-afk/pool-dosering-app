# Copyright © 2026 Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.
# E-mail: tommywchristensen@gmail.com
# Denne kode og det tilhørende koncept er udviklet til brug for service teknikere ansat hos Sol og Strand.
# Alle rettigheder forbeholdes. Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes
# kommercielt eller deles offentligt uden skriftlig tilladelse fra ophavsmanden.
# Copyright-teksten er fjernet fra synlig output og findes kun her som usynlig kommentar.

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

# Automatisk versionsnummer: vÅÅÅÅMMDD (sidste ændring af pool_app.py)
def get_auto_version():
    file_path = __file__  # Denne fil selv
    timestamp = os.path.getmtime(file_path)
    dt = datetime.fromtimestamp(timestamp)
    return f"v{dt.strftime('%Y%m%d')}"

VERSION = get_auto_version()

# ────────────────────────────────────────────────
# Google Sheets opsætning – DIT SHEET-ID
# ────────────────────────────────────────────────

SHEET_ID = "1J7hqPcK7rpRwrjaYAhKh5jDpk8tNYKhfM3_7FWCY2rA"
WORKSHEET_NAME = "Sheet1"  # Ændr til "Ark1" hvis dit ark hedder det på dansk

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Brug Streamlit Secrets til credentials (på cloud)
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

# Hent pools fra Sheet – med get_all_values() for at bevare ledende nuller i nøglebokskoder
def load_pools():
    values = sheet.get_all_values()
    if not values:
        return {}, {}
    
    headers = [h.strip() for h in values[0]] if values else []
    
    pools = {}
    pool_info = {}
    
    for row in values[1:]:
        if not row or not row[0].strip(): continue
        
        name = row[0].strip()
        if not name: continue
        
        vol_idx = headers.index("Volumen (m3)") if "Volumen (m3)" in headers else 1
        adresse_idx = headers.index("Adresse") if "Adresse" in headers else 2
        pumpetype_idx = headers.index("Pumpetype") if "Pumpetype" in headers else 3
        returskyl_idx = headers.index("Returskyl (5 min)") if "Returskyl (5 min)" in headers else 4
        nøglebokskode_idx = headers.index("Nøglebokskode") if "Nøglebokskode" in headers else 5
        he_idx = headers.index("HE telefonnummer") if "HE telefonnummer" in headers else 6
        
        vol_str = row[vol_idx] if vol_idx < len(row) else "0"
        try:
            vol = float(vol_str)
        except (ValueError, TypeError):
            vol = 0.0
        
        pools[name] = vol
        
        extra = {}
        if adresse_idx < len(row): extra["Adresse"] = row[adresse_idx] or "Ikke angivet"
        if pumpetype_idx < len(row): extra["Pumpetype"] = row[pumpetype_idx] or "Ikke angivet"
        if returskyl_idx < len(row) and row[returskyl_idx]:
            try:
                liter = float(row[returskyl_idx])
                kubik = liter / 1000
                extra["Returskyl (5 min)"] = f"{int(liter)} liter / {kubik:.1f} m³"
            except ValueError:
                extra["Returskyl (5 min)"] = row[returskyl_idx]
        else:
            extra["Returskyl (5 min)"] = "Ikke angivet"
        if nøglebokskode_idx < len(row): extra["Nøglebokskode"] = row[nøglebokskode_idx] or "Ikke angivet"
        if he_idx < len(row): extra["HE telefonnummer"] = row[he_idx] or "Ikke angivet"
        
        pool_info[name] = extra
    
    return pools, pool_info

pools, pool_info = load_pools()

# Tilføj ny pool til Sheet – rettet rækkefølge
def add_pool(name, vol):
    sheet.append_row([name, vol, "", name, "", "", ""])

st.set_page_config(page_title="Pool Dosering", layout="wide")

st.title("Pool Dosering - HTH Briquetter & Tempo Sticks")

# Pool valg – øverst
st.header("Pool")
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

# Foldbar tilføjelse af ny pool – under vælgeren
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

# Stor header med pool-navn og volumen (kun her)
st.header(f"{selected} - {volume:.1f} m³")

# Vis ekstra info under headeren – med fast rækkefølge
ordered_keys = ["Adresse", "Nøglebokskode", "HE telefonnummer", "Pumpetype", "Returskyl (5 min)"]
info_lines = []
for key in ordered_keys:
    if key in info:
        info_lines.append(f"{key}: {info[key]}")
for key in info:
    if key not in ordered_keys:
        info_lines.append(f"{key}: {info[key]}")
if info_lines:
    st.caption(" | ".join(info_lines))

# Husets status – før målinger
leased = st.radio("Husets status", ["Ikke udlejet", "Udlejet"], horizontal=True)

# Målinger
colA, colB = st.columns(2)
with colA:
    current_ph = st.number_input("Nuværende pH", min_value=0.0, value=7.0, step=0.1)
with colB:
    current_cl = st.number_input("Nuværende frit klor (mg/l)", min_value=0.0, value=0.0, step=0.1)

# Advarsel om klorgas – kun ved pH 4.0–6.9 + opkloring (gul), under 4.0 (rød/alvorlig)
delta_cl_leave = max(0, 4.0 - current_cl)  # Mål 4.0 mg/l
if delta_cl_leave > 0:
    if current_ph < 4.0:
        st.error(
            "**ALVORLIG ADVARSEL: EKSTREMT LAV pH + KLOR-TILSÆTNING!**\n\n"
            "Risiko for frigivelse af **farlig klorgas** er meget høj!\n\n"
            "- STOP! Mål pH igen og hæv den til mindst 7.0 FØR du tilsætter klor.\n"
            "- Brug aldrig klor og pH-minus samtidig.\n"
            "- Opløs klor i spand vand, tilsæt langsomt, sørg for god cirkulation og frisk luft.\n"
            "- Forlad området hvis du mærker lugt af klor eller åndedrætsbesvær.\n"
            "- Kontakt giftlinjen ved symptomer!"
        )
    elif 4.0 <= current_ph <= 6.9:
        st.warning(
            "**Advarsel: Lav pH + klor-tilsætning kan frigive klorgas!**\n\n"
            "- Sørg for pH er mindst 7.0 før du tilsætter klor.\n"
            "- Opløs klor i spand vand først, tilsæt langsomt ud for dyserne.\n"
            "- Sørg for god cirkulation og frisk luft i poolhuset.\n"
            "- Mål igen efter 30–60 minutter."
        )

# Checkbox og selectbox
has_existing_stick = st.checkbox("**Der ligger allerede en Tempo Stick i skimmer/klorinator**", value=False)

# Vejledning lige efter checkbox
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

# Vejledningstekst under checkbox/selectbox
st.markdown(
    """
    <div style="font-size: 1.05rem; color: #444; margin-bottom: 0.8rem;">
    <strong>Vigtigt om Tempo Sticks:</strong><br>
    - Tempo Sticks skal altid placeres i KLORINATOREN eller i SKIMMEREN via en Tempo Stick Dispenser - aldrig direkte i skimmeren eller poolen!
    </div>
    """,
    unsafe_allow_html=True
)

target_ph = 7.0
target_cl_leave = 4.0
target_cl_maintenance = 5.5 if leased == "Udlejet" else 3.8

delta_ph = current_ph - target_ph

delta_cl_leave = max(0, target_cl_leave - current_cl)

# Beregn nyt klor-niveau EFTER opkloring med Briquetter
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
            sticks_needed = max(1, round(sticks_needed)) # Mindst 1 stick
            ph_rise_from_sticks = 0.4 * sticks_needed * (25.0 / volume)
        else:
            sticks_needed = 1 # Mindst 1 stick selv hvis delta er 0
            ph_rise_from_sticks = 0.4 * sticks_needed * (25.0 / volume)
    else:
        sticks_needed = 0

# Forventet pH-stigning fra Briquetter/Daytabs (ca. 0.15 per stk ved 25 m³)
ph_rise_from_briqs = 0.0
if delta_cl_leave > 0:
    briqs = 0.21 * delta_cl_leave * volume
    ph_rise_from_briqs = 0.15 * briqs * (25.0 / volume)  # tilnærmelse

# Samlet forventet pH-stigning fra klor-tilsætning
total_ph_rise_from_klor = ph_rise_from_briqs + ph_rise_from_sticks

# Justeret delta_ph efter klor-tilsætning
adjusted_delta_ph = delta_ph - total_ph_rise_from_klor

# PH-justering – ALTID reguler til 7.0 hvis PH før eller efter klor er over 7.0
if current_ph > 7.0 or adjusted_delta_ph > 0:
    # PH er over eller bliver over 7.0 – sænk med pH-minus (mere hvis klor hæver yderligere)
    ml_minus = 35 * max(adjusted_delta_ph, current_ph - target_ph) * volume
    st.subheader(f"Sænk pH med {max(adjusted_delta_ph, current_ph - target_ph):.2f} (efter klor)")
    st.markdown(f"**pH-minus → {ml_minus:.0f} ml**")
elif current_ph < 7.0 and adjusted_delta_ph < 0:
    # PH er under 7.0 og klor hæver ikke nok til at komme over – hæv med pH-plus
    ml_plus = 49 * (-adjusted_delta_ph) * volume
    st.subheader(f"Hæv pH med {-adjusted_delta_ph:.2f} (efter klor)")
    st.markdown(f"**pH-plus → {ml_plus:.0f} ml**")
else:
    # PH er på eller tæt på 7.0 – ingen justering
    st.success("pH er på eller tæt på målet efter klor – ingen PH-justering nødvendig")

delta_ph_eff = adjusted_delta_ph

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

# Ingen synlig copyright i bunden – kun versionsnummer
st.markdown(
    f"""
    <div style="font-size: 0.85rem; color: #555; text-align: center; margin-top: 2rem; padding: 1rem;">
    Version: {VERSION}
    </div>
    """,
    unsafe_allow_html=True
)
