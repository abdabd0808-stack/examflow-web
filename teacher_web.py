import time
import threading
import requests
import customtkinter as ctk
from tkinter import messagebox, filedialog

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- FIREBASE SKY-KONFIGURASJON ---
FIREBASE_BASE_URL = "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"

class TeacherDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EXAMFLOW — Lærerdashbord (Sky-versjon)")
        self.geometry("1100企x700")
        self.minsize(950, 600)

        self.current_code = ""
        self.is_monitoring = False
        self.known_alerts_count = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Container
        self.main_container = ctk.CTkFrame(self, fg_color="#f8fafc", corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self.main_container, fg_color="#ffffff", height=60, corner_radius=0, border_width=1, border_color="#e2e8f0")
        header.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkLabel(header, text="🌿 EXAMFLOW — LÆRERDASHBORD", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0284c7").pack(side="left", padx=20, pady=15)

        # Content Area
        content = ctk.CTkFrame(self.main_container, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        # LEFT PANEL: Lag prøve
        left_panel = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e2e8f0")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="Opprett Ny Prøve", font=ctk.CTkFont(size=16, weight="bold"), text_color="#0f172a").pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(left_panel, text="PRØVEKODE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=20)
        self.ent_code = ctk.CTkEntry(left_panel, height=40, corner_radius=8, fg_color="#f8fafc", text_color="#0f172a", border_color="#cbd5e1", font=ctk.CTkFont(weight="bold"))
        self.ent_code.pack(fill="x", padx=20, pady=(4, 15))
        self.generate_new_code()

        ctk.CTkLabel(left_panel, text="OPPGAVETEKST / INSTRUKSJONER", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=20)
        self.txt_prompt = ctk.CTkTextbox(left_panel, height=180, corner_radius=8, fg_color="#f8fafc", text_color="#0f172a", border_color="#cbd5e1", font=ctk.CTkFont(size=13))
        self.txt_prompt.pack(fill="x", padx=20, pady=(4, 15))

        self.btn_publish = ctk.CTkButton(
            left_panel, 
            text="Publiser Prøve til Skyen", 
            command=self.publish_exam,
            height=42,
            corner_radius=8,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_publish.pack(fill="x", padx=20, pady=(0, 20))

        # RIGHT PANEL: Live Overvåking
        right_panel = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#e2e8f0")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(right_panel, text="Live Overvåking & Elever", font=ctk.CTkFont(size=16, weight="bold"), text_color="#0f172a").grid(row=0, column=0, anchor="w", padx=20, pady=(20, 5))

        self.lbl_status = ctk.CTkLabel(right_panel, text="Ingen prøve overvåkes nå.", font=ctk.CTkFont(size=12), text_color="#64748b")
        self.lbl_status.grid(row=1, column=0, anchor="w", padx=20, pady=(0, 10))

        # Tabs
        self.tabview = ctk.CTkTabview(right_panel, corner_radius=8)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self.tab_joined = self.tabview.add("Tilkoblede Elever")
        self.tab_live = self.tabview.add("Live Tekst")
        self.tab_submissions = self.tabview.add("Leverte Besvarelser")

        # Tab 1: Joined
        self.txt_joined = ctk.CTkTextbox(self.tab_joined, font=ctk.CTkFont(size=13), fg_color="#f8fafc", text_color="#0f172a")
        self.txt_joined.pack(fill="both", expand=True)

        # Tab 2: Live Text
        self.live_student_var = ctk.StringVar(value="Velg elev...")
        self.opt_students = ctk.CTkOptionMenu(self.tab_live, variable=self.live_student_var, values=["Velg elev..."], command=self.on_student_select)
        self.opt_students.pack(fill="x", pady=(0, 10))

        self.txt_live = ctk.CTkTextbox(self.tab_live, font=ctk.CTkFont(size=13), fg_color="#f8fafc", text_color="#0f172a")
        self.txt_live.pack(fill="both", expand=True)

        # Tab 3: Submissions
        self.sub_student_var = ctk.StringVar(value="Velg levert elev...")
        self.opt_sub_students = ctk.CTkOptionMenu(self.tab_submissions, variable=self.sub_student_var, values=["Velg levert elev..."], command=self.on_sub_student_select)
        self.opt_sub_students.pack(fill="x", pady=(0, 10))

        self.txt_submission = ctk.CTkTextbox(self.tab_submissions, font=ctk.CTkFont(size=13), fg_color="#f8fafc", text_color="#0f172a")
        self.txt_submission.pack(fill="both", expand=True)

    def generate_new_code(self):
        import random
        import string
        code = "EXAM-" + "".join(random.choices(string.digits, k=4))
        self.ent_code.delete(0, "end")
        self.ent_code.insert(0, code)

    def publish_exam(self):
        code = self.ent_code.get().strip().upper()
        prompt = self.txt_prompt.get("1.0", "end-1c").strip()

        if not code or not prompt:
            messagebox.showwarning("Mangler info", "Vennligst fyll ut både prøvekode og oppgavetekst.")
            return

        exam_data = {
            "code": code,
            "prompt": prompt,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            url = f"{FIREBASE_BASE_URL}/exams/{code}.json"
            requests.patch(url, json=exam_data, timeout=5)
            
            self.current_code = code
            self.lbl_status.configure(text=f"Aktiv overvåking av prøve: {code}", text_color="#10b981")
            messagebox.showinfo("Publisert!", f"Prøven {code} er nå publisert til skyen og klar for elever!")

            if not self.is_monitoring:
                self.is_monitoring = True
                threading.Thread(target=self.cloud_monitor_loop, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Feil", f"Kunne ikke publisere prøven til skyen: {e}")

    def cloud_monitor_loop(self):
        """Henter data direkte fra Firebase i sanntid"""
        while self.is_monitoring:
            if self.current_code:
                try:
                    url = f"{FIREBASE_BASE_URL}/exams/{self.current_code}.json"
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200 and res.json():
                        data = res.json()
                        self.after(0, lambda d=data: self.update_dashboard_ui(d))
                except Exception:
                    pass
            time.sleep(2.0)

    def update_dashboard_ui(self, data):
        # 1. Tilkoblede elever
        joined_dict = data.get("students_joined", {})
        self.txt_joined.configure(state="normal")
        self.txt_joined.delete("1.0", "end")
        if joined_dict:
            for student, joined_time in joined_dict.items():
                clean_student = student.replace("_", ".")
                self.txt_joined.insert("end", f"🟢 {clean_student} — Koblet til kl. {joined_time}\n")
        else:
            self.txt_joined.insert("end", "Ingen elever har koblet seg til ennå.")
        self.txt_joined.configure(state="disabled")

        # 2. Live Tekst liste
        live_texts = data.get("live_texts", {})
        student_list = [s.replace("_", ".") for s in live_texts.keys()]
        if student_list:
            self.opt_students.configure(values=student_list)
        
        # Oppdater valgt elevs live-tekst hvis valgt
        selected = self.live_student_var.get()
        if selected in student_list:
            clean_key = selected.replace(".", "_")
            live_text = live_texts.get(clean_key, "")
            self.txt_live.configure(state="normal")
            self.txt_live.delete("1.0", "end")
            self.txt_live.insert("1.0", live_text)
            self.txt_live.configure(state="disabled")

        # 3. Leverte besvarelser
        submissions = data.get("submissions", {})
        submission_times = data.get("submission_times", {})
        sub_list = [s.replace("_", ".") for s in submissions.keys()]
        if sub_list:
            self.opt_sub_students.configure(values=sub_list)

        selected_sub = self.sub_student_var.get()
        if selected_sub in sub_list:
            clean_key = selected_sub.replace(".", "_")
            sub_text = submissions.get(clean_key, "")
            sub_time = submission_times.get(clean_key, "Ukjent tid")
            self.txt_submission.configure(state="normal")
            self.txt_submission.delete("1.0", "end")
            self.txt_submission.insert("1.0", f"--- LEVERT KL. {sub_time} ---\n\n{sub_text}")
            self.txt_submission.configure(state="disabled")

    def on_student_select(self, choice):
        self.live_student_var.set(choice)

    def on_sub_student_select(self, choice):
        self.sub_student_var.set(choice)

if __name__ == "__main__":
    app = TeacherDashboard()
    app.mainloop()
