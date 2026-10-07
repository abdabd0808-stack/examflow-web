import streamlit as st
import requests
import pandas as pd
import random
import io
import re
from datetime import datetime, timedelta

# Importerer biblioteker for nedlasting av PDF og Word
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document
from docx.shared import Pt, RGBColor

st.set_page_config(page_title="EXAMFLOW — Lærer Dashbord", layout="wide", page_icon="🌿")

FIREBASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"
NORMAL_WORDS_PER_MINUTE = 25  # Normal skrivehastighet for elever

# --- HJELPEFUNKSJONER FOR NEDLASTING ---
def generate_pdf_bytes(student_name, exam_code, text, prompt_text=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
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
        prompt_p.add_run("Oppgave: ").bold = True
        prompt_p.add_run(prompt_text).italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    for p in text.split('\n'):
        if p.strip():
            doc_p = doc.add_paragraph(p)
            doc_p.paragraph_format.space_after = Pt(8)
            doc_p.paragraph_format.line_spacing = 1.15

    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- SESSION STATE ---
if "current_exam_code" not in st.session_state:
    st.session_state["current_exam_code"] = "EXAM-5114"

if "history_cache" not in st.session_state:
    st.session_state["history_cache"] = {}

if "last_text_cache" not in st.session_state:
    st.session_state["last_text_cache"] = {}

if "start_times" not in st.session_state:
    st.session_state["start_times"] = {}

if "last_change_time" not in st.session_state:
    st.session_state["last_change_time"] = {}

if "frozen_metrics" not in st.session_state:
    st.session_state["frozen_metrics"] = {}

# --- DASHBORD HEADER ---
st.title("🌿 EXAMFLOW — Lærer Dashbord")
st.write("Administrer prøver, overvåk elever i realtid og last ned leverte besvarelser.")

tabs = st.tabs(["📊 Live Overvåking & Graf", "📥 Leverte Besvarelser", "➕ Opprett Ny Prøve"])

# ================= TAB 1: LIVE OVERVÅKING & GRAF =================
with tabs[0]:
    col_input, col_btn = st.columns([3, 1])

    with col_input:
        exam_code = st.text_input(
            "Overvåk prøvekode", 
            value=st.session_state["current_exam_code"],
            key="exam_code_input"
        ).strip().upper()

    with col_btn:
        st.write("")
        st.write("")
        if st.button("🎲 Generer Ny Kode", use_container_width=True):
            new_random_code = f"EXAM-{random.randint(1000, 9999)}"
            st.session_state["current_exam_code"] = new_random_code
            st.rerun()

    # AUTOMATISK REFRESH FRAGMENT HVERT 3. SEKUND
    @st.fragment(run_every=3)
    def render_live_monitoring(current_code):
        if not current_code:
            return

        res = requests.get(f"{FIREBASE_URL}/exams/{current_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error(f"Fant ingen prøve med kode '{current_code}'. Sjekk koden og prøv igjen.")
            return

        prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or exam_data.get("oppgave") or ""
        if prompt_text:
            st.info(f"📌 **Oppgavetekst:** {prompt_text}")

        raw_alerts = exam_data.get("alerts", {})
        auto_alerts = []

        students = exam_data.get("students_joined", {})
        live_texts = exam_data.get("live_texts", {})
        submissions = exam_data.get("submissions", {})

        now_time = datetime.now()
        now_str = now_time.strftime("%H:%M:%S")

        # ELEVANALYSE FOR MISTENKELIG ADBERD OG INAKTIVITET
        if isinstance(students, dict) and students:
            for student_key in students.keys():
                is_submitted = isinstance(submissions, dict) and student_key in submissions
                if is_submitted:
                    continue

                display_name = student_key.replace("_", " ")
                student_info = live_texts.get(student_key, {}) if isinstance(live_texts, dict) else {}

                if isinstance(student_info, dict):
                    text_content = student_info.get("text", "")
                    word_count = student_info.get("words", len(text_content.split()))
                else:
                    text_content = str(student_info)
                    word_count = len(text_content.split())

                if student_key not in st.session_state["start_times"]:
                    st.session_state["start_times"][student_key] = now_time

                prev_info = st.session_state["last_text_cache"].get(student_key, {"words": word_count, "time": now_time, "text": text_content})
                prev_words = prev_info["words"]
                word_diff = word_count - prev_words

                if student_key not in st.session_state["last_change_time"]:
                    st.session_state["last_change_time"][student_key] = now_time
                elif word_diff != 0:
                    st.session_state["last_change_time"][student_key] = now_time

                # ⚡ 1. SJEKK FOR EKSTREM SKRIVEHASTIGHET / PASTE
                if word_diff >= 30:
                    auto_alerts.append({
                        "student": display_name,
                        "time": now_str,
                        "message": f"⚡ Ekstrem økning (+{word_diff} ord på 3 sek). Sannsynligvis limt inn ekstern tekst!"
                    })

                # 🔤 2. SJEKK FOR TASTATURENS SPAM
                words = text_content.split()
                has_long_random_words = any(len(w) > 25 for w in words)
                if has_long_random_words:
                    auto_alerts.append({
                        "student": display_name,
                        "time": now_str,
                        "message": "⚠️ Registrerte unormalt lange ord (tastaturbanking / meningsløs tekst)."
                    })

                # ⏸️ 3. SJEKK FOR INAKTIVITET (OVER 10 MINUTTER)
                last_active = st.session_state["last_change_time"][student_key]
                inactive_duration = now_time - last_active
                if inactive_duration >= timedelta(minutes=10) and word_count > 0:
                    minutes_inactive = int(inactive_duration.total_seconds() // 60)
                    auto_alerts.append({
                        "student": display_name,
                        "time": now_str,
                        "message": f"⏸️ Ingen skriveaktivitet på {minutes_inactive} minutter (over 10 min inaktiv)."
                    })

                st.session_state["last_text_cache"][student_key] = {
                    "words": word_count,
                    "time": now_time,
                    "text": text_content
                }

        # VISNING AV VARSLINGER
        st.warning("⚠️ REGISTRERTE HENDELSER / VARSLINGER:")
        has_alerts = False

        for a in auto_alerts:
            st.error(f"🚨 **{a['student']}** [{a['time']}]: {a['message']}")
            has_alerts = True

        if isinstance(raw_alerts, dict) and raw_alerts:
            for alert_id, alert in reversed(list(raw_alerts.items())):
                if isinstance(alert, dict):
                    st.error(f"🚨 **{alert.get('student', '')}** [{alert.get('time', '')}]: {alert.get('message', '')}")
                    has_alerts = True

        if not has_alerts:
            st.caption("Ingen spesielle hendelser eller unormal skriveadferd registrert ennå.")

        st.divider()

        # ELEVOVERSIKT & GRAF
        if isinstance(students, dict) and students:
            st.success(f"Viser live data for {len(students)} elev(er) (Oppdateres automatisk hvert 3. sek)")

            for student_key in students.keys():
                display_name = student_key.replace("_", " ")
                is_submitted = isinstance(submissions, dict) and student_key in submissions

                student_info = live_texts.get(student_key, {}) if isinstance(live_texts, dict) else {}

                if isinstance(student_info, dict):
                    text_content = student_info.get("text", "")
                    word_count = student_info.get("words", len(text_content.split()))
                    history = student_info.get("history", {})
                else:
                    text_content = str(student_info)
                    word_count = len(text_content.split())
                    history = {}

                # BYGG OG HÅNDTER CACHE
                if student_key not in st.session_state["history_cache"]:
                    st.session_state["history_cache"][student_key] = []

                cache_list = st.session_state["history_cache"][student_key]

                if not is_submitted:
                    start_dt = st.session_state["start_times"].get(student_key, now_time)
                    elapsed_minutes = max(0.1, (now_time - start_dt).total_seconds() / 60.0)
                    expected_normal_words = int(elapsed_minutes * NORMAL_WORDS_PER_MINUTE)

                    if expected_normal_words > 0:
                        pct_vs_normal = ((word_count - expected_normal_words) / expected_normal_words) * 100
                    else:
                        pct_vs_normal = 0.0

                    if isinstance(history, dict) and history:
                        cache_list.clear()
                        for h in history.values():
                            if isinstance(h, dict):
                                t_str = h.get("time")
                                w_val = h.get("words", 0)
                                cache_list.append({
                                    "Klokkeslett": t_str,
                                    "Faktisk ordtall": w_val,
                                    "Normal skrivehastighet (forventet)": expected_normal_words
                                })
                    else:
                        if not cache_list:
                            start_time_str = (now_time - timedelta(seconds=30)).strftime("%H:%M:%S")
                            cache_list.append({
                                "Klokkeslett": start_time_str,
                                "Faktisk ordtall": max(0, word_count - 10),
                                "Normal skrivehastighet (forventet)": max(1, expected_normal_words - 5)
                            })
                        if not cache_list or cache_list[-1]["Klokkeslett"] != now_str:
                            cache_list.append({
                                "Klokkeslett": now_str,
                                "Faktisk ordtall": word_count,
                                "Normal skrivehastighet (forventet)": expected_normal_words
                            })

                    first_words = cache_list[0].get("Faktisk ordtall", word_count) if cache_list else word_count
                    word_delta = word_count - first_words

                else:
                    # ELEV ER LEVERT -> LÅS/FRYS ALL DATA SÅ DET IKKE BLIR 0
                    text_content = str(submissions[student_key])
                    word_count = len(text_content.split())

                    if student_key not in st.session_state["frozen_metrics"]:
                        # Hvis krasj/refresh har tømt history_cache, gjenoppbygg en dummy-graf basert på leveringen
                        if not cache_list:
                            start_time_str = (now_time - timedelta(minutes=10)).strftime("%H:%M:%S")
                            cache_list.append({
                                "Klokkeslett": start_time_str,
                                "Faktisk ordtall": 0,
                                "Normal skrivehastighet (forventet)": 0
                            })
                            cache_list.append({
                                "Klokkeslett": now_str,
                                "Faktisk ordtall": word_count,
                                "Normal skrivehastighet (forventet)": int(word_count * 0.9)
                            })

                        first_words = cache_list[0].get("Faktisk ordtall", 0)
                        word_delta = word_count - first_words
                        
                        last_expected = cache_list[-1].get("Normal skrivehastighet (forventet)", int(word_count * 0.9))
                        if last_expected <= 0:
                            last_expected = int(word_count * 0.9) if word_count > 0 else 10

                        frozen_pct = ((word_count - last_expected) / last_expected) * 100 if last_expected > 0 else 0.0

                        st.session_state["frozen_metrics"][student_key] = {
                            "word_count": word_count,
                            "word_delta": word_delta,
                            "pct_vs_normal": frozen_pct,
                            "expected_normal_words": last_expected,
                            "history_snapshot": list(cache_list)
                        }

                    frozen = st.session_state["frozen_metrics"][student_key]
                    word_count = frozen["word_count"]
                    word_delta = frozen["word_delta"]
                    pct_vs_normal = frozen["pct_vs_normal"]
                    expected_normal_words = frozen["expected_normal_words"]
                    cache_list = frozen["history_snapshot"]

                # ELEVKORT
                status_label = "✅ Levert (Fryst)" if is_submitted else "🟢 Aktiv i realtid"
                card_title = f"👤 {display_name} — {word_count} ord | Status: {status_label}"

                with st.expander(card_title, expanded=not is_submitted):
                    st.caption(f"Tekst fra {display_name} ({'LEVERT' if is_submitted else 'PÅGÅENDE'})")
                    st.text_area(f"Tekstvisning_{student_key}", value=text_content, height=180, disabled=True, label_visibility="collapsed")

                    m1, m2, m3 = st.columns(3)
                    m1.metric(
                        label="Totalt antall ord", 
                        value=f"{word_count} ord", 
                        delta=f"{word_delta:+d} ord" if not is_submitted else None
                    )
                    m2.metric(
                        label="Økning vs normal hastighet (25 ord/min)", 
                        value=f"{pct_vs_normal:+.1f}%", 
                        delta=f"{pct_vs_normal:+.1f}% vs normal" if not is_submitted else None
                    )
                    m3.metric(label="Forventet ordtall til nå", value=f"{expected_normal_words} ord")

                    st.write("")
                    st.markdown("**📈 Skriveprogresjon sammenlignet med normal skrivehastighet**")

                    if cache_list and len(cache_list) >= 1:
                        df = pd.DataFrame(cache_list)
                        st.line_chart(df.set_index("Klokkeslett"))
                    else:
                        st.caption("📈 Registrerer skriveprogresjon...")
        else:
            st.info("Ingen elever har koblet seg til prøven ennå.")

    render_live_monitoring(exam_code)

# ================= TAB 2: LEVERTE BESVARELSER =================
with tabs[1]:
    sub_exam_code = st.text_input("Skriv prøvekode for å se leveringer", key="sub_code").strip().upper()

    if sub_exam_code:
        res = requests.get(f"{FIREBASE_URL}/exams/{sub_exam_code}.json")
        exam_data = res.json() if res.status_code == 200 else None

        if not exam_data:
            st.error("Fant ikke prøven.")
        else:
            submissions = exam_data.get("submissions", {})
            times = exam_data.get("submission_times", {})
            prompt_text = exam_data.get("prompt") or exam_data.get("instruction") or ""

            if not isinstance(submissions, dict) or not submissions:
                st.warning("Ingen elever har levert prøven ennå.")
            else:
                st.success(f"Totalt {len(submissions)} levert(e) besvarelse(r).")
                
                for student_key, sub_text in submissions.items():
                    student_display = student_key.replace("_", " ")
                    sub_time = times.get(student_key, "Ukjent tidspunkt") if isinstance(times, dict) else "Ukjent tidspunkt"

                    with st.expander(f"📄 {student_display} — Levert kl. {sub_time}"):
                        st.text_area(f"Levering_{student_key}", value=str(sub_text), height=250, disabled=True)

                        col_pdf, col_word = st.columns(2)
                        
                        pdf_bytes = generate_pdf_bytes(student_display, sub_exam_code, str(sub_text), prompt_text)
                        col_pdf.download_button(
                            label="📄 Last ned PDF",
                            data=pdf_bytes,
                            file_name=f"Levert_{student_display.replace(' ', '_')}_{sub_exam_code}.pdf",
                            mime="application/pdf",
                            key=f"pdf_{student_key}"
                        )

                        word_bytes = generate_word_bytes(student_display, sub_exam_code, str(sub_text), prompt_text)
                        col_word.download_button(
                            label="📝 Last ned Word (.docx)",
                            data=word_bytes,
                            file_name=f"Levert_{student_display.replace(' ', '_')}_{sub_exam_code}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"word_{student_key}"
                        )

# ================= TAB 3: OPPRETT NY PRØVE =================
with tabs[2]:
    st.subheader("➕ Opprett en ny prøve")
    
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        new_code = st.text_input("NY PRØVEKODE (f.eks. EXAM-9941)", value=f"EXAM-{random.randint(1000, 9999)}").strip().upper()
    with col_c2:
        st.write("")
        st.write("")
        if st.button("🎲 Generer Ny Kode", key="btn_gen_new"):
            st.rerun()

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
                st.session_state["current_exam_code"] = new_code
            else:
                st.error("Kunne ikke opprette prøven. Sjekk internettforbindelsen.")
