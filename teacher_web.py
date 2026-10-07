import streamlit as st
import requests
import pandas as pd
import io
import time
from datetime import datetime

# ReportLab for PDF-generering
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# python-docx for Word-generering
from docx import Document
from docx.shared import Pt, RGBColor

st.set_page_config(page_title="EXAMFLOW — Lærer Dashbord", layout="wide", page_icon="🌿")

FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

# --- HJELPEFUNKSJONER FOR PDF OG WORD ---

def generate_pdf_bytes(student_name, exam_code, text, prompt_text=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#0f172a"), spaceAfter=10)
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#475569"), spaceAfter=15)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=11, leading=16, textColor=colors.HexColor("#1e293b"), spaceAfter=12)

    story = [
        Paragraph(f"Offisiell Eksamensbesvarelse — {exam_code}", title_style),
        Paragraph(f"<b>Elev:</b> {student_name} | <b>Prøvekode:</b> {exam_code} | <b>Eksportert:</b> {datetime.now().strftime('%d.%m.%Y kl. %H:%M:%S')}", meta_style),
        Spacer(1, 10)
    ]

    if prompt_text:
        story.append(Paragraph(f"<b>Oppgave:</b> <i>{prompt_text}</i>", meta_style))
        story.append(Spacer(1, 15))

    for p in text.split('\n'):
        if p.strip():
            safe_p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_p, body_style))
        else:
            story.append(Spacer(1, 8))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_word_bytes(student_name, exam_code, text, prompt_text=""):
    buffer = io.BytesIO()
    doc = Document()

    title = doc.add_heading(level=1)
    run_title = title.add_run(f"Offisiell Eksamensbesvarelse — {exam_code}")
    run_title.font.size = Pt(18)
    run_title.font.color.rgb = RGBColor(15, 23, 42)

    meta = doc.add_paragraph()
    p_meta = meta.add_run(f"Elev: {student_name} | Prøvekode: {exam_code} | Eksportert: {datetime.now().strftime('%d.%m.%Y kl. %H:%M:%S')}")
    p_meta.font.size = Pt(10)
    p_meta.font.italic = True
    p_meta.font.color.rgb = RGBColor(71, 85, 105)

    if prompt_text:
        prompt_p = doc.add_paragraph()
        r_label = prompt_p.add_run("Oppgave: ")
        r_label.bold = True
        r_prompt = prompt_p.add_run(prompt_text)
        r_prompt.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    for p in text.split('\n'):
        if p.strip():
            doc_p = doc.add_paragraph(p)
            doc_p.paragraph_format.space_after = Pt(8)
            doc_p.paragraph_format.line_spacing = 1.15

    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- HOVEDAPPLIKASJON ---

st.title("🌿 EXAMFLOW — Lærer Dashbord")
st.write("Administrer prøver, overvåk elever i realtid og last ned leverte besvarelser.")

tabs = st.tabs(["📊 Live Overvåking & Graf", "📥 Leverte Besvarelser", "➕ Opprett Ny Prøve"])

# ================= TAB 1: LIVE OVERVÅKING & GRAF =================
with tabs[0]:
    exam_code = st.text_input("SØK ETTER PRØVEKODE", "").strip().upper()

    if exam_code:
        res = requests.get(f"{FIREBASE_URL}/exams/{exam_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error(f"Fant ingen prøve med kode '{exam_code}'. Sjekk koden og prøv igjen.")
        else:
            prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or exam_data.get("oppgave") or "Ingen oppgavetekst registrert."
            st.info(f"📌 **Oppgavetekst for {exam_code}:** {prompt_text}")

            col1, col2 = st.columns([1, 2])

            with col1:
                st.subheader("👥 Påloggede Elever")
                students = exam_data.get("students_joined", {})
                
                if students:
                    student_list = list(students.keys())
                    selected_student_raw = st.selectbox(
                        "Velg elev for detaljer:", 
                        student_list, 
                        format_func=lambda x: x.replace("_", " ")
                    )
                else:
                    st.warning("Ingen elever har koblet til ennå.")
                    selected_student_raw = None

                st.divider()

                st.subheader("🔔 Hendelser og Varsler")
                alerts = exam_data.get("alerts", {})
                if alerts:
                    for alert_id, alert in reversed(list(alerts.items())):
                        st.caption(f"⏱ **{alert.get('time', '')}** — **{alert.get('student', '')}:** {alert.get('message', '')}")
                else:
                    st.write("Ingen varsler registrert ennå.")

            with col2:
                if selected_student_raw:
                    display_name = selected_student_raw.replace("_", " ")
                    st.subheader(f"📝 Live besvarelse: {display_name}")

                    live_info = exam_data.get("live_texts", {}).get(selected_student_raw, {})
                    current_text = live_info.get("text", "Ingen tekst registrert...")
                    word_count = live_info.get("words", 0)

                    st.metric(label="Antall ord i teksten nå", value=f"{word_count} ord")
                    st.text_area("Live teksteditor", value=current_text, height=200, disabled=True)

                    st.divider()

                    # GRAF OVER TID
                    st.subheader("📈 Skriveprogresjon (Ord over tid)")
                    history = live_info.get("history", {})

                    if history:
                        df_data = []
                        for h in history.values():
                            df_data.append({"Klokkeslett": h.get("time"), "Antall ord": h.get("words")})
                        
                        df = pd.DataFrame(df_data)
                        st.line_chart(df.set_index("Klokkeslett"))
                    else:
                        st.info("Grafen oppdateres automatisk når eleven har skrevet i mer enn 30 sekunder.")

                else:
                    st.info("Velg en elev i menyen til venstre for å se besvarelsen og grafen.")

# ================= TAB 2: LEVERTE BESVARELSER =================
with tabs[1]:
    st.subheader("📥 Oversikt over leverte besvarelser")
    sub_exam_code = st.text_input("SKRIV PRØVEKODE FOR Å SE LEVERINGER", key="sub_code").strip().upper()

    if sub_exam_code:
        res = requests.get(f"{FIREBASE_URL}/exams/{sub_exam_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error("Fant ikke prøven.")
        else:
            submissions = exam_data.get("submissions", {})
            times = exam_data.get("submission_times", {})
            prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or ""

            if not submissions:
                st.warning("Ingen elever har levert prøven ennå.")
            else:
                st.success(f"Totalt {len(submissions)} levert(e) besvarelse(r).")
                
                sub_student_list = list(submissions.keys())
                selected_sub_student = st.selectbox(
                    "Velg elev for å lese/laste ned:", 
                    sub_student_list,
                    format_func=lambda x: x.replace("_", " ")
                )

                if selected_sub_student:
                    student_display = selected_sub_student.replace("_", " ")
                    sub_text = submissions[selected_sub_student]
                    sub_time = times.get(selected_sub_student, "Ukjent tidspunkt")

                    st.markdown(f"### Besvarelse fra {student_display}")
                    st.caption(f"🕒 Levert klokken: **{sub_time}** | Ord: **{len(sub_text.split())}**")

                    st.text_area("Besvarelsestekst", value=sub_text, height=300, disabled=True)

                    # Last ned knapper
                    col_pdf, col_word = st.columns(2)

                    pdf_bytes = generate_pdf_bytes(student_display, sub_exam_code, sub_text, prompt_text)
                    col_pdf.download_button(
                        label="📄 Last ned som PDF",
                        data=pdf_bytes,
                        file_name=f"Levert_{student_display.replace(' ', '_')}_{sub_exam_code}.pdf",
                        mime="application/pdf"
                    )

                    word_bytes = generate_word_bytes(student_display, sub_exam_code, sub_text, prompt_text)
                    col_word.download_button(
                        label="📝 Last ned som Word (.docx)",
                        data=word_bytes,
                        file_name=f"Levert_{student_display.replace(' ', '_')}_{sub_exam_code}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

# ================= TAB 3: OPPRETT NY PRØVE =================
with tabs[2]:
    st.subheader("➕ Opprett en ny prøve")
    
    new_code = st.text_input("NY PRØVEKODE (f.eks. EXAM-99)", "").strip().upper()
    new_prompt = st.text_area("OPPGAVETEKST / INSTRUKSJON TIL ELEVENE", height=150)

    if st.button("Lagre og Opprett Prøve", type="primary"):
        if not new_code or not new_prompt:
            st.error("Du må fylle ut både prøvekode og oppgavetekst!")
        else:
            payload = {
                "prompt": new_prompt,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            res = requests.put(f"{FIREBASE_URL}/exams/{new_code}.json", json=payload)
            if res.status_code == 200:
                st.success(f"✅ Prøven '{new_code}' er nå opprettet i skyen og klar for elever!")
            else:
                st.error("Kunne ikke opprette prøven. Sjekk internettforbindelsen.")
