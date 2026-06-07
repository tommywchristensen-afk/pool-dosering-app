# Copyright © 2026 FairPool v/Tommy Christensen, Laur Larsensgade 13, STTH, 4800 Nykøbing F.
# E-mail: info@fairpool.dk
# Denne app og dens underliggende kode/koncept er udviklet af FairPool v/Tommy Christensen.
# Alle rettigheder forbeholdes FairPool v/Tommy Christensen.
# Service Teknikere ansat hos Sol og Strand har tilladelse til at bruge appen uden beregning i forbindelse med deres arbejde.
# Må ikke kopieres, distribueres, modificeres, sælges eller på anden måde anvendes kommercielt eller deles offentligt
# uden skriftlig tilladelse fra FairPool v/Tommy Christensen.

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ────────────────────────────────────────────────
# Google Sheets opsætning
# ────────────────────────────────────────────────
POOL_SHEET_ID = "1J7hqPcK7rpRwrjaYAhKh5jDpk8tNYKhfM3_7FWCY2rA"
POOL_WORKSHEET_NAME = "Sheet1"

SPA_SHEET_ID = "16PLyJjec6WX-6Z5SQD1B_tl8qZYObKRx5Nt9ZRBHgRU"
SPA_WORKSHEET_NAME = "Sheet1"

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
# Valg af Pool eller SPA ved første opstart
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
    # ==================== POOL DEL ====================
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
    
    leased =
