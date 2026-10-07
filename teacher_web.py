<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EXAMFLOW — Lærer Dashbord</title>

    <!-- Tailwind CSS for moderne design -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Firebase JS SDK (v8) -->
    <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
    <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-database.js"></script>
    
    <!-- Chart.js for interaktiv graf -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="text-slate-800 p-6">

    <div class="max-w-7xl mx-auto space-y-6">
        
        <!-- HEADER -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row justify-between items-center gap-4">
            <div>
                <h1 class="text-2xl font-bold text-sky-600 flex items-center gap-2">🌿 EXAMFLOW — Lærer Dashbord</h1>
                <p class="text-slate-500 text-sm">Overvåk prøver, se elevstatus og skriveprogresjon i realtid.</p>
            </div>
            
            <div class="flex items-center gap-3">
                <input type="text" id="examCodeInput" placeholder="Søk prøvekode (f.eks. EXAM-4821)" class="px-4 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 uppercase font-semibold text-slate-700">
                <button onclick="kobleTilProeve()" class="bg-sky-600 hover:bg-sky-700 text-white font-semibold px-5 py-2 rounded-xl transition-all shadow-sm">
                    Koble til
                </button>
            </div>
        </div>

        <!-- HOVEDINNHOLD -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <!-- VENSTRE KOLONNE: ELEVLISTE & VARSLER -->
            <div class="space-y-6">
                <!-- Elevliste -->
                <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                    <h2 class="text-lg font-bold text-slate-800 mb-3 flex items-center justify-between">
                        <span>👥 Påloggede Elever</span>
                        <span id="studentCount" class="text-xs bg-sky-100 text-sky-700 font-bold px-2.5 py-1 rounded-full">0</span>
                    </h2>
                    <ul id="studentList" class="space-y-2 max-h-60 overflow-y-auto pr-1">
                        <li class="text-slate-400 text-sm italic">Skriv inn prøvekode for å hente elever...</li>
                    </ul>
                </div>

                <!-- Hendelseslogg / Varsler -->
                <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                    <h2 class="text-lg font-bold text-slate-800 mb-3">🔔 Hendelser & Varsler</h2>
                    <div id="alertsLog" class="space-y-2 max-h-60 overflow-y-auto text-sm pr-1">
                        <p class="text-slate-400 italic">Ingen varsler ennå...</p>
                    </div>
                </div>
            </div>

            <!-- HØYRE KOLONNE: LIVE TEKST & GRAF -->
            <div class="lg:col-span-2 space-y-6">

                <!-- Elevvelger og Live Tekst -->
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
                    <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-100 pb-4">
                        <div>
                            <h2 class="text-xl font-bold text-slate-800" id="selectedStudentTitle">Velg en elev</h2>
                            <p class="text-xs text-slate-500" id="selectedStudentSub">Klikk på en elev til venstre for å se live-tekst og graf.</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-600" id="liveWordCount">0 ord</span>
                            <span class="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-600" id="liveStatus">Ingen elev valgt</span>
                        </div>
                    </div>

                    <!-- Tekstfelt for live-visning -->
                    <div id="liveTextContent" class="w-full h-48 p-4 bg-slate-50 border border-slate-200 rounded-xl overflow-y-auto whitespace-pre-wrap font-mono text-sm text-slate-800">
                        Ingen tekst valgt...
                    </div>
                </div>

                <!-- Graf over skriveprogresjon -->
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <h3 class="text-lg font-bold text-slate-800 mb-1">📈 Skriveprogresjon (Ord over tid)</h3>
                    <p class="text-xs text-slate-500 mb-4">Viser hvordan elevens tekst har vokst igjennom prøveøkten.</p>
                    
                    <div class="w-full relative" style="height: 260px;">
                        <canvas id="studentProgressChart"></canvas>
                    </div>
                </div>

            </div>

        </div>

    </div>

    <script>
        // FIREBASE KONFIGURASJON
        const firebaseConfig = {
            databaseURL: "https://exam-flow-bedc2-default-rtdb.europe-west1.firebasedatabase.app"
        };
        
        firebase.initializeApp(firebaseConfig);
        const db = firebase.database();

        let currentExamCode = "";
        let currentStudent = "";
        let progressChart = null;

        // Koble til prøven via oppgitt kode
        function kobleTilProeve() {
            const codeInput = document.getElementById("examCodeInput").value.trim().toUpperCase();
            if (!codeInput) {
                alert("Vennligst oppgi en prøvekode!");
                return;
            }

            currentExamCode = codeInput;
            
            // Lytt på påloggede elever
            db.ref(`exams/${currentExamCode}/students_joined`).on('value', (snapshot) => {
                const data = snapshot.val();
                const studentList = document.getElementById("studentList");
                studentList.innerHTML = "";

                if (!data) {
                    studentList.innerHTML = `<li class="text-slate-400 text-sm italic">Ingen elever har koblet til ennå.</li>`;
                    document.getElementById("studentCount").innerText = "0";
                    return;
                }

                const students = Object.keys(data);
                document.getElementById("studentCount").innerText = students.length;

                students.forEach(rawName => {
                    const displayName = rawName.replace(/_/g, " ");
                    const li = document.createElement("li");
                    li.className = "p-2.5 rounded-xl border border-slate-100 hover:bg-sky-50 hover:border-sky-200 cursor-pointer transition-all flex justify-between items-center text-sm font-medium";
                    li.onclick = () => velgElev(rawName, displayName);
                    li.innerHTML = `<span>👤 ${displayName}</span> <span class="text-xs text-sky-600 font-bold">Vis ➔</span>`;
                    studentList.appendChild(li);
                });
            });

            // Lytt på hendelser/varsler
            db.ref(`exams/${currentExamCode}/alerts`).on('value', (snapshot) => {
                const alerts = snapshot.val();
                const alertsLog = document.getElementById("alertsLog");
                alertsLog.innerHTML = "";

                if (!alerts) {
                    alertsLog.innerHTML = `<p class="text-slate-400 italic">Ingen varsler ennå...</p>`;
                    return;
                }

                Object.values(alerts).reverse().forEach(alert => {
                    const item = document.createElement("div");
                    item.className = "p-2 rounded-lg bg-slate-50 border border-slate-100 flex justify-between text-xs";
                    item.innerHTML = `<span><b>${alert.student}:</b> ${alert.message}</span> <span class="text-slate-400">${alert.time}</span>`;
                    alertsLog.appendChild(item);
                });
            });
        }

        // Velg en elev for å se live-tekst og graf
        function velgElev(rawName, displayName) {
            currentStudent = rawName;
            document.getElementById("selectedStudentTitle").innerText = displayName;
            document.getElementById("selectedStudentSub").innerText = `Lytter direkte på ${displayName}...`;

            // Lytt på live-tekst
            db.ref(`exams/${currentExamCode}/live_texts/${rawName}`).on('value', (snapshot) => {
                const liveData = snapshot.val();
                if (liveData) {
                    document.getElementById("liveTextContent").innerText = liveData.text || "Tom besvarelse...";
                    document.getElementById("liveWordCount").innerText = `${liveData.words || 0} ord`;
                    document.getElementById("liveStatus").innerText = liveData.status || "Aktiv";
                } else {
                    document.getElementById("liveTextContent").innerText = "Ingen live-data tilgjengelig ennå...";
                    document.getElementById("liveWordCount").innerText = "0 ord";
                    document.getElementById("liveStatus").innerText = "Ukjent";
                }
            });

            // Oppdater grafen for elevens progresjon
            oppdaterElevGraf(rawName, displayName);
        }

        // Hent historikk og tegn graf
        function oppdaterElevGraf(rawName, displayName) {
            db.ref(`exams/${currentExamCode}/live_texts/${rawName}/history`).on('value', (snapshot) => {
                const historyData = snapshot.val();
                const labels = [];
                const wordCounts = [];

                if (historyData) {
                    Object.values(historyData).forEach(point => {
                        labels.push(point.time);
                        wordCounts.push(point.words);
                    });
                }

                const ctx = document.getElementById('studentProgressChart').getContext('2d');

                if (progressChart) {
                    progressChart.destroy();
                }

                progressChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: `Ordutvikling for ${displayName}`,
                            data: wordCounts,
                            borderColor: '#0284c7',
                            backgroundColor: 'rgba(2, 132, 199, 0.08)',
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.3,
                            pointRadius: 4,
                            pointBackgroundColor: '#0284c7'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, position: 'top' }
                        },
                        scales: {
                            x: { title: { display: true, text: 'Klokkeslett' } },
                            y: { title: { display: true, text: 'Antall ord' }, beginAtZero: true }
                        }
                    }
                });
            });
        }
    </script>
</body>
</html>
