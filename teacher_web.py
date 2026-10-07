import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(page_title="EXAMFLOW — Lærer Dashbord", layout="wide")

FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

st.title("🌿 EXAMFLOW — Lærer Dashbord")
st.write("Overvåk prøver, se elevstatus og skriveprogresjon i realtid.")

exam_code = st.text_input("ENTER PRØVEKODE (f.eks. EXAM-4821)", "").strip().upper()

if exam_code:
    # Hent data fra Firebase
    res = requests.get(f"{FIREBASE_URL}/exams/{exam_code}.json")
    exam_data = res.json() if res.status_code == 200 else None

    if not exam_data:
        st.error(f"Fant ingen prøve med kode '{exam_code}'.")
    else:
        col1, col2 = st.columns([1, 2])

        # --- VENSTRE KOLONNE: ELEVER OG VARSLER ---
        with col1:
            st.subheader("👥 Påloggede Elever")
            students = exam_data.get("students_joined", {})
            
            if students:
                student_list = list(students.keys())
                selected_student_raw = st.selectbox("Velg elev:", student_list, format_func=lambda x: x.replace("_", " "))
            else:
                st.info("Ingen elever tilkoblet ennå.")
                selected_student_raw = None

            st.subheader("🔔 Hendelser / Varsler")
            alerts = exam_data.get("alerts", {})
            if alerts:
                for alert_id, alert in reversed(list(alerts.items())):
                    st.caption(f"**{alert.get('time', '')} - {alert.get('student', '')}:** {alert.get('message', '')}")
            else:
                st.write("Ingen varsler ennå.")

        # --- HØYRE KOLONNE: LIVE-TEKST OG GRAF ---
        with col2:
            if selected_student_raw:
                display_name = selected_student_raw.replace("_", " ")
                st.subheader(f"📝 Live-tekst for {display_name}")

                live_info = exam_data.get("live_texts", {}).get(selected_student_raw, {})
                current_text = live_info.get("text", "Ingen tekst registrert...")
                word_count = live_info.get("words", 0)

                st.metric("Antall ord nå", word_count)
                st.text_area("Elevens besvarelse", value=current_text, height=200, disabled=True)

                st.subheader("📈 Skriveprogresjon (Ord over tid)")
                history = live_info.get("history", {})

                if history:
                    df_data = []
                    for h in history.values():
                        df_data.append({"Tid": h.get("time"), "Ord": h.get("words")})
                    
                    df = pd.DataFrame(df_data)
                    st.line_chart(df.set_index("Tid"))
                else:
                    st.info("Ingen historikk registrert for denne eleven ennå.")
            else:
                st.info("Velg en elev fra menyen til venstre.")

        # Automatisk oppdatering hvert 5. sekund
        time.sleep(5)
        st.rerun()
