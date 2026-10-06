import streamlit as st
import requests
import json

st.set_page_config(page_title="EXAMFLOW — Lærerdashbord", page_icon="🌿", layout="wide")

# Firebase URL
FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

# Custom CSS for fint design
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    div.stButton > button {
        background-color: #ff4b4b; color: white; font-weight: bold;
        border-radius: 8px; border: none; padding: 10px; width: 100%;
    }
    div.stButton > button:hover { background-color: #ff2b2b; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🌿 EXAMFLOW — Lærerdashbord")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📝 Opprett Ny Prøve")
    provekode = st.text_input("Prøvekode", value="EXAM-1935")
    instruksjoner = st.text_area("Oppgavetekst / Instruksjoner", value="Skriv 1000 ord om dette...", height=200)
    
    if st.button("🚀 Publiser Prøve"):
        # Vi sender BÅDE "instruction" og "instruksjoner" så elev-appen garantert finner teksten!
        payload = {
            "instruction": instruksjoner,
            "instruksjoner": instruksjoner,
            "active": True,
            "aktiv": True
        }
        
        # Lagrer i både /exams/ og /proever/
        r1 = requests.put(f"{FIREBASE_URL}/exams/{provekode}.json", data=json.dumps(payload))
        r2 = requests.put(f"{FIREBASE_URL}/proever/{provekode}.json", data=json.dumps(payload))
        
        if r1.status_code == 200 or r2.status_code == 200:
            st.success(f"Prøven {provekode} er publisert!")
        else:
            st.error("Kunne ikke lagre i Firebase.")

with col2:
    st.subheader("📊 Live Elever & Overvåking")
    active_code = st.text_input("Sjekk prøvekode", value="EXAM-1935")
    
    if st.button("🔄 Oppdater elevliste"):
        # Sjekker både students_joined, live_texts og elever
        res_joined = requests.get(f"{FIREBASE_URL}/exams/{active_code}/students_joined.json").json()
        res_live = requests.get(f"{FIREBASE_URL}/exams/{active_code}/live_texts.json").json()
        
        elever = res_joined or res_live
        
        if elever and isinstance(elever, dict):
            st.success(f"Funnet {len(elever)} elev(er):")
            for elev_navn, elev_data in elever.items():
                st.write(f"👤 **{elev_navn}** — Tilkoblet og aktiv")
        else:
            st.info("Ingen elever har koblet seg til ennå.")
