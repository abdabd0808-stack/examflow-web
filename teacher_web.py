import streamlit as st
import requests
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

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📝 Opprett / Endre Prøve")
    provekode = st.text_input("Prøvekode", value="EXAM-1935")
    instruksjoner = st.text_area("Oppgavetekst / Instruksjoner", value="Skriv 1000 ord om dette...", height=180)
    
    if st.button("🚀 Publiser Prøve"):
        payload = {
            "instruction": instruksjoner,
            "instruksjoner": instruksjoner,
            "active": True,
            "aktiv": True
        }
        r1 = requests.put(f"{FIREBASE_URL}/exams/{provekode}.json", json=payload)
        r2 = requests.put(f"{FIREBASE_URL}/proever/{provekode}.json", json=payload)
        
        if r1.status_code == 200 or r2.status_code == 200:
            st.success(f"Prøven {provekode} er publisert!")
        else:
            st.error("Kunne ikke lagre i Firebase.")

with col2:
    st.subheader("📊 Live Overvåking & Tekst i Sanntid")
    active_code = st.text_input("Sjekk prøvekode", value="EXAM-1935")
    
    # Hent levende tekster, innkoblede elever og varsler fra Firebase
    live_data = requests.get(f"{FIREBASE_URL}/exams/{active_code}/live_texts.json").json() or {}
    alerts_data = requests.get(f"{FIREBASE_URL}/exams/{active_code}/alerts.json").json() or {}
    
    # ⚠️ Varslinger (f.eks. ved mistenkelig oppførsel / tab-switching)
    if alerts_data and isinstance(alerts_data, dict):
        st.error("⚠️ ADVARSEL / VARSLINGER REGISTRERT:")
        for student, alert_msg in alerts_data.items():
            st.markdown(f"<div class='alert-box'>🚨 <b>{student}</b>: {alert_msg}</div>", unsafe_allow_html=True)
            
    # 📝 Live tekstvisning per elev
    if live_data and isinstance(live_data, dict):
        st.success(f"Viser live data for {len(live_data)} elev(er) (Oppdateres hvert 3. sek)")
        
        for student_name, student_content in live_data.items():
            # Hent teksten eller objektet
            if isinstance(student_content, dict):
                tekst = student_content.get("text", student_content.get("tekst", ""))
                ordteller = student_content.get("words", len(tekst.split()))
                status = student_content.get("status", "Aktiv")
            else:
                tekst = str(student_content)
                ordteller = len(tekst.split())
                status = "Aktiv"

            with st.expander(f"👤 **{student_name}** — {ordteller} ord | Status: `{status}`", expanded=True):
                st.text_area(f"Tekst fra {student_name}", value=tekst, height=150, key=f"text_{student_name}", disabled=True)
    else:
        st.info("Ingen live tekster registrert ennå. Vent til eleven begynner å skrive...")
