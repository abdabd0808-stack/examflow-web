import streamlit as st
import requests
import json

st.set_page_config(page_title="EXAMFLOW", page_icon="🌿", layout="wide")

# Firebase URL
FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

st.title("🌿 EXAMFLOW — Lærerdashbord")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Opprett Ny Prøve")
    provekode = st.text_input("Prøvekode", value="EXAM-1935")
    instruksjoner = st.text_area("Oppgavetekst", value="Skriv 1000 ord om dette...")
    
    if st.button("🚀 Publiser Prøve"):
        payload = {
            "instruksjoner": instruksjoner,
            "aktiv": True
        }
        # Vi lagrer både i /proever/ og /exams/ så elev-appen finner den uansett!
        r1 = requests.put(f"{FIREBASE_URL}/proever/{provekode}.json", data=json.dumps(payload))
        r2 = requests.put(f"{FIREBASE_URL}/exams/{provekode}.json", data=json.dumps(payload))
        
        if r1.status_code == 200:
            st.success(f"Prøven {provekode} er nå publisert!")
        else:
            st.error("Feil ved lagring.")

with col2:
    st.subheader("📊 Elever")
    if st.button("🔄 Oppdater elevliste"):
        res = requests.get(f"{FIREBASE_URL}/proever/{provekode}/elever.json")
        st.write(res.json())
