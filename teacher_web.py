import streamlit as st
import requests
import random
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="EXAMFLOW — Lærerdashbord", page_icon="🌿", layout="wide")

# Automatisk oppdatering hvert 3. sekund (3000 ms)
count = st_autorefresh(interval=3000, key="live_monitor")

# Firebase URL
FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

# Custom CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    div.stButton > button {
        background-color: #ff4b4b; color: white; font-weight: bold;
        border-radius: 8px; border: none; padding: 10px; width: 100%;
    }
    div.stButton > button:hover { background-color: #ff2b2b; color: white; }
    .alert-box {
        background-color: #4a151b;
        border: 1px solid #ff4b4b;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌿 EXAMFLOW — Lærerdashbord")

if "provekode" not in st.session_state:
    st.session_state.provekode = "EXAM-1294"

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📝 Opprett / Endre Prøve")
    
    provekode_input = st.text_input("Prøvekode", value=st.session_state.provekode)
    st.session_state.provekode = provekode_input.strip()
    
    if st.button("🎲 Generer Ny Tilfeldig Kode"):
        ny_tall = random.randint(1000, 9999)
        st.session_state.provekode = f"EXAM-{ny_tall}"
        st.rerun()

    instruksjoner = st.text_area("Oppgavetekst / Instruksjoner", value="Skriv en tekst om valgt emne...", height=180)
    
    if st.button("🚀 Publiser Prøve"):
        # Vi bruker PATCH for å ikke slette live-tekster fra elever!
        payload = {
            "prompt": instruksjoner,
            "instruction": instruksjoner,
            "instruksjoner": instruksjoner,
            "oppgave": instruksjoner,
            "active": True,
            "aktiv": True
        }
        
        r1 = requests.patch(f"{FIREBASE_URL}/exams/{st.session_state.provekode}.json", json=payload)
        r2 = requests.patch(f"{FIREBASE_URL}/proever/{st.session_state.provekode}.json", json=payload)
        
        if r1.status_code == 200 or r2.status_code == 200:
            st.success(f"✅ Prøven {st.session_state.provekode} er publisert!")
        else:
            st.error("❌ Kunne ikke lagre i Firebase.")

with col2:
    st.subheader("📊 Live Overvåking & Tekst i Sanntid")
    active_code = st.text_input("Overvåk prøvekode", value=st.session_state.provekode).strip()
    
    # Hent live-data fra Firebase
    live_data = requests.get(f"{FIREBASE_URL}/exams/{active_code}/live_texts.json").json() or {}
    alerts_data = requests.get(f"{FIREBASE_URL}/exams/{active_code}/alerts.json").json() or {}
    
    # ⚠️ Varslinger
    if alerts_data and isinstance(alerts_data, dict):
        st.warning("⚠️ REGISTRERTE HENDELSER / VARSLINGER:")
        for alert_key, alert_item in alerts_data.items():
            if isinstance(alert_item, dict):
                elev = alert_item.get("student", alert_item.get("elev", "Ukjent elev"))
                melding = alert_item.get("message", alert_item.get("melding", str(alert_item)))
                tid = alert_item.get("time", alert_item.get("tid", ""))
                st.markdown(f"<div class='alert-box'>🚨 <b>{elev}</b> [{tid}]: {melding}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-box'>🚨 {alert_item}</div>", unsafe_allow_html=True)
            
    # 📝 Live tekstvisning per elev
    if live_data and isinstance(live_data, dict):
        st.success(f"Viser live data for {len(live_data)} elev(er) (Oppdateres automatisk)")
        
        for student_name, student_content in live_data.items():
            if isinstance(student_content, dict):
                tekst = student_content.get("text", student_content.get("tekst", ""))
                ordteller = student_content.get("words", len(tekst.split()) if tekst else 0)
                status = student_content.get("status", "Aktiv")
            else:
                tekst = str(student_content)
                ordteller = len(tekst.split()) if tekst else 0
                status = "Aktiv"

            with st.expander(f"👤 **{student_name}** — {ordteller} ord | Status: `{status}`", expanded=True):
                st.text_area(f"Tekst fra {student_name}", value=tekst, height=150, key=f"text_{student_name}", disabled=True)
    else:
        st.info("Ingen live tekster registrert ennå på denne koden.")
