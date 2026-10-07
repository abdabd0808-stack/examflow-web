import streamlit as st
import requests
import pandas as pd
import random
import io
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="EXAMFLOW — Lærer Dashbord", 
    layout="wide", 
    page_icon="🌿"
)

FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

# --- SESSION STATE FOR PRØVEKODE ---
if "current_exam_code" not in st.session_state:
    st.session_state["current_exam_code"] = "EXAM-5114"

# --- TITTEL OG HEADER ---
st.title("🌿 EXAMFLOW — Lærer Dashbord")
st.write("Administrer prøver, overvåk elever i realtid, se skriveprogresjon og last ned leverte besvarelser.")

# --- FANER (TABS) ---
tabs = st.tabs([
    "📊 Live Overvåking & Graf", 
    "📥 Leverte Besvarelser", 
    "➕ Opprett Ny Prøve"
])

# ==============================================================================
# TAB 1: LIVE OVERVÅKING & GRAF
# ==============================================================================
with tabs[0]:
    st.subheader("🔍 Sanntidsovervåking av Prøverom")
    
    # Input og knapp for å generere tilfeldig kode
    col_input, col_btn = st.columns([3, 1])

    with col_input:
        exam_code = st.text_input(
            "Overvåk prøvekode", 
            value=st.session_state["current_exam_code"],
            key="exam_code_input",
            placeholder="f.eks. EXAM-5114"
        ).strip().upper()

    with col_btn:
        st.write("")  # Lufting for vertikal flukting
        st.write("") 
        if st.button("🎲 Generer Ny Kode", use_container_width=True):
            new_random_code = f"EXAM-{random.randint(1000, 9999)}"
            st.session_state["current_exam_code"] = new_random_code
            st.rerun()

    # Hent sanntidsdata fra Firebase
    if exam_code:
        res = requests.get(f"{FIREBASE_URL}/exams/{exam_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error(f"Fant ingen prøve med kode '{exam_code}'. Sjekk koden eller opprett den under 'Opprett Ny Prøve'.")
        else:
            # Vis oppgavetekst hvis registrert
            prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or exam_data.get("oppgave") or ""
            if prompt_text:
                st.info(f"📌 **Oppgavetekst for {exam_code}:**\n\n_{prompt_text}_")

            st.divider()

            # 1. HENDELSER OG VARSLINGER (Original farge/stil)
            st.warning("⚠️ REGISTRERTE HENDELSER / VARSLINGER:")
            alerts = exam_data.get("alerts", {})
            if alerts:
                for alert_id, alert in reversed(list(alerts.items())):
                    st.error(f"🚨 **{alert.get('student', '')}** [{alert.get('time', '')}]: {alert.get('message', '')}")
            else:
                st.caption("Ingen spesielle hendelser eller juks-varsler registrert ennå.")

            st.divider()

            # 2. ELEVSTATUS OG LIVE-TEKST
            students = exam_data.get("students_joined", {})
            live_texts = exam_data.get("live_texts", {})

            if students:
                st.success(f"Viser live data for {len(students)} elev(er) (Oppdateres automatisk)")

                for student_key in students.keys():
                    display_name = student_key.replace("_", " ")
                    student_info = live_texts.get(student_key, {})
                    text_content = student_info.get("text", "")
                    word_count = student_info.get("words", len(text_content.split()))
                    history = student_info.get("history", {})

                    # Ekspendert elevkort med full oversikt og design
                    with st.expander(f"👤 {display_name} — {word_count} ord | Status: Aktiv", expanded=True):
                        st.caption(f"Tekst fra {display_name}")
                        st.text_area(
                            f"Tekstvisning_{student_key}", 
                            value=text_content if text_content else "Eleven har ikke begynte å skrive ennå...", 
                            height=200, 
                            disabled=True, 
                            label_visibility="collapsed"
                        )
                        
                        # 📈 GRAF OVER SKRIVEPROGRESJON (ORD OVER TID)
                        st.markdown("#### 📈 Skriveprogresjon (Ord over tid)")
                        if history:
                            df_data = []
                            for h in history.values():
                                df_data.append({
                                    "Klokkeslett": h.get("time"), 
                                    "Antall ord": h.get("words")
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.line_chart(df.set_index("Klokkeslett"))
                        else:
                            st.caption("📈 Grafen vil oppdatere seg automatisk så snart eleven har skrevet i mer enn 30 sekunder.")

                        # Hurtignedlasting av utkast
                        download_content = f"UTKAST / LIVE-TEKST — {exam_code}\nElev: {display_name}\nOrdantall: {word_count}\n-----------------------------------\n\n{text_content}"
                        st.download_button(
                            label=f"💾 Last ned live-utkast for {display_name} (.txt)",
                            data=download_content,
                            file_name=f"LiveUtkast_{display_name.replace(' ', '_')}_{exam_code}.txt",
                            mime="text/plain",
                            key=f"dl_live_{student_key}"
                        )
            else:
                st.info("Ingen elever har koblet seg til denne prøvekoden ennå.")


# ==============================================================================
# TAB 2: LEVERTE BESVARELSER
# ==============================================================================
with tabs[1]:
    st.subheader("📥 Oversikt over leverte besvarelser")
    sub_exam_code = st.text_input("Skriv inn prøvekode for å hente leverte besvarelser", key="sub_code_input").strip().upper()

    if sub_exam_code:
        res = requests.get(f"{FIREBASE_URL}/exams/{sub_exam_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error(f"Fant ikke prøven med kode '{sub_exam_code}'.")
        else:
            submissions = exam_data.get("submissions", {})
            times = exam_data.get("submission_times", {})
            prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or ""

            if not submissions:
                st.warning("Ingen elever har levert inn besvarelsen sin på denne prøvekoden ennå.")
            else:
                st.success(f"Totalt {len(submissions)} levert(e) besvarelse(r) funnet!")
                
                for student_key, sub_text in submissions.items():
                    student_display = student_key.replace("_", " ")
                    sub_time = times.get(student_key, "Ukjent tidspunkt")
                    word_count = len(sub_text.split())

                    with st.expander(f"📄 {student_display} — Levert kl. {sub_time} ({word_count} ord)"):
                        st.markdown(f"**Elev:** {student_display}  \n**Levert tidspunkt:** {sub_time}  \n**Antall ord:** {word_count}")
                        
                        st.text_area(
                            f"Leveringstekst_{student_key}", 
                            value=sub_text, 
                            height=300, 
                            disabled=True
                        )

                        # Formatert tekstfil for nedlasting
                        full_export = (
                            f"===================================================\n"
                            f"OFFISIELL EKSAMENSBESVARELSE — {sub_exam_code}\n"
                            f"===================================================\n"
                            f"Elev:            {student_display}\n"
                            f"Prøvekode:       {sub_exam_code}\n"
                            f"Leveringstid:    {sub_time}\n"
                            f"Antall ord:      {word_count}\n"
                            f"---------------------------------------------------\n"
                            f"OPPGAVETEKST:\n{prompt_text}\n"
                            f"---------------------------------------------------\n\n"
                            f"BESVARELSE:\n\n{sub_text}\n"
                        )

                        st.download_button(
                            label=f"📄 Last ned besvarelse for {student_display} (.txt)",
                            data=full_export,
                            file_name=f"Levert_{student_display.replace(' ', '_')}_{sub_exam_code}.txt",
                            mime="text/plain",
                            key=f"dl_sub_{student_key}"
                        )


# ==============================================================================
# TAB 3: OPPRETT NY PRØVE
# ==============================================================================
with tabs[2]:
    st.subheader("➕ Opprett en ny prøve i skyen")
    st.write("Her kan du opprette nye prøvekoder og legge inn oppgavetekst som elev-appen henter automatisk.")

    col_create1, col_create2 = st.columns([2, 1])

    with col_create1:
        new_code = st.text_input("NY PRØVEKODE (f.eks. EXAM-8842)", value=f"EXAM-{random.randint(1000, 9999)}").strip().upper()
    
    with col_create2:
        st.write("")
        st.write("")
        if st.button("🎲 Generer Ny Kode for skjema"):
            st.rerun()

    new_prompt = st.text_area("OPPGAVETEKST / INSTRUKSJON TIL ELEVENE", height=200, placeholder="Skriv inn oppgaveteksten eller instruksjonene her...")

    if st.button("🚀 Lagre og Opprett Prøve", type="primary", use_container_width=True):
        if not new_code or not new_prompt:
            st.error("Du må fylle ut både prøvekode og oppgavetekst før du kan opprette prøven!")
        else:
            payload = {
                "prompt": new_prompt,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            res = requests.put(f"{FIREBASE_URL}/exams/{new_code}.json", json=payload)
            if res.status_code == 200:
                st.success(f"✅ Prøven '{new_code}' ble vellykket opprettet i skyen og er nå klar for elevene!")
                st.session_state["current_exam_code"] = new_code
            else:
                st.error("Kunne ikke opprette prøven i databasen. Sjekk internettforbindelsen og prøv igjen.")
