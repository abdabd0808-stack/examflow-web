import streamlit as st
import requests
import json

# Konfigurer siden
st.set_page_config(
    page_title="EXAMFLOW — Lærerdashbord",
    page_icon="🌿",
    layout="wide"
)

# Firebase Realtime Database URL
FIREBASE_URL = "https://exam-flow-default-rtdb.europe-west1.firebasedatabase.app"

# Custom CSS for design og farger
st.markdown("""
    <style>
    /* Bakgrunn og hovedstil */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* Styling for knapper */
    div.stButton > button {
        background-color: #ff4b4b;
        color: white;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #ff2b2b;
        border: none;
        color: white;
        transform: scale(1.01);
    }

    /* Styling for informasjonsbokser */
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Tittel
st.title("🌿 EXAMFLOW — Lærerdashbord")
st.write("Administrer prøver og overvåk elever i sanntid fra skyen.")

st.divider()

# Hovedoppsett med to kolonner
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📝 Opprett Ny Prøve")
    
    provekode = st.text_input("Prøvekode", value="EXAM-1935")
    instruksjoner = st.text_area(
        "Oppgavetekst / Instruksjoner", 
        height=200, 
        placeholder="Skriv inn oppgaveteksten her..."
    )
    
    if st.button("🚀 Publiser Prøve til Skyen"):
        if provekode and instruksjoner:
            # Send data til Firebase
            payload = {
                "instruksjoner": instruksjoner,
                "aktiv": True
            }
            try:
                response = requests.put(
                    f"{FIREBASE_URL}/proever/{provekode}.json", 
                    data=json.dumps(payload)
                )
                if response.status_code == 200:
                    st.success(f"Prøven '{provekode}' er nå publisert og aktiv i skyen!")
                else:
                    st.error("Kunne ikke publisere prøven. Sjekk Firebase-tilkoblingen.")
            except Exception as e:
                st.error(f"Feil ved tilkobling til Firebase: {e}")
        else:
            st.warning("Vennligst fyll ut både prøvekode og oppgavetekst.")

with col2:
    st.subheader("📊 Live Overvåking & Elever")
    
    active_code = st.text_input("Skriv inn prøvekode for å overvåke", value="EXAM-1935")
    
    if st.button("🔄 Hent status / Oppdater"):
        try:
            res = requests.get(f"{FIREBASE_URL}/proever/{active_code}/elever.json")
            elever = res.json()
            
            if elever:
                st.success(f"Funnet data for prøve: {active_code}")
                for elev_id, elev_data in elever.items():
                    navn = elev_data.get("navn", elev_id)
                    status = elev_data.get("status", "Ukjent")
                    sist_sett = elev_data.get("sist_sett", "Ikke registrert")
                    
                    st.write(f"👤 **{navn}** — Status: `{status}` (Sist aktiv: {sist_sett})")
            else:
                st.info("Ingen elever har koblet seg til denne prøven ennå.")
        except Exception as e:
            st.error(f"Feil ved henting av elevdata: {e}")

st.divider()
st.caption("ExamFlow SaaS © 2026 — Sikker prøvegjennomføring i skolen")
