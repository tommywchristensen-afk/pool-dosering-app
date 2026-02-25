# Copyright © 2026 Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.
# E-mail: tommywchristensen@gmail.com
# Denne kode og det tilhørende koncept er udviklet til brug for service-teknikere ansat hos Sol og Strand.
# Alle rettigheder forbeholdes. Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes
# kommercielt eller deles offentligt uden skriftlig tilladelse fra ophavsmanden.

import streamlit as st
import json
import os

POOL_FILE = "pools.json"

if os.path.exists(POOL_FILE):
    with open(POOL_FILE, "r", encoding="utf-8") as f:
        pools = json.load(f)
else:
    pools = {}

def save_pools():
    with open(POOL_FILE, "w", encoding="utf-8") as f:
        json.dump(pools, f, ensure_ascii=False, indent=2)

st.set_page_config(page_title="Pool Dosering", layout="wide")

st.title("Pool Dosering - HTH Briquetter & Tempo Sticks")

# Pool valg / tilføj
st.header("Pool")
col1, col2, col3 = st.columns([3, 2, 1.5])
with col1:
    new_name = st.text_input("Nyt pool-navn", key="new_pool_name")
with col2:
    new_vol = st.number_input("Volumen (m³)", min_value=5.0, value=45.0, step=1.0, key="new_vol")
with col3:
    if st.button("Tilføj", use_container_width=True):
        if new_name.strip():
            pools[new_name.strip()] = new_vol
            save_pools()
            st.success(f"{new_name.strip()} tilføjet")
            st.rerun()

pool_list = list(pools.keys())
if pool_list:
    selected = st.selectbox("Vælg pool", pool_list)
    volume = pools[selected]
else:
    st.info("Tilføj en pool først")
    st.stop()

st.header(f"{selected} - {volume:.1f} m³")

colA, colB = st.columns(2)
with colA:
    current_ph = st.number_input("Nuværende pH", 0.0, 14.0, 7.5, 0.1)
with colB:
    current_cl = st.number_input("Nuværende frit klor (mg/l)", 0.0, 20.0, 1.5, 0.1)

st.markdown(
    """
    <div style="font-size: 1.05rem; color: #444; margin-bottom: 0.8rem;">
    <strong>Vigtigt om Tempo Sticks:</strong><br>
    - Vælg kun feltet hvis der er mindst 0.5 stick tilbage<br>
    - Tempo Sticks skal altid placeres i KLORINATOREN eller i SKIMMEREN via en Tempo Stick Dispenser - aldrig direkte i skimmeren eller poolen!<br>
    - Ved eksisterende sticks skal du vælge 1 eller 2
    </div>
    """
)

has_existing_stick = st.checkbox("Der ligger allerede Tempo Stick(s) i poolen (min. 0.5 stick tilbage)", value=False)

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

leased = st.radio("Husets status", ["Ikke udlejet", "Udlejet"], horizontal=True)

target_ph = 7.0
target_cl_leave = 4.0
target_cl_maintenance = 5.5 if leased == "Udlejet" else 3.8

delta_ph = current_ph - target_ph
delta_cl_leave = max(0, target_cl_leave - current_cl)

delta_cl_maint = 0.0
if not has_existing_stick and leased == "Udlejet":
    delta_cl_maint = max(0, target_cl_maintenance - current_cl)

ph_rise_from_sticks = 0.0
sticks_needed = 0.0

if delta_cl_maint > 0:
    klor_per_stick_25m3 = 8.0
    raise_here = klor_per_stick_25m3 * (25.0 / volume)
    sticks_needed = delta_cl_maint / raise_here
    sticks_needed = round(sticks_needed)
    ph_rise_from_sticks = 0.4 * sticks_needed * (25.0 / volume)

delta_ph_eff = delta_ph + ph_rise_from_sticks

st.markdown(
    """
    <div style="background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 1.2rem; margin: 1rem 0; border-radius: 6px; font-size: 1.15rem; color: #664d03;">
    <strong>GØR DETTE FØRST - trin for trin</strong><br><br>
    1. Juster pH først (opløs Saniklar PH Minus i en spand med poolvand og tilsæt blandingen langsomt, gerne ud for dyserne)<br>
    2. Tilsæt HTH Briquetter/Daytabs hvis nødvendigt for at nå ~4 mg/l ved afgang fra poolhus.<br>
    3. Tilsæt Tempo Sticks i KLORINATOREN eller SKIMMERKURVEN via en Tempo Stick Dispenser (kun hvis der ingen Tempo Sticks er i forvejen og huset er udlejet)
    </div>
    """,
    unsafe_allow_html=True
)

st.header("Anbefalet dosering")

if abs(delta_ph_eff) < 0.05:
    st.success("pH ser fin ud - ingen justering nødvendig")
elif delta_ph_eff > 0:
    ml_minus = 35 * delta_ph_eff * volume
    st.subheader(f"Sænk pH med {delta_ph_eff:.2f}")
    st.markdown(f"**pH-minus → {ml_minus:.0f} ml**")
else:
    ml_plus = 49 * (-delta_ph_eff) * volume
    st.subheader(f"Hæv pH med {-delta_ph_eff:.2f}")
    st.markdown(f"**pH-plus → {ml_plus:.0f} ml**")

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
        
        st.subheader(f"Opkloring til {target_cl_leave} mg/l ved afgang")
        st.markdown(f"**HTH Briquetter/Daytabs: {briqs:.1f} stk → afrund til {briqs_round} stk**")
        st.caption(f"→ doserer klor fra {current_cl:.1f} mg/l til {new_cl:.1f} mg/l")

st.subheader("Vedligehold - Tempo Sticks (5-7 dage)")

if has_existing_stick and existing_sticks is None:
    st.markdown(
        """
        <div style="background-color: #ffebee; color: #b71c1c; padding: 1rem; border-radius: 6px; margin: 1rem 0; border: 1px solid #ef9a9a;">
        <strong>Fejl:</strong> Du skal vælge 1 eller 2 eksisterende Tempo Sticks for at fortsætte.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.info("Vedligeholdelsesforslag vises først når antal eksisterende sticks er valgt.")
else:
    if has_existing_stick:
        st.info(f"Der ligger allerede {existing_sticks} stk → ingen nye sticks foreslået")
    elif leased == "Ikke udlejet":
        st.info("Huset er ikke udlejet → ingen Tempo Sticks - kun Briquetter/Daytabs til 3-4 mg/l")
    elif sticks_needed == 0:
        st.info("Ingen nye Tempo Sticks nødvendige")
    else:
        added_cl = sticks_needed * 8.0 * (25.0 / volume)
        st.markdown(f"**HTH Tempo Sticks: {sticks_needed:.0f} stk**")
        st.caption(f"→ giver ca. +{added_cl:.1f} mg/l klor og +{ph_rise_from_sticks:.2f} pH-stigning")
        st.caption("Tempo Sticks skal altid placeres i KLORINATOREN eller i SKIMMEREN via en Tempo Stick Dispenser - aldrig direkte i skimmeren eller poolen!")

# Copyright i bunden
st.markdown(
    """
    <div style="font-size: 0.85rem; color: #555; text-align: center; margin-top: 2rem; padding: 1rem; border-top: 1px solid #ddd; background-color: #f5f5f5;">
    © 2026 Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.<br>
    E-mail: tommywchristensen@gmail.com<br>
    Denne applikation og dens koncept er udviklet til brug for service-teknikere ansat hos Sol og Strand.<br>
    Alle rettigheder forbeholdes. Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes<br>
    kommercielt eller deles offentligt uden skriftlig tilladelse fra ophavsmanden.
    </div>
    """,
    unsafe_allow_html=True
)