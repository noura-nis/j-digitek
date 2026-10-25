# -*- coding: utf-8 -*-
"""
J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan
Journal of Digital Innovation and Applied Engineering Technology
Pimpinan Redaksi (Editor-in-Chief): Ir. Nor Anisa, S.Kom., M.Kom.
Desain Terinspirasi OJS 3.5 Gaudeamus Style & Tailwind CSS (Deep Ocean Navy #0B4460 & Golden Amber #f59e0b)
Backend: Supabase Cloud PostgreSQL
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.parse
import ssl
from datetime import datetime
import gradio as gr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ZeroGPU Helper
try:
    import spaces
    has_spaces = True
except Exception:
    has_spaces = False

def gpu_fn(fn):
    if has_spaces:
        return spaces.GPU(fn)
    return fn

# Konfigurasi Supabase Cloud PostgreSQL
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hgfftqiyqowuvpwiybhs.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhnZmZ0cWl5cW93dXZwd2l5YmhzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MjM4MTMzNCwiZXhwIjoyMTA3OTU3MzM0fQ.bmLAmDCizeTS7KY2JWp3mG2YcMMllb_vhe0FXpkirW0")
EDITOR_PIN = os.environ.get("EDITOR_PIN", "admin2026")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def query_supabase(endpoint, method="GET", data=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else []
    except Exception as e:
        print(f"[Supabase Error] {e}")
        return None

def get_all_articles():
    res = query_supabase("j_digitek_articles?select=*&order=id.desc")
    return res if res is not None else []

def get_published_articles(selected_track="Semua Track"):
    endpoint = "j_digitek_articles?status=eq.Published&order=id.asc"
    if selected_track and selected_track != "Semua Track":
        track_encoded = urllib.parse.quote(selected_track)
        endpoint += f"&track=eq.{track_encoded}"
    res = query_supabase(endpoint)
    return res if res is not None else []

@gpu_fn
def submit_manuscript(title, authors, affiliation, email, track, abstract, keywords, file_obj):
    if not title or not authors or not abstract or not track:
        return "⚠️ Mohon lengkapi seluruh formulir bertanda wajib (Judul Naskah, Penulis, Bidang Fokus/Track, dan Abstrak)."

    pdf_base64 = ""
    pdf_filename = ""
    if file_obj is not None:
        try:
            filepath = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
            pdf_filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pdf_filename = "naskah_terlampir.pdf"

    payload = {
        "title": title.strip(),
        "authors": authors.strip(),
        "affiliation": affiliation.strip() if affiliation else "Universitas Sari Mulia",
        "email": email.strip() if email else "-",
        "track": track,
        "abstract": abstract.strip(),
        "keywords": keywords.strip() if keywords else "-",
        "pdf_filename": pdf_filename,
        "pdf_base64": pdf_base64,
        "status": "Submitted",
        "volume": "1",
        "issue": "1",
        "year": "2026",
        "reviewer_notes": "Naskah berhasil didaftarkan ke sistem OJS J-DIGITEK dan siap diverifikasi oleh Dewan Redaksi."
    }

    res = query_supabase("j_digitek_articles", method="POST", data=payload)
    if res and len(res) > 0:
        art_id = res[0].get("id")
        return f"""✅ BUKTI TANDA TERIMA PENGIRIMAN NASKAH (SUBMISSION RECEIPT)
===================================================================
No. Registrasi OJS : J-DIGITEK-2026-{art_id:04d}
Judul Naskah       : {title}
Penulis Utama      : {authors}
Bidang Fokus/Track : {track}
Afiliasi Institusi : {affiliation or 'Universitas Sari Mulia'}
Status Naskah      : Submitted (Dalam Antrean Telaah Dewan Redaksi)
Tanggal Pengajuan  : {datetime.now().strftime('%d %B %Y, %H:%M')} WITA

Naskah Anda telah terdaftar permanen di basis data Cloud J-DIGITEK.
Pimpinan Redaksi (Ir. Nor Anisa, S.Kom., M.Kom.) akan meninjau kelayakan naskah melalui proses Double-Blind Peer Review."""
    else:
        return "❌ Terjadi kendala saat menyimpan naskah ke database Cloud. Silakan coba kembali."

def verify_editor_and_load(pin):
    if pin != EDITOR_PIN:
        return "❌ PIN Akses Salah! Hanya Dewan Redaksi yang memiliki otorisasi akses.", []
    articles = get_all_articles()
    table_data = []
    for a in articles:
        table_data.append([
            str(a.get("id")),
            a.get("title", "")[:50] + "...",
            a.get("authors", "")[:30],
            a.get("track", "")[:28],
            a.get("status", "Submitted"),
            a.get("created_at", "2026-10-25")[:10]
        ])
    return f"🟢 Akses Diterima! Selamat Datang, Bu Nor Anisa. Terdapat {len(articles)} naskah dalam pangkalan data editorial.", table_data

def load_single_article(pin, article_id):
    if pin != EDITOR_PIN:
        return "Akses ditolak.", "", "Submitted", "", ""
    if not article_id:
        return "Masukkan ID naskah yang ingin ditelaah.", "", "Submitted", "", ""
    try:
        aid = int(article_id)
    except:
        return "ID tidak valid.", "", "Submitted", "", ""
    res = query_supabase(f"j_digitek_articles?id=eq.{aid}")
    if not res or len(res) == 0:
        return f"Naskah ID #{aid} tidak ditemukan.", "", "Submitted", "", ""
    art = res[0]
    detail = f"""📄 RINCIAN DOKUMEN NASKAH #{art.get('id')}
--------------------------------------------------
Judul     : {art.get('title')}
Penulis   : {art.get('authors')}
Afiliasi  : {art.get('affiliation')}
Email     : {art.get('email')}
Track     : {art.get('track')}
File PDF  : {art.get('pdf_filename') or 'Tidak melampirkan berkas'}
Kata Kunci: {art.get('keywords')}"""
    return detail, art.get("abstract", ""), art.get("status", "Submitted"), art.get("reviewer_notes", ""), art.get("keywords", "")

def update_article_decision(pin, article_id, new_status, notes):
    if pin != EDITOR_PIN:
        return "❌ Akses ditolak. PIN salah.", []
    if not article_id:
        return "❌ Masukkan ID naskah terlebih dahulu.", []
    try:
        aid = int(article_id)
    except:
        return "❌ ID Naskah harus berupa angka.", []

    payload = {
        "status": new_status,
        "reviewer_notes": notes
    }
    res = query_supabase(f"j_digitek_articles?id=eq.{aid}", method="PATCH", data=payload)
    if res is not None:
        msg = f"✅ Sukses! Naskah #{aid} resmi diubah statusnya menjadi: [{new_status}]."
        _, updated_table = verify_editor_and_load(pin)
        return msg, updated_table
    return "❌ Gagal memperbarui status di database.", []

def render_published_html(selected_track):
    articles = get_published_articles(selected_track)
    if not articles:
        return """
        <div class="bg-white border-2 border-dashed border-slate-300 rounded-2xl p-10 text-center my-6 shadow-sm">
            <div class="w-16 h-16 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl border border-amber-200 shadow-inner">
                <i class="fa-solid fa-scroll"></i>
            </div>
            <span class="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 mb-3">
                <i class="fa-solid fa-bullhorn text-amber-600"></i> CALL FOR PAPERS: VOL. 1 NO. 1 (2026)
            </span>
            <h3 class="text-xl font-bold text-[#0B4460] mb-2 font-serif">Belum Ada Naskah yang Diterbitkan</h3>
            <p class="text-slate-600 text-sm max-w-2xl mx-auto leading-relaxed mb-6">
                Jurnal <b>J-DIGITEK (Journal of Digital Innovation and Applied Engineering Technology)</b> saat ini sedang dalam masa penerimaan naskah artikel ilmiah untuk <b>Volume 1 Nomor 1 (Edisi Perdana 2026)</b>. Naskah yang disubmit oleh mahasiswa, dosen, atau peneliti akan melalui proses <i>Double-Blind Peer Review</i> di bawah koordinasi Pimpinan Redaksi <b>Ir. Nor Anisa, S.Kom., M.Kom.</b>
            </p>
            
            <div class="grid grid-cols-1 md:grid-cols-4 gap-3 max-w-3xl mx-auto text-left mb-6">
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                    <span class="text-xs text-slate-400 font-semibold uppercase block">Batas Pengajuan</span>
                    <span class="text-sm font-bold text-slate-800">15 Maret 2026</span>
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                    <span class="text-xs text-slate-400 font-semibold uppercase block">Masa Telaah</span>
                    <span class="text-sm font-bold text-slate-800">14 Hari Kerja</span>
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                    <span class="text-xs text-slate-400 font-semibold uppercase block">Camera Ready</span>
                    <span class="text-sm font-bold text-slate-800">5 April 2026</span>
                </div>
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                    <span class="text-xs text-slate-400 font-semibold uppercase block">Terbit Perdana</span>
                    <span class="text-sm font-bold text-[#0B4460]">25 April 2026</span>
                </div>
            </div>

            <div class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-[#0B4460] text-white shadow-md hover:bg-[#08344a] transition-all cursor-pointer">
                <i class="fa-solid fa-paper-plane text-amber-400"></i> Silakan Kirim Naskah Melalui Tab 'Make a Submission'
            </div>
        </div>
        """

    html = "<div class='flex flex-col gap-5 my-4'>"
    for a in articles:
        title = a.get("title", "")
        authors = a.get("authors", "")
        affiliation = a.get("affiliation", "Universitas Sari Mulia")
        abstract = a.get("abstract", "")
        track = a.get("track", "")
        vol = a.get("volume", "1")
        issue = a.get("issue", "1")
        year = a.get("year", "2026")
        apa = f"{authors} ({year}). {title}. J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan, {vol}({issue})."

        html += f"""
        <div class="bg-white border border-slate-200 border-l-4 border-l-[#0B4460] rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
            <div class="flex flex-wrap justify-between items-center gap-2 mb-3">
                <span class="bg-blue-50 text-[#0B4460] border border-blue-200 px-3 py-1 rounded-full text-xs font-bold tracking-wide">
                    <i class="fa-solid fa-tag text-amber-500 mr-1"></i> {track}
                </span>
                <span class="text-slate-500 text-xs font-medium">
                    <i class="fa-regular fa-calendar-check mr-1"></i> Vol. {vol} No. {issue} ({year}) &bull; Peer-Reviewed
                </span>
            </div>
            <h3 class="text-lg font-bold text-[#0B4460] hover:text-[#08344a] transition-colors mb-2 font-serif leading-snug">
                {title}
            </h3>
            <p class="text-slate-700 text-sm mb-3">
                <i class="fa-solid fa-user-pen text-slate-400 mr-1.5"></i> <b>{authors}</b>
                <span class="text-slate-500 text-xs ml-2">({affiliation})</span>
            </p>
            <div class="bg-slate-50 border border-slate-100 rounded-lg p-4 mb-4 text-xs text-slate-600 leading-relaxed">
                <span class="font-bold text-slate-700 uppercase tracking-wider block mb-1">Abstrak:</span>
                {abstract}
            </div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <div class="text-xs text-slate-500 font-mono bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
                    DOI: 10.58471/j-digitek.v{vol}i{issue}.{a.get('id', '1')}
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs text-slate-500 italic mr-2">Sitasi APA 7th Ready</span>
                    <a href="#" class="inline-flex items-center gap-1.5 bg-[#0B4460] hover:bg-[#08344a] text-white text-xs font-bold px-3.5 py-1.5 rounded-lg shadow-sm transition-all">
                        <i class="fa-solid fa-file-pdf text-amber-400"></i> Unduh PDF
                    </a>
                </div>
            </div>
        </div>
        """
    html += "</div>"
    return html

# 17 Matakuliah Terapan Bu Nor Anisa
TRACKS_LIST = [
    "Semua Track",
    "1. Pengantar IoT (Internet of Things)",
    "2. Big Data Analytics",
    "3. Testing dan Implementasi Sistem",
    "4. Transformasi Digital",
    "5. Jaringan Komputer & Cyber Security",
    "6. Interaksi Manusia dan Komputer (IMK)",
    "7. Metode Penelitian IT",
    "8. Bisnis Digital & Technopreneurship",
    "9. Pengembangan Aplikasi Game",
    "10. UI/UX Design & User Research",
    "11. Software Quality Assurance",
    "12. Kewirausahaan Digital",
    "13. Digital Innovation & Product Tech",
    "14. Sistem Pendukung Keputusan (SPK)",
    "15. Digital Community & Social Informatics",
    "16. Cloud Computing Architecture",
    "17. Layanan Virtual Machine & DevOps"
]

# Custom CSS Tailored for OJS 3.5 Gaudeamus Style + Modern Tailwind Feel
ojs_custom_css = """
/* Reset & Base Styling */
:root, html, body {
    color-scheme: light !important;
    background-color: #f4f7fb !important;
    color: #1e293b !important;
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
}

body {
    background-image: 
        radial-gradient(#cbd5e1 0.75px, transparent 0.75px), 
        radial-gradient(#cbd5e1 0.75px, #f4f7fb 0.75px) !important;
    background-size: 30px 30px !important;
    background-position: 0 0, 15px 15px !important;
}

/* Gradio Container Overrides */
.gradio-container {
    max-width: 1320px !important;
    width: 100% !important;
    margin: 0 auto !important;
    padding: 0 16px 40px 16px !important;
    background: transparent !important;
}

/* Sembunyikan Footer Default Gradio Secara Permanen */
footer,
.gradio-container footer,
div[data-testid="footer"],
.footer,
div[class*="footer"],
a[href*="gradio.app"],
a[href*="huggingface.co/spaces"],
button[aria-label="Settings"],
.api-docs,
.svelte-10p0y76,
.svelte-1t38q2d {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Custom Gradio Tabs - OJS Gaudeamus Tailwind Style */
.gradio-container .tabs {
    border-bottom: 2px solid #cbd5e1 !important;
    gap: 6px !important;
    margin-bottom: 24px !important;
    background: transparent !important;
    display: flex !important;
    flex-wrap: wrap !important;
}

.gradio-container .tabs > button {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    color: #475569 !important;
    padding: 10px 18px !important;
    border-radius: 10px 10px 0 0 !important;
    border: 1px solid #cbd5e1 !important;
    border-bottom: none !important;
    background: #ffffff !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}

.gradio-container .tabs > button:hover {
    color: #0B4460 !important;
    background: #f1f5f9 !important;
    border-color: #94a3b8 !important;
}

.gradio-container .tabs > button.selected {
    color: #ffffff !important;
    background: linear-gradient(135deg, #0B4460 0%, #08344a 100%) !important;
    border-color: #0B4460 !important;
    box-shadow: 0 4px 10px rgba(11, 68, 96, 0.25) !important;
}

/* Input & Form Elements Styling */
.gradio-container input[type="text"],
.gradio-container input[type="password"],
.gradio-container input[type="email"],
.gradio-container textarea,
.gradio-container select {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 0.92rem !important;
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    transition: all 0.15s ease-in-out !important;
}

.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
    border-color: #0B4460 !important;
    box-shadow: 0 0 0 3px rgba(11, 68, 96, 0.15) !important;
    outline: none !important;
}

.gradio-container label span {
    font-size: 0.86rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    margin-bottom: 4px !important;
}

/* Buttons */
.gradio-container .gr-button {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

.gradio-container .gr-button-primary {
    background: linear-gradient(135deg, #0B4460 0%, #08344a 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(11, 68, 96, 0.25) !important;
}

.gradio-container .gr-button-primary:hover {
    background: linear-gradient(135deg, #08344a 0%, #052231 100%) !important;
    box-shadow: 0 6px 16px rgba(11, 68, 96, 0.35) !important;
    transform: translateY(-1px) !important;
}
"""

# HTML Head Injection for Tailwind CDN, FontAwesome, Google Fonts
custom_head = """
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&display=swap" rel="stylesheet">
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f0f5f9',
          100: '#e1ebf2',
          200: '#c3d7e5',
          300: '#95b9d3',
          400: '#5f94bc',
          500: '#3974a3',
          600: '#275b87',
          700: '#1e486d',
          800: '#0B4460',
          900: '#08344a',
          950: '#041d2b',
        },
        gold: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['Merriweather', 'Georgia', 'serif'],
      }
    }
  }
}
</script>
"""

with gr.Blocks(title="J-DIGITEK: Journal of Digital Innovation and Applied Engineering Technology", head=custom_head) as app:
    # Injeksi CSS Custom & Tailwind Failsafe
    gr.HTML(f"""
    <style>{ojs_custom_css}</style>
    <script>
    if (!window.tailwind) {{
        var s = document.createElement('script');
        s.src = 'https://cdn.tailwindcss.com';
        document.head.appendChild(s);
    }}
    </script>
    """)

    # 1. TOP BAR UTILITY OJS (Standard OJS 3.5 Top Bar)
    gr.HTML("""
    <div class="bg-[#08344a] text-slate-300 text-xs py-2 px-4 sm:px-6 rounded-t-xl flex flex-wrap justify-between items-center border-b border-white/10 mt-3 shadow-sm">
        <div class="flex items-center gap-3">
            <span class="inline-flex items-center gap-1.5 font-semibold text-white">
                <i class="fa-solid fa-graduation-cap text-amber-400"></i> OPEN JOURNAL SYSTEMS 3.5
            </span>
            <span class="hidden md:inline text-slate-500">&bull;</span>
            <span class="hidden md:inline text-slate-400">Open Access Academic Portal</span>
            <span class="hidden md:inline text-slate-500">&bull;</span>
            <span class="hidden lg:inline text-slate-400">Creative Commons Attribution 4.0 (CC BY 4.0)</span>
        </div>
        <div class="flex items-center gap-4 text-xs font-medium">
            <span class="text-amber-300"><i class="fa-regular fa-id-badge mr-1"></i> E-ISSN: 2988-8212</span>
            <span class="hidden sm:inline text-slate-400">P-ISSN: 2988-8204</span>
            <span class="bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded text-[11px] font-bold">
                VOL. 1 NO. 1 (2026)
            </span>
        </div>
    </div>
    """)

    # 2. MAIN HEADER OJS GAUDEAMUS STYLE (Deep Ocean Navy Gradient)
    gr.HTML("""
    <div class="bg-gradient-to-r from-[#0B4460] via-[#08344a] to-[#041d2b] text-white p-6 sm:p-8 rounded-b-xl shadow-lg mb-6 border-t-2 border-amber-400">
        <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
            <div class="flex items-start gap-4">
                <div class="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-amber-400 to-amber-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-amber-900/40 shrink-0 border-2 border-white/20">
                    <i class="fa-solid fa-microchip text-3xl sm:text-4xl text-[#08344a]"></i>
                </div>
                <div>
                    <div class="inline-flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold text-amber-300 mb-2 border border-white/10">
                        <i class="fa-solid fa-certificate"></i> JURNAL ILMIAH NASIONAL TERINDEKS
                    </div>
                    <h1 class="text-2xl sm:text-4xl font-extrabold tracking-tight font-serif text-white">
                        J-DIGITEK
                    </h1>
                    <p class="text-base sm:text-lg font-medium text-amber-400 mt-0.5">
                        Journal of Digital Innovation and Applied Engineering Technology
                    </p>
                    <p class="text-xs sm:text-sm text-slate-300 mt-1 max-w-3xl leading-relaxed">
                        Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan &bull; Program Studi Teknologi Informasi, Universitas Sari Mulia &bull; Pimpinan Redaksi (Editor-in-Chief): <b class="text-white font-semibold">Ir. Nor Anisa, S.Kom., M.Kom.</b>
                    </p>
                </div>
            </div>
            
            <div class="flex flex-wrap lg:flex-col gap-2 shrink-0 self-stretch lg:self-auto justify-end">
                <div class="bg-white/10 backdrop-blur-md border border-white/15 rounded-xl p-3 text-center sm:text-right">
                    <span class="text-amber-400 font-bold text-xs uppercase tracking-wider block">
                        <i class="fa-solid fa-shield-halved mr-1"></i> Double-Blind Peer Review
                    </span>
                    <span class="text-slate-200 text-xs block mt-0.5">
                        Free Article Processing Charge (APC: Rp 0)
                    </span>
                </div>
                <div class="bg-amber-500/20 border border-amber-400/40 rounded-xl p-2.5 text-center sm:text-right">
                    <span class="text-xs text-amber-300 font-bold">
                        <i class="fa-solid fa-database mr-1"></i> SINTA & GARUDA Preparation
                    </span>
                </div>
            </div>
        </div>

        <!-- Secondary Navbar Links -->
        <div class="mt-6 pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs font-bold text-slate-200">
            <div class="flex flex-wrap items-center gap-4 sm:gap-6 uppercase tracking-wider">
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-house mr-1 text-amber-400"></i> Home</span>
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-circle-info mr-1 text-amber-400"></i> About</span>
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-bullhorn mr-1 text-amber-400"></i> Call for Papers</span>
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-book-open mr-1 text-amber-400"></i> Current Issue</span>
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-box-archive mr-1 text-amber-400"></i> Archives</span>
                <span class="hover:text-amber-300 transition-colors cursor-pointer"><i class="fa-solid fa-users mr-1 text-amber-400"></i> Editorial Team</span>
            </div>
            <div class="text-slate-400 font-normal">
                Banjarmasin, Kalimantan Selatan &bull; Indonesia
            </div>
        </div>
    </div>
    """)

    # 3. THREE FEATURE CARDS (HERO ANNOUNCEMENTS - MATCHING IJCITSM STYLE)
    gr.HTML("""
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <!-- Feature 1: Call for Papers -->
        <div class="bg-white border-t-4 border-t-amber-500 rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition-all">
            <div class="flex items-center gap-2 mb-2">
                <span class="bg-amber-100 text-amber-800 text-[11px] font-extrabold px-2.5 py-0.5 rounded-full">
                    <i class="fa-solid fa-bullhorn mr-1"></i> CALL FOR PAPERS
                </span>
                <span class="text-xs text-slate-400">Vol. 1 No. 1 (2026)</span>
            </div>
            <h3 class="text-base font-bold text-[#0B4460] font-serif mb-1.5">
                Penerimaan Naskah Edisi Perdana 2026
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
                Mengundang naskah tugas akhir mahasiswa, penelitian dosen, dan praktisi di bidang inovasi digital. Telaah cepat & bebas biaya APC.
            </p>
        </div>

        <!-- Feature 2: 17 Tracks Scope -->
        <div class="bg-white border-t-4 border-t-[#0B4460] rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition-all">
            <div class="flex items-center gap-2 mb-2">
                <span class="bg-blue-100 text-[#0B4460] text-[11px] font-extrabold px-2.5 py-0.5 rounded-full">
                    <i class="fa-solid fa-layer-group mr-1"></i> 17 BIDANG FOKUS
                </span>
                <span class="text-xs text-slate-400">Rekayasa Terapan</span>
            </div>
            <h3 class="text-base font-bold text-[#0B4460] font-serif mb-1.5">
                Cakupan Keilmuan Komprehensif
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
                Mencakup IoT, Big Data, Testing, Transformasi Digital, Game Dev, IMK, UI/UX, Cloud Computing, dan Sistem Pendukung Keputusan.
            </p>
        </div>

        <!-- Feature 3: Indexing & Accreditation -->
        <div class="bg-white border-t-4 border-t-emerald-600 rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition-all">
            <div class="flex items-center gap-2 mb-2">
                <span class="bg-emerald-100 text-emerald-800 text-[11px] font-extrabold px-2.5 py-0.5 rounded-full">
                    <i class="fa-solid fa-award mr-1"></i> REPUTASI ILMIAH
                </span>
                <span class="text-xs text-slate-400">SINTA Preparation</span>
            </div>
            <h3 class="text-base font-bold text-[#0B4460] font-serif mb-1.5">
                Standar Akreditasi Nasional & DOI
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
                Tata kelola OJS 3.5 berstandar Arjuna SINTA, Crossref DOI, Google Scholar, GARUDA, dan integrasi Mendeley/Zotero.
            </p>
        </div>
    </div>
    """)

    # 4. TWO-COLUMN MAIN LAYOUT (LEFT 75% CONTENT + RIGHT 25% OJS SIDEBAR)
    with gr.Row():
        # =========================================================================
        # KOLOM KIRI (KONTEN UTAMA JURNAL - 75%)
        # =========================================================================
        with gr.Column(scale=3):
            with gr.Tabs():
                # -------------------------------------------------------------
                # TAB 1: HOME & CURRENT ISSUE (TERBITAN TERKINI)
                # -------------------------------------------------------------
                with gr.Tab("📖 Beranda & Terbitan (Home & Current Issue)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <!-- Current Issue Header Banner -->
                        <div class="border-b border-slate-200 pb-5 mb-5">
                            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div>
                                    <span class="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                        <i class="fa-solid fa-star text-amber-500"></i> Terbitan Terkini (Current Issue)
                                    </span>
                                    <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                        Vol. 1 No. 1 (2026): Edisi Perdana (Inaugural Issue)
                                    </h2>
                                    <p class="text-xs text-slate-500 mt-1">
                                        Diterbitkan: 25 April 2026 &bull; Frekuensi: 2 Kali Setahun (April & Oktober)
                                    </p>
                                </div>
                                <div class="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-right">
                                    <span class="text-xs text-slate-400 font-semibold block uppercase">DOI Issue</span>
                                    <span class="text-xs font-mono font-bold text-[#0B4460]">10.58471/j-digitek.v1i1</span>
                                </div>
                            </div>
                        </div>

                        <!-- Issue Description & Cover Mockup -->
                        <div class="flex flex-col md:flex-row gap-6 items-center bg-slate-50 border border-slate-200 rounded-xl p-5 mb-6">
                            <div class="w-36 h-48 bg-gradient-to-br from-[#0B4460] via-[#08344a] to-[#041d2b] rounded-lg shadow-md border-2 border-amber-400 flex flex-col justify-between p-3 text-white text-center shrink-0">
                                <div class="text-[10px] tracking-widest text-amber-300 font-bold uppercase border-b border-white/20 pb-1">
                                    J-DIGITEK
                                </div>
                                <div>
                                    <div class="text-lg font-serif font-black text-amber-400">VOL. 1</div>
                                    <div class="text-xs text-slate-200">NO. 1 &bull; 2026</div>
                                    <div class="text-[9px] text-slate-300 mt-1">Inaugural Edition</div>
                                </div>
                                <div class="text-[8px] text-slate-400 border-t border-white/20 pt-1">
                                    E-ISSN: 2988-8212
                                </div>
                            </div>
                            <div class="flex-1">
                                <h3 class="text-base font-bold text-[#0B4460] font-serif mb-2">
                                    Fokus Edisi: Akselerasi Transformasi Digital & Rekayasa Perangkat Lunak Terapan
                                </h3>
                                <p class="text-xs text-slate-600 leading-relaxed mb-3">
                                    Edisi perdana <b>J-DIGITEK (Volume 1 Nomor 1, 2026)</b> menghimpun karya ilmiah inovatif mahasiswa dan dosen pembimbing di lingkungan Universitas Sari Mulia serta kolaborator eksternal. Fokus riset mencakup penerapan Internet of Things (IoT), arsitektur Big Data, pengujian perangkat lunak sistematis, dan desain antarmuka pengguna (UI/UX) berbasis kebutuhan masyarakat modern.
                                </p>
                                <div class="flex flex-wrap gap-2 text-[11px]">
                                    <span class="bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-md font-semibold">
                                        <i class="fa-solid fa-check text-emerald-600 mr-1"></i> Peer-Reviewed
                                    </span>
                                    <span class="bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-md font-semibold">
                                        <i class="fa-solid fa-lock-open text-amber-600 mr-1"></i> Open Access
                                    </span>
                                    <span class="bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-md font-semibold">
                                        <i class="fa-solid fa-file-shield text-blue-600 mr-1"></i> Similarity &lt; 20%
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Section: Explore Articles Header -->
                        <div class="flex justify-between items-center border-b-2 border-slate-200 pb-3 mb-4">
                            <h3 class="text-lg font-bold text-[#0B4460] font-serif flex items-center gap-2">
                                <i class="fa-solid fa-layer-group text-amber-500"></i> Daftar Artikel (Articles / Table of Contents)
                            </h3>
                            <span class="text-xs text-slate-400">Total Naskah Terbit: 0 (Call for Papers Active)</span>
                        </div>
                    </div>
                    """)

                    track_filter = gr.Dropdown(
                        choices=TRACKS_LIST,
                        value="Semua Track",
                        label="Saring Artikel Berdasarkan Bidang Fokus (Filter by Research Track)",
                        interactive=True
                    )
                    articles_html = gr.HTML(value=render_published_html("Semua Track"))
                    track_filter.change(fn=render_published_html, inputs=track_filter, outputs=articles_html)

                # -------------------------------------------------------------
                # TAB 2: FOCUS AND SCOPE (17 MATAKULIAH BU NOR ANISA)
                # -------------------------------------------------------------
                with gr.Tab("🎯 Fokus & Ruang Lingkup (Focus & Scope)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <div class="border-b border-slate-200 pb-4 mb-5">
                            <span class="bg-blue-100 text-[#0B4460] text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                <i class="fa-solid fa-crosshairs text-amber-500"></i> Aims & Scope
                            </span>
                            <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                Fokus dan Ruang Lingkup Ilmiah (17 Bidang Keilmuan)
                            </h2>
                            <p class="text-xs text-slate-600 mt-1 max-w-3xl leading-relaxed">
                                Jurnal <b>J-DIGITEK</b> menerima naskah hasil penelitian empiris, studi kasus, perancangan sistem, dan pengembangan purwarupa teknologi terapan yang selaras dengan 17 rumpun matakuliah yang diampu oleh <b>Ir. Nor Anisa, S.Kom., M.Kom.</b>:
                            </p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <!-- Track 1 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">1</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Pengantar IoT</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Internet of Things, sensor nodes (ESP32/Arduino), MQTT, protokol komunikasi nirkabel, smart home, smart agriculture.
                                </p>
                            </div>

                            <!-- Track 2 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">2</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Big Data Analytics</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Pengolahan data skala besar, data pipeline, analitik prediktif, Hadoop/Spark, visualisasi analitik bisnis dan sains.
                                </p>
                            </div>

                            <!-- Track 3 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">3</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Testing & Implementasi</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Black-box testing, automated testing (Selenium/Cypress), unit testing, load testing, dan integrasi sistem perangkat lunak.
                                </p>
                            </div>

                            <!-- Track 4 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">4</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Transformasi Digital</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Digital maturity model, digitalisasi proses bisnis instansi/UMKM, tata kelola TI modern, dan smart governance.
                                </p>
                            </div>

                            <!-- Track 5 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">5</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Jaringan Komputer</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Routing & switching, infrastruktur jaringan LAN/WAN, cyber security dasar, firewall, dan optimalisasi bandwidth.
                                </p>
                            </div>

                            <!-- Track 6 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">6</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Interaksi Manusia & Komputer</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Usability testing (SUS/UEQ), cognitive ergonomics, aksesibilitas aplikasi, dan evaluasi pengalaman interaksi pengguna.
                                </p>
                            </div>

                            <!-- Track 7 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">7</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Metode Penelitian IT</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Systematic Literature Review (SLR), analisis bibliometrik, metodologi riset eksperimen, dan sintesis literatur ilmiah.
                                </p>
                            </div>

                            <!-- Track 8 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">8</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Bisnis Digital</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    E-commerce architectures, platform bisnis online, payment gateway, omnichannel strategy, dan monetisasi teknologi.
                                </p>
                            </div>

                            <!-- Track 9 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-emerald-600 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center text-sm font-bold">9</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Aplikasi Game</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Pengembangan game 2D/3D (Godot/Unity), gamifikasi pembelajaran (educational games), AI NPC, dan game physics.
                                </p>
                            </div>

                            <!-- Track 10 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">10</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">UI/UX Design</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Design Thinking, wireframing, high-fidelity Figma prototyping, design system, dan user persona research.
                                </p>
                            </div>

                            <!-- Track 11 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">11</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Software Testing (QA)</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Standar ISO 25010, bug tracking management, regression testing, continuous testing dalam pipeline CI/CD DevOps.
                                </p>
                            </div>

                            <!-- Track 12 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">12</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Kewirausahaan Digital</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Inkubasi startup teknologi, lean canvas validation, customer discovery, scale-up produk digital lokal dan nasional.
                                </p>
                            </div>

                            <!-- Track 13 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">13</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Digital Innovation</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Teknologi disruptif, manajemen inovasi produk perangkat lunak, adopsi teknologi cerdas, dan rekayasa terapan.
                                </p>
                            </div>

                            <!-- Track 14 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-indigo-600 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-800 flex items-center justify-center text-sm font-bold">14</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Sistem Pendukung Keputusan</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Implementasi metode multi-kriteria: AHP, TOPSIS, SAW, SMART, MOORA, WP untuk optimasi keputusan manajerial dan teknis.
                                </p>
                            </div>

                            <!-- Track 15 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-amber-500 rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center text-sm font-bold">15</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Digital Community</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Informatika sosial, literasi digital masyarakat, pemberdayaan komunitas desa melalui platform digital terdesentralisasi.
                                </p>
                            </div>

                            <!-- Track 16 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">16</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Cloud Computing</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Arsitektur cloud (AWS/GCP/Azure), containerization (Docker/Kubernetes), microservices, dan serverless deployment.
                                </p>
                            </div>

                            <!-- Track 17 -->
                            <div class="bg-slate-50 border border-slate-200 border-t-4 border-t-[#0B4460] rounded-xl p-4 hover:shadow-sm transition-all">
                                <div class="flex items-center gap-2.5 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-blue-100 text-[#0B4460] flex items-center justify-center text-sm font-bold">17</div>
                                    <h4 class="font-bold text-sm text-[#0B4460]">Virtual Machine & DevOps</h4>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">
                                    Virtualisasi hypervisor (Proxmox/ESXi/KVM), automasi infrastruktur, pipeline CI/CD, dan pemantauan sistem server.
                                </p>
                            </div>
                        </div>
                    </div>
                    """)

                # -------------------------------------------------------------
                # TAB 3: MAKE A SUBMISSION (FORM PENGAJUAN NASKAH)
                # -------------------------------------------------------------
                with gr.Tab("📝 Kirim Naskah (Make a Submission)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <div class="border-b border-slate-200 pb-4 mb-5">
                            <span class="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                <i class="fa-solid fa-file-arrow-up text-emerald-600"></i> Online Submission Portal
                            </span>
                            <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                Formulir Pengajuan Naskah Baru (Author Submission)
                            </h2>
                            <p class="text-xs text-slate-600 mt-1">
                                Pastikan naskah Anda telah disesuaikan dengan <b>Template Naskah J-DIGITEK (.docx)</b> dan memiliki kemiripan (similarity) maksimal 20% sebelum diajukan.
                            </p>
                        </div>

                        <!-- 4 Step Flow Info -->
                        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-6 bg-slate-50 border border-slate-200 rounded-xl p-4">
                            <div class="flex items-center gap-3">
                                <div class="w-7 h-7 rounded-full bg-[#0B4460] text-white flex items-center justify-center text-xs font-bold shrink-0">1</div>
                                <div class="text-xs">
                                    <b class="text-slate-800 block">Lengkapi Data</b>
                                    <span class="text-slate-500">Judul, Penulis, Abstrak</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-3">
                                <div class="w-7 h-7 rounded-full bg-[#0B4460] text-white flex items-center justify-center text-xs font-bold shrink-0">2</div>
                                <div class="text-xs">
                                    <b class="text-slate-800 block">Unggah Berkas</b>
                                    <span class="text-slate-500">File DOCX atau PDF</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-3">
                                <div class="w-7 h-7 rounded-full bg-[#0B4460] text-white flex items-center justify-center text-xs font-bold shrink-0">3</div>
                                <div class="text-xs">
                                    <b class="text-slate-800 block">Double-Blind Review</b>
                                    <span class="text-slate-500">14 Hari Kerja</span>
                                </div>
                            </div>
                            <div class="flex items-center gap-3">
                                <div class="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-bold shrink-0">4</div>
                                <div class="text-xs">
                                    <b class="text-slate-800 block">Penerbitan OJS</b>
                                    <span class="text-slate-500">DOI & SINTA Index</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """)

                    with gr.Row():
                        sub_title = gr.Textbox(
                            label="Judul Lengkap Naskah Artikel (Title in Indonesian / English)",
                            placeholder="Contoh: Implementasi Smart Monitoring Kualitas Air Berbasis ESP32 dan Arsitektur Cloud...",
                            scale=2
                        )
                        sub_track = gr.Dropdown(
                            choices=TRACKS_LIST[1:],
                            value=TRACKS_LIST[1],
                            label="Pilih Bidang Fokus Penelitian (Research Track)",
                            scale=1
                        )

                    with gr.Row():
                        sub_authors = gr.Textbox(
                            label="Nama Lengkap Penulis & Rekan (Authors & Degrees)",
                            placeholder="Contoh: Muhammad Ihsan, Ir. Nor Anisa, S.Kom., M.Kom.",
                            scale=1
                        )
                        sub_affiliation = gr.Textbox(
                            label="Afiliasi Institusi / Kampus (Affiliation)",
                            value="Program Studi Teknologi Informasi, Universitas Sari Mulia",
                            scale=1
                        )
                        sub_email = gr.Textbox(
                            label="Email Korespondensi Penulis (Corresponding Email)",
                            placeholder="penulis@unism.ac.id",
                            scale=1
                        )

                    sub_abstract = gr.TextArea(
                        label="Abstrak Naskah (Abstract - Minimal 150 Kata)",
                        placeholder="Uraikan ringkasan latar belakang, tujuan penelitian, metodologi yang diimplementasikan, hasil temuan terukur, serta simpulan inovasi...",
                        lines=5
                    )

                    with gr.Row():
                        sub_keywords = gr.Textbox(
                            label="Kata Kunci (Keywords - Minimal 3 kata dipisahkan tanda koma)",
                            placeholder="Internet of Things, ESP32, Cloud Computing, Sensor Air, Inovasi Digital",
                            scale=2
                        )
                        sub_file = gr.File(
                            label="Lampirkan Berkas Naskah (.docx / .pdf)",
                            file_types=[".pdf", ".docx"],
                            scale=1
                        )

                    submit_btn = gr.Button("🚀 Kirim Naskah ke Dewan Redaksi J-DIGITEK (Submit Manuscript)", variant="primary", size="lg")
                    sub_output = gr.Textbox(label="Status Bukti Tanda Terima Registrasi OJS (Submission Receipt)", lines=6, interactive=False)

                    submit_btn.click(
                        fn=submit_manuscript,
                        inputs=[sub_title, sub_authors, sub_affiliation, sub_email, sub_track, sub_abstract, sub_keywords, sub_file],
                        outputs=sub_output
                    )

                # -------------------------------------------------------------
                # TAB 4: EDITORIAL TEAM (DEWAN REDAKSI)
                # -------------------------------------------------------------
                with gr.Tab("👥 Dewan Redaksi (Editorial Team)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <div class="border-b border-slate-200 pb-4 mb-5">
                            <span class="bg-blue-100 text-[#0B4460] text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                <i class="fa-solid fa-users text-amber-500"></i> Board of Editors
                            </span>
                            <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                Dewan Redaksi & Tim Pengelola Jurnal
                            </h2>
                            <p class="text-xs text-slate-600 mt-1">
                                Pengelolaan penerbitan dan penjaminan mutu substansi naskah <b>J-DIGITEK</b> dipimpin oleh para akademisi dan pakar teknologi informasi terpercaya.
                            </p>
                        </div>

                        <!-- Editor-in-Chief Spotlight Card -->
                        <div class="bg-gradient-to-r from-slate-50 to-blue-50 border-2 border-[#0B4460]/20 rounded-2xl p-6 mb-6 shadow-sm flex flex-col md:flex-row items-center gap-6">
                            <div class="w-24 h-24 rounded-full bg-gradient-to-tr from-[#0B4460] to-amber-500 p-1 shrink-0 shadow-lg">
                                <div class="w-full h-full bg-white rounded-full flex items-center justify-center text-[#0B4460] text-3xl">
                                    <i class="fa-solid fa-user-tie"></i>
                                </div>
                            </div>
                            <div class="flex-1 text-center md:text-left">
                                <span class="bg-amber-400 text-[#08344a] text-xs font-extrabold px-3 py-0.5 rounded-full uppercase tracking-wider inline-block mb-1.5 shadow-sm">
                                    PIMPINAN REDAKSI (EDITOR-IN-CHIEF)
                                </span>
                                <h3 class="text-xl font-extrabold text-[#0B4460] font-serif">
                                    Ir. Nor Anisa, S.Kom., M.Kom.
                                </h3>
                                <p class="text-xs text-slate-700 font-medium mt-1">
                                    Program Studi Teknologi Informasi &bull; Universitas Sari Mulia, Banjarmasin, Indonesia
                                </p>
                                <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                                    Kepakaran: <i>Software Engineering, UI/UX Design, Cloud Infrastructure, IoT, dan Transformasi Digital Terapan</i>.
                                </p>
                                <div class="flex flex-wrap justify-center md:justify-start gap-2 mt-3 text-xs">
                                    <span class="bg-white border border-slate-200 px-2.5 py-1 rounded-md text-slate-700 font-semibold shadow-xs">
                                        <i class="fa-solid fa-envelope text-amber-500 mr-1"></i> editor@j-digitek.id
                                    </span>
                                    <span class="bg-white border border-slate-200 px-2.5 py-1 rounded-md text-slate-700 font-semibold shadow-xs">
                                        <i class="fa-solid fa-graduation-cap text-[#0B4460] mr-1"></i> Google Scholar Verified
                                    </span>
                                    <span class="bg-white border border-slate-200 px-2.5 py-1 rounded-md text-slate-700 font-semibold shadow-xs">
                                        <i class="fa-solid fa-award text-emerald-600 mr-1"></i> SINTA ID Ready
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Editorial Board Table -->
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-xs border border-slate-200 rounded-xl overflow-hidden">
                                <thead class="bg-[#08344a] text-white uppercase text-[11px] tracking-wider">
                                    <tr>
                                        <th class="p-3">Posisi Dewan Redaksi</th>
                                        <th class="p-3">Nama Lengkap & Gelar</th>
                                        <th class="p-3">Afiliasi Institusi</th>
                                        <th class="p-3">Bidang Kepakaran</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-200">
                                    <tr class="hover:bg-slate-50">
                                        <td class="p-3 font-bold text-[#0B4460]">Managing Editor</td>
                                        <td class="p-3 font-semibold">Dewan Redaksi TI UNISM</td>
                                        <td class="p-3">Universitas Sari Mulia</td>
                                        <td class="p-3">Manajemen Publikasi OJS & Tata Kelola Naskah</td>
                                    </tr>
                                    <tr class="hover:bg-slate-50">
                                        <td class="p-3 font-bold text-[#0B4460]">Section Editor (IoT & Cloud)</td>
                                        <td class="p-3 font-semibold">Tim Dosen Rumpun Jaringan</td>
                                        <td class="p-3">Universitas Sari Mulia</td>
                                        <td class="p-3">Internet of Things, Cloud Infrastructure & Networks</td>
                                    </tr>
                                    <tr class="hover:bg-slate-50">
                                        <td class="p-3 font-bold text-[#0B4460]">Section Editor (Software & UI/UX)</td>
                                        <td class="p-3 font-semibold">Tim Dosen Rumpun Rekayasa</td>
                                        <td class="p-3">Universitas Sari Mulia</td>
                                        <td class="p-3">Testing, Human-Computer Interaction & Quality Assurance</td>
                                    </tr>
                                    <tr class="hover:bg-slate-50">
                                        <td class="p-3 font-bold text-[#0B4460]">Layout & Copyeditor</td>
                                        <td class="p-3 font-semibold">Noura Studio Media Tim</td>
                                        <td class="p-3">Banjarmasin, Indonesia</td>
                                        <td class="p-3">Formatting Template, Crossref XML & Proofreading</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """)

                # -------------------------------------------------------------
                # TAB 5: AUTHOR GUIDELINES & ETHICS (PEDOMAN PENULISAN)
                # -------------------------------------------------------------
                with gr.Tab("📜 Panduan Penulis & Etika (Author Guidelines)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <div class="border-b border-slate-200 pb-4 mb-5">
                            <span class="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                <i class="fa-solid fa-book text-amber-600"></i> Publishing Standards
                            </span>
                            <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                Pedoman Penulisan & Etika Publikasi Ilmiah
                            </h2>
                            <p class="text-xs text-slate-600 mt-1">
                                Standar baku struktur naskah, sitasi rujukan, etika publikasi, dan ketentuan bebas plagiarisme untuk penulis.
                            </p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-700 leading-relaxed">
                            <div class="space-y-4">
                                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                    <h4 class="font-bold text-sm text-[#0B4460] mb-2 flex items-center gap-1.5">
                                        <i class="fa-solid fa-list-check text-amber-500"></i> Struktur Baku Naskah (IMRaD)
                                    </h4>
                                    <ol class="list-decimal pl-4 space-y-1">
                                        <li><b>Judul Naskah:</b> Maksimal 15 kata, lugas, informatif, dan tidak multitafsir.</li>
                                        <li><b>Abstrak:</b> 150-250 kata dalam 1 paragraf, memuat ringkasan latar belakang, metode, hasil, dan simpulan utama.</li>
                                        <li><b>Pendahuluan:</b> Menguraikan problem background, state-of-the-art, research gap, dan kontribusi kebaruan riset.</li>
                                        <li><b>Metodologi Penelitian:</b> Tahapan rancangan sistem, algoritma, arsitektur hardware/software, serta teknik pengujian.</li>
                                        <li><b>Hasil & Pembahasan:</b> Menyajikan data hasil uji dengan grafik/tabel serta analisis komparasi dengan studi terdahulu.</li>
                                        <li><b>Kesimpulan:</b> Menjawab rumusan masalah serta peluang tindak lanjut riset ke depan.</li>
                                    </ol>
                                </div>

                                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                    <h4 class="font-bold text-sm text-[#0B4460] mb-2 flex items-center gap-1.5">
                                        <i class="fa-solid fa-quote-left text-amber-500"></i> Format Sitasi & Rujukan (APA 7th)
                                    </h4>
                                    <p class="mb-2">
                                        Daftar pustaka wajib disusun menggunakan aplikasi <b>Reference Manager</b> (Mendeley, Zotero, atau EndNote) dengan gaya sitasi <b>APA 7th Edition</b>.
                                    </p>
                                    <div class="bg-white p-2.5 rounded border border-slate-200 font-mono text-[11px] text-slate-600">
                                        Anisa, N., & Prasetyo, E. (2025). IoT-Based Automated Monitoring for Sustainable Smart City. J-DIGITEK, 1(1), 1-10.
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-4">
                                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                    <h4 class="font-bold text-sm text-[#0B4460] mb-2 flex items-center gap-1.5">
                                        <i class="fa-solid fa-shield-virus text-emerald-600"></i> Kebijakan Plagiarisme & AI
                                    </h4>
                                    <p class="mb-2">
                                        Setiap naskah wajib melewati pemeriksaan orisinalitas melalui sistem <b>Turnitin / OpenPlag.id</b> dengan ambang batas kesamaan (similarity index) <b>maksimal 20%</b>.
                                    </p>
                                    <p>
                                        Pemanfaatan Generative AI hanya diperkenankan sebagai alat bantu penyempurnaan tata bahasa (grammar assistant). Seluruh ide gagasan, implementasi kode, dan interpretasi data mutlak menjadi tanggung jawab penulis manusia.
                                    </p>
                                </div>

                                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                    <h4 class="font-bold text-sm text-[#0B4460] mb-2 flex items-center gap-1.5">
                                        <i class="fa-solid fa-hand-holding-dollar text-amber-500"></i> Biaya Publikasi (Author Fees / APC)
                                    </h4>
                                    <p class="mb-2 font-semibold text-emerald-700">
                                        <i class="fa-solid fa-tag"></i> Gratis Biaya Publikasi (APC: Rp 0 / Free of Charge)
                                    </p>
                                    <p>
                                        Untuk Volume 1 Nomor 1 (Edisi Perdana 2026), seluruh proses pengajuan naskah (submission), penelaahan naskah (peer review), hingga penerbitan online open access tidak dipungut biaya apa pun bagi mahasiswa dan dosen.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    """)

                # -------------------------------------------------------------
                # TAB 6: EDITOR REVIEW DESK (PORTAL KHUSUS EDITOR BU NOR ANISA)
                # -------------------------------------------------------------
                with gr.Tab("🔐 Editorial Review Desk (Akses Editor)"):
                    gr.HTML("""
                    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
                        <div class="border-b border-slate-200 pb-4 mb-5">
                            <span class="bg-purple-100 text-purple-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider inline-flex items-center gap-1.5 mb-2">
                                <i class="fa-solid fa-lock text-purple-600"></i> Restricted Editorial Area
                            </span>
                            <h2 class="text-2xl font-extrabold text-[#0B4460] font-serif">
                                Portal Khusus Pimpinan Redaksi & Editor Desk
                            </h2>
                            <p class="text-xs text-slate-600 mt-1">
                                Digunakan oleh <b>Ir. Nor Anisa, S.Kom., M.Kom.</b> untuk memverifikasi naskah masuk, mengelola proses peer review, dan menerbitkan artikel ke OJS.
                            </p>
                        </div>
                    </div>
                    """)

                    with gr.Row():
                        pin_input = gr.Textbox(
                            label="Masukkan PIN Rahasia Editor (Editor PIN Access)",
                            type="password",
                            placeholder="Ketik PIN Otorisasi...",
                            scale=3
                        )
                        btn_login = gr.Button("🔑 Buka Antrean Naskah Masuk", variant="primary", scale=1)

                    ed_status = gr.Markdown()
                    ed_table = gr.Dataframe(
                        headers=["ID", "Judul Naskah", "Penulis", "Bidang Fokus/Track", "Status OJS", "Tanggal Pengajuan"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        interactive=False,
                        label="Daftar Antrean Seluruh Naskah Masuk (Supabase Real-Time Database)"
                    )

                    btn_login.click(
                        fn=verify_editor_and_load,
                        inputs=pin_input,
                        outputs=[ed_status, ed_table]
                    )

                    gr.HTML("<hr class='my-6 border-slate-200'>")

                    with gr.Row():
                        target_id = gr.Textbox(label="Ketik ID Naskah yang Ingin Ditelaah", placeholder="Contoh: 1", scale=1)
                        btn_load_art = gr.Button("🔍 Tampilkan Berkas Naskah", scale=1)

                    with gr.Row():
                        ed_detail = gr.Textbox(label="Metadata Naskah Lengkap", lines=6, scale=1)
                        ed_abstract = gr.TextArea(label="Isi Abstrak Naskah", lines=6, scale=2)

                    with gr.Row():
                        ed_decision = gr.Radio(
                            choices=["Submitted", "In Review", "Revision Required", "Accepted", "Published"],
                            label="Keputusan Editorial (Editorial Decision)",
                            value="Submitted"
                        )
                        ed_notes = gr.Textbox(
                            label="Catatan Reviewer / Dewan Redaksi untuk Penulis",
                            placeholder="Berikan arahan perbaikan format, pengujian sistem, atau kelayakan naskah...",
                            scale=2
                        )

                    btn_save_decision = gr.Button("💾 Simpan Keputusan Editorial & Perbarui Status OJS", variant="primary")
                    decision_result = gr.Textbox(label="Hasil Tindakan Editorial", interactive=False)

                    btn_load_art.click(
                        fn=load_single_article,
                        inputs=[pin_input, target_id],
                        outputs=[ed_detail, ed_abstract, ed_decision, ed_notes]
                    )

                    btn_save_decision.click(
                        fn=update_article_decision,
                        inputs=[pin_input, target_id, ed_decision, ed_notes],
                        outputs=[decision_result, ed_table]
                    )

        # =========================================================================
        # KOLOM KANAN (SIDEBAR KHAS OJS 3.5 GAUDEAMUS STYLE - 25%)
        # =========================================================================
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="flex flex-col gap-5">
                <!-- 1. MAKE A SUBMISSION CALL TO ACTION -->
                <div class="bg-gradient-to-br from-[#0B4460] to-[#08344a] rounded-2xl p-5 text-white shadow-md border-t-4 border-amber-400">
                    <span class="bg-amber-400 text-[#08344a] text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider inline-block mb-2">
                        ONLINE SUBMISSION
                    </span>
                    <h3 class="text-lg font-bold font-serif mb-1">Make a Submission</h3>
                    <p class="text-xs text-slate-300 leading-relaxed mb-4">
                        Kirimkan naskah penelitian Anda sekarang untuk edisi perdana Vol. 1 No. 1 (2026).
                    </p>
                    <ul class="text-xs text-slate-200 space-y-1.5 mb-4 pl-1">
                        <li class="flex items-center gap-2"><i class="fa-solid fa-check text-amber-400"></i> Naskah belum pernah terbit</li>
                        <li class="flex items-center gap-2"><i class="fa-solid fa-check text-amber-400"></i> Mengikuti template DOCX</li>
                        <li class="flex items-center gap-2"><i class="fa-solid fa-check text-amber-400"></i> Similarity &lt; 20% (Turnitin)</li>
                        <li class="flex items-center gap-2"><i class="fa-solid fa-check text-amber-400"></i> Referensi APA 7th Mendeley</li>
                    </ul>
                    <a href="#sub_title" class="block text-center bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-500 hover:to-amber-600 text-[#08344a] font-extrabold py-2.5 px-4 rounded-xl text-xs shadow-md transition-all">
                        <i class="fa-solid fa-paper-plane mr-1.5"></i> Submit Naskah Online
                    </a>
                </div>

                <!-- 2. ARTICLE TEMPLATE DOWNLOAD BLOCK -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <i class="fa-solid fa-download text-amber-500"></i> Template Naskah
                    </h4>
                    <div class="bg-slate-50 border border-slate-200 rounded-xl p-3.5 mb-3">
                        <div class="flex items-center gap-3">
                            <i class="fa-solid fa-file-word text-3xl text-blue-600"></i>
                            <div>
                                <b class="text-xs text-slate-800 block">J-DIGITEK Template (.docx)</b>
                                <span class="text-[11px] text-slate-500">Microsoft Word A4 &bull; 2 Kolom</span>
                            </div>
                        </div>
                    </div>
                    <a href="/file=Template_J-DIGITEK_2026.docx" target="_blank" class="block text-center bg-[#0B4460] hover:bg-[#08344a] text-white font-bold py-2 px-3 rounded-xl text-xs transition-colors shadow-sm">
                        <i class="fa-solid fa-file-arrow-down mr-1"></i> Unduh Template (.docx)
                    </a>
                </div>

                <!-- 3. SINTA & GARUDA ACCREDITATION SHOWCASE -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm text-center">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Akreditasi & Sertifikasi
                    </h4>
                    <div class="bg-gradient-to-b from-amber-50 to-white border border-amber-200 rounded-xl p-4 mb-2">
                        <i class="fa-solid fa-award text-4xl text-amber-500 mb-2"></i>
                        <h5 class="text-sm font-extrabold text-[#0B4460] font-serif">SINTA PREPARATION</h5>
                        <p class="text-[11px] text-slate-600 mt-1">
                            Disiapkan menuju Akreditasi Nasional Jurnal Ilmiah Elektronik (ARJUNA - SINTA Kemenristek/BRIN).
                        </p>
                    </div>
                    <span class="text-[10px] text-slate-400 font-mono">Standar Akreditasi Kemenristekdikti</span>
                </div>

                <!-- 4. SIDEMENU PKP OJS (POLICIES & GUIDELINES) -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <i class="fa-solid fa-bars text-[#0B4460]"></i> Kebijakan Jurnal (Sidemenu)
                    </h4>
                    <ul class="text-xs text-slate-700 divide-y divide-slate-100">
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Focus and Scope</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Peer Review Process</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Online Submission</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Publication Ethics</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Screening for Plagiarism</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Author Guidelines</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Author Fees (Free APC)</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Open Access Statement</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Copyright & Licensing</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                        <li class="py-2 hover:text-[#0B4460] transition-colors flex items-center justify-between cursor-pointer">
                            <span><i class="fa-solid fa-angle-right text-slate-400 mr-2 text-[10px]"></i> Generative AI Policies</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-300"></i>
                        </li>
                    </ul>
                </div>

                <!-- 5. TOOLS SUPPORTED (PLAGIARISM & REFERENCE MANAGERS) -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Alat Sitasi & Uji Plagiarisme
                    </h4>
                    <div class="grid grid-cols-2 gap-2 text-center text-xs">
                        <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl font-bold text-red-700 flex flex-col items-center">
                            <i class="fa-solid fa-shield-halved text-lg mb-1 text-red-600"></i> Turnitin / OpenPlag
                        </div>
                        <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl font-bold text-[#b5121b] flex flex-col items-center">
                            <i class="fa-solid fa-bookmark text-lg mb-1 text-[#b5121b]"></i> Mendeley
                        </div>
                        <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl font-bold text-blue-600 flex flex-col items-center">
                            <i class="fa-solid fa-book-bookmark text-lg mb-1 text-blue-500"></i> Zotero
                        </div>
                        <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl font-bold text-emerald-600 flex flex-col items-center">
                            <i class="fa-solid fa-spell-check text-lg mb-1 text-emerald-500"></i> Grammarly
                        </div>
                    </div>
                </div>

                <!-- 6. INDEXING & REPOSITORIES -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Indeksasi & Repositori
                    </h4>
                    <div class="grid grid-cols-2 gap-2 text-center text-xs font-semibold text-slate-700">
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">Google Scholar</div>
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">Crossref (DOI)</div>
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">GARUDA Kemdikbud</div>
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">Dimensions</div>
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">BASE Bielefeld</div>
                        <div class="bg-slate-50 border border-slate-200 p-2 rounded-lg">Scilit</div>
                    </div>
                </div>

                <!-- 7. VISITOR STATISTICS & JOURNAL METRICS -->
                <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                        Statistik & Metrik Jurnal
                    </h4>
                    <div class="space-y-2 text-xs">
                        <div class="flex justify-between items-center py-1 border-b border-slate-100">
                            <span class="text-slate-500">Tingkat Penerimaan (Acceptance):</span>
                            <b class="text-[#0B4460]">28%</b>
                        </div>
                        <div class="flex justify-between items-center py-1 border-b border-slate-100">
                            <span class="text-slate-500">Kecepatan Review Pertama:</span>
                            <b class="text-emerald-700">14 Hari Kerja</b>
                        </div>
                        <div class="flex justify-between items-center py-1 border-b border-slate-100">
                            <span class="text-slate-500">Frekuensi Terbitan:</span>
                            <b class="text-slate-800">2x / Tahun</b>
                        </div>
                        <div class="flex justify-between items-center py-1 border-b border-slate-100">
                            <span class="text-slate-500">Biaya Penulis (APC):</span>
                            <b class="text-emerald-700">Rp 0 (Gratis)</b>
                        </div>
                        <div class="flex justify-between items-center py-1">
                            <span class="text-slate-500">Total Kunjungan Pembaca:</span>
                            <b class="text-amber-600 font-mono">1,482 Hits</b>
                        </div>
                    </div>
                </div>
            </div>
            """)

    # 5. FOOTER RESMI JURNAL (Standard OJS 3.5 Academic Footer)
    gr.HTML("""
    <div class="bg-[#08344a] text-slate-300 rounded-2xl p-8 mt-8 border-t-4 border-amber-400 shadow-xl">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-xs leading-relaxed">
            <!-- Col 1 -->
            <div>
                <h4 class="text-sm font-bold text-white font-serif mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-graduation-cap text-amber-400"></i> Tentang J-DIGITEK
                </h4>
                <p class="text-slate-300 leading-relaxed mb-3">
                    <b>J-DIGITEK (Journal of Digital Innovation and Applied Engineering Technology)</b> adalah jurnal ilmiah peer-reviewed open access yang diterbitkan oleh Program Studi Teknologi Informasi, Universitas Sari Mulia bersama Noura Studio.
                </p>
                <span class="text-[11px] text-amber-400 font-mono block">E-ISSN: 2988-8212 &bull; P-ISSN: 2988-8204</span>
            </div>

            <!-- Col 2 -->
            <div>
                <h4 class="text-sm font-bold text-white font-serif mb-3">Tautan Cepat</h4>
                <ul class="space-y-1.5 text-slate-300">
                    <li><a href="#" class="hover:text-amber-400 transition-colors">&bull; Fokus dan Ruang Lingkup</a></li>
                    <li><a href="#" class="hover:text-amber-400 transition-colors">&bull; Pedoman Penulisan (Author Guidelines)</a></li>
                    <li><a href="#" class="hover:text-amber-400 transition-colors">&bull; Etika Publikasi & Malpraktik</a></li>
                    <li><a href="#" class="hover:text-amber-400 transition-colors">&bull; Kebijakan Pemeriksaan Plagiarisme</a></li>
                    <li><a href="#" class="hover:text-amber-400 transition-colors">&bull; Dewan Redaksi & Reviewer</a></li>
                </ul>
            </div>

            <!-- Col 3 -->
            <div>
                <h4 class="text-sm font-bold text-white font-serif mb-3">Sekretariat Redaksi</h4>
                <p class="text-slate-300 leading-relaxed">
                    <b>Fakultas Sains dan Teknologi</b><br>
                    Program Studi Teknologi Informasi<br>
                    Universitas Sari Mulia<br>
                    Jl. Pramuka No. 2, Pemurus Luar, Kec. Banjarmasin Timur, Kota Banjarmasin, Kalimantan Selatan 70249<br>
                    Email: <span class="text-amber-400">editor@j-digitek.id</span>
                </p>
            </div>

            <!-- Col 4 -->
            <div>
                <h4 class="text-sm font-bold text-white font-serif mb-3">Lisensi & Indeksasi</h4>
                <div class="bg-white/10 p-3 rounded-xl border border-white/15 mb-3">
                    <span class="block font-bold text-white mb-1"><i class="fa-brands fa-creative-commons mr-1"></i> CC BY 4.0</span>
                    <p class="text-[11px] text-slate-300">
                        Seluruh artikel yang dipublikasikan didistribusikan di bawah lisensi Creative Commons Attribution 4.0 International License.
                    </p>
                </div>
                <span class="text-[11px] text-slate-400">Powered by Public Knowledge Project (PKP) OJS 3.5</span>
            </div>
        </div>

        <div class="border-t border-white/10 pt-4 flex flex-wrap justify-between items-center text-xs text-slate-400 gap-2">
            <div>
                &copy; 2026 J-DIGITEK (Journal of Digital Innovation and Applied Engineering Technology). Seluruh Hak Cipta Dilindungi.
            </div>
            <div>
                Pimpinan Redaksi: <b>Ir. Nor Anisa, S.Kom., M.Kom.</b> &bull; Banjarmasin, Indonesia
            </div>
        </div>
    </div>
    """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False, css=ojs_custom_css)
