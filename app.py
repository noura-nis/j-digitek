# -*- coding: utf-8 -*-
"""
J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan
Journal of Digital Innovation and Applied Engineering Technology
Pimpinan Redaksi (Editor-in-Chief): Ir. Nor Anisa, S.Kom., M.Kom.
Desain Terinspirasi OJS 3.5 Gaudeamus Style (Deep Navy & Golden Amber)
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

# Konfigurasi Supabase
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
        return "⚠️ Mohon lengkapi seluruh formulir bertanda wajib (Judul, Penulis, Track, dan Abstrak naskah)."

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
        "reviewer_notes": "Naskah berhasil masuk ke sistem OJS J-DIGITEK dan siap ditelaah oleh Dewan Redaksi."
    }

    res = query_supabase("j_digitek_articles", method="POST", data=payload)
    if res and len(res) > 0:
        art_id = res[0].get("id")
        return f"""✅ BUKTI TANDA TERIMA PENGIRIMAN NASKAH (SUBMISSION RECEIPT)
===================================================================
No. Registrasi OJS : J-DIGITEK-2026-{art_id:04d}
Judul Naskah       : {title}
Penulis Utama      : {authors}
Bidang Fokus       : {track}
Afiliasi Institusi : {affiliation or 'Universitas Sari Mulia'}
Status Naskah      : Submitted (Dalam Antrean Dewan Redaksi)
Tanggal Pengajuan  : {datetime.now().strftime('%d %B %Y, %H:%M')} WITA

Naskah Anda telah terdaftar permanen di basis data Cloud J-DIGITEK.
Pimpinan Redaksi (Ir. Nor Anisa, S.Kom., M.Kom.) akan meninjau kelayakan naskah melalui proses Peer-Review."""
    else:
        return "❌ Terjadi kendala saat menyimpan naskah ke database. Silakan coba kembali."

def verify_editor_and_load(pin):
    if pin != EDITOR_PIN:
        return "❌ PIN Akses Salah! Hanya Dewan Redaksi yang memiliki otorisasi.", []
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
    return f"🟢 Akses Diterima! Selamat Datang, Bu Nor Anisa. Terdapat {len(articles)} naskah dalam antrean editorial.", table_data

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
        <div style="background:#ffffff;border:2px dashed #cbd5e1;border-radius:12px;padding:45px 20px;text-align:center;margin-top:16px;">
            <div style="font-size:2.8rem;margin-bottom:12px;">📭</div>
            <h3 style="color:#14246b;font-size:1.25rem;font-weight:800;margin:0 0 8px 0;">Belum Ada Naskah yang Diterbitkan</h3>
            <p style="color:#475569;font-size:0.92rem;margin:0 auto;max-width:620px;line-height:1.7;">
                Jurnal <b>J-DIGITEK</b> saat ini sedang dalam masa <b>Call for Papers (Penerimaan Naskah)</b> untuk <b>Volume 1 Nomor 1 (Edisi Perdana 2026)</b>. 
                Naskah yang diajukan oleh mahasiswa atau peneliti akan melalui tahapan telaah sejawat (peer-review) oleh Dewan Redaksi sebelum resmi tayang di sini.
            </p>
            <div style="margin-top:20px;">
                <span style="background:#ffb23e;color:#14246b;padding:6px 18px;border-radius:20px;font-size:0.82rem;font-weight:800;letter-spacing:0.5px;">STATUS: OPEN FOR SUBMISSIONS (VOL. 1 NO. 1, 2026)</span>
            </div>
        </div>
        """

    html = "<div style='display:flex;flex-direction:column;gap:18px;margin-top:15px;'>"
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
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid #14246b;border-radius:8px;padding:22px;box-shadow:0 2px 6px rgba(0,0,0,0.03);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="background:#f1f5f9;color:#14246b;border:1px solid #cbd5e1;padding:4px 12px;border-radius:14px;font-size:0.78rem;font-weight:700;">{track}</span>
                <span style="color:#64748b;font-size:0.82rem;font-weight:600;">Vol. {vol} No. {issue} ({year})</span>
            </div>
            <h3 style="color:#14246b;font-size:1.15rem;font-weight:800;margin:0 0 10px 0;line-height:1.45;">{title}</h3>
            <p style="color:#334155;font-size:0.88rem;margin:0 0 12px 0;"><b>Penulis:</b> {authors} &bull; <span style="color:#64748b;">{affiliation}</span></p>
            <div style="background:#f8fafc;padding:14px;border-radius:6px;margin-bottom:12px;border:1px solid #f1f5f9;">
                <b style="color:#14246b;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px;">Abstrak:</b>
                <p style="color:#334155;font-size:0.88rem;line-height:1.65;margin:4px 0 0 0;">{abstract}</p>
            </div>
            <div style="background:#f4f6fa;padding:10px 14px;border-radius:6px;font-size:0.82rem;color:#334155;">
                <b style="color:#14246b;">Sitasi APA 7th:</b> <code style="color:#14246b;background:#e2e8f0;padding:2px 6px;border-radius:4px;">{apa}</code>
            </div>
        </div>
        """
    html += "</div>"
    return html


# Tema Khas OJS Gaudeamus (Deep Navy #14246b + Golden Amber #ffb23e + Light Background #f4f6fa)
ojs_css = """
/* Mode Terang Bersih OJS 3.5 */
:root, html, body {
    color-scheme: light !important;
    background-color: #f4f6fa !important;
    color: #1e293b !important;
    font-family: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
}

.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background-color: #f4f6fa !important;
}

/* OJS Top Bar */
.ojs-topbar {
    background: #0d1740;
    color: #94a3b8;
    padding: 8px 30px;
    font-size: 0.8rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* OJS Main Header */
.ojs-header {
    background: #14246b;
    padding: 24px 30px;
    color: #ffffff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 4px solid #ffb23e;
}

.ojs-title {
    font-size: 2.1rem;
    font-weight: 900;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.5px;
}

.ojs-subtitle {
    font-size: 1.05rem;
    font-weight: 600;
    color: #ffb23e;
    margin: 4px 0 0 0;
}

/* Tombol Make a Submission Khas OJS */
.btn-ojs-submission {
    display: block;
    background: #ffb23e !important;
    color: #14246b !important;
    font-weight: 800 !important;
    font-size: 0.95rem !important;
    text-align: center;
    padding: 14px 20px !important;
    border-radius: 8px !important;
    text-decoration: none !important;
    box-shadow: 0 4px 10px rgba(255, 178, 62, 0.35) !important;
    border: none !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.btn-ojs-submission:hover {
    background: #e0992a !important;
    transform: translateY(-1px);
}

/* Sidebar Box Khas Gaudeamus Theme */
.ojs-sidebar-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 16px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.ojs-sidebar-header {
    background: #14246b;
    color: #ffffff;
    padding: 10px 16px;
    font-size: 0.88rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-left: 4px solid #ffb23e;
}

.ojs-sidebar-body {
    padding: 14px 16px;
    font-size: 0.86rem;
    color: #334155;
    line-height: 1.6;
}

/* Tab Navigasi OJS */
.tab-nav {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 6px !important;
    margin-bottom: 20px !important;
    gap: 6px !important;
}

.tab-nav button {
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    color: #475569 !important;
    padding: 10px 18px !important;
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}

.tab-nav button:hover {
    background: #f1f5f9 !important;
    color: #14246b !important;
}

.tab-nav button.selected {
    background: #14246b !important;
    color: #ffffff !important;
}

/* Form Styling */
input, textarea, select {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    font-size: 0.92rem !important;
}

input:focus, textarea:focus {
    border-color: #14246b !important;
    box-shadow: 0 0 0 3px rgba(20, 36, 107, 0.15) !important;
}

label, .label-wrap span {
    color: #14246b !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
}

button.primary {
    background: #14246b !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 10px 22px !important;
}

button.primary:hover {
    background: #0d1740 !important;
}

/* Footer Khas OJS Gaudeamus */
.ojs-footer {
    background: #0d1740;
    color: #e2e8f0;
    padding: 36px 30px 20px 30px;
    margin-top: 30px;
    border-top: 4px solid #ffb23e;
}

/* Sembunyikan Footer Bawaan Gradio (Use via API, Built with Gradio, Settings) */
footer, .gradio-container footer, div[data-testid="footer"], .svelte-10p0y76, .svelte-1ed2p3z {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
"""

with gr.Blocks(title="J-DIGITEK: International Journal of Digital Innovation and Applied Engineering Technology") as app:
    # Injeksi CSS OJS
    gr.HTML(f"<style>{ojs_css}</style>")
    
    # 1. TOP BAR OJS
    gr.HTML("""
    <div class="ojs-topbar">
        <div>
            <span>OPEN JOURNAL SYSTEMS 3.5 &bull; OPEN ACCESS ACADEMIC PORTAL</span>
        </div>
        <div style="display:flex;gap:15px;">
            <span>E-ISSN: 2988-xxxx</span>
            <span>P-ISSN: 2988-yyyy</span>
            <span style="color:#ffb23e;font-weight:700;">VOL. 1 NO. 1 (2026)</span>
        </div>
    </div>
    """)

    # 2. MAIN HEADER OJS GAUDEAMUS STYLE
    gr.HTML("""
    <div class="ojs-header">
        <div>
            <h1 class="ojs-title">J-DIGITEK</h1>
            <p class="ojs-subtitle">Journal of Digital Innovation and Applied Engineering Technology</p>
            <p style="color:#cbd5e1;font-size:0.88rem;margin:6px 0 0 0;">
                Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan &bull; Editor-in-Chief: <b>Ir. Nor Anisa, S.Kom., M.Kom.</b>
            </p>
        </div>
        <div style="text-align:right;">
            <div style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);padding:10px 18px;border-radius:8px;">
                <span style="color:#ffb23e;font-weight:800;font-size:0.85rem;display:block;">PEER-REVIEWED JOURNAL</span>
                <span style="color:#ffffff;font-size:0.78rem;">Indexed in Google Scholar & GARUDA</span>
            </div>
        </div>
    </div>
    """)

    # 3. CONTAINER DUA KOLOM OJS (MAIN 75% + SIDEBAR 25%)
    with gr.Row(elem_classes=["ojs-body-container"]):
        # KOLOM KIRI (KONTEN UTAMA - 75%)
        with gr.Column(scale=3):
            with gr.Tabs():
                # TAB 1: BERANDA & INFORMASI JURNAL
                with gr.Tab("🏠 Home (Beranda)"):
                    gr.HTML("""
                    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:24px;margin-bottom:20px;">
                        <h2 style="color:#14246b;font-size:1.35rem;font-weight:800;margin-top:0;border-bottom:2px solid #e2e8f0;padding-bottom:10px;">
                            About the Journal
                        </h2>
                        <p style="color:#334155;line-height:1.75;font-size:0.95rem;">
                            <b>J-DIGITEK (Journal of Digital Innovation and Applied Engineering Technology)</b> is a peer-reviewed open-access journal dedicated to publishing original research and cutting-edge practical advancements in the fields of software engineering, cloud computing, artificial intelligence, and digital business transformation.
                        </p>
                        <p style="color:#334155;line-height:1.75;font-size:0.95rem;">
                            Diterbitkan secara berkala 2 (dua) kali setahun (Juni dan Desember) sebagai media diseminasi hasil karya tugas akhir mahasiswa, penelitian dosen, dan inovasi terapan dari praktisi industri teknologi informasi di bawah bimbingan dan kepemimpinan <b>Ir. Nor Anisa, S.Kom., M.Kom.</b>
                        </p>

                        <!-- PENGUMUMAN CALL FOR PAPERS -->
                        <div style="background:#fffbeb;border:1.5px solid #fde68a;border-left:5px solid #ffb23e;border-radius:8px;padding:18px;margin:24px 0;">
                            <span style="background:#ffb23e;color:#14246b;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:800;">CALL FOR PAPERS</span>
                            <h3 style="color:#92400e;font-size:1.15rem;font-weight:800;margin:8px 0 6px 0;">Volume 1, Issue 1 (Inaugural Edition 2026)</h3>
                            <p style="color:#78350f;font-size:0.88rem;line-height:1.6;margin:0;">
                                We cordially invite authors to submit original, unpublished manuscripts for the upcoming inaugural issue. All submissions will undergo a double-blind peer review process. Free Article Processing Charge (APC: Rp 0) for verified students and academic researchers.
                            </p>
                        </div>

                        <h3 style="color:#14246b;font-size:1.15rem;font-weight:800;border-bottom:2px solid #e2e8f0;padding-bottom:8px;margin-bottom:16px;">
                            Focus and Scope (Bidang Keilmuan)
                        </h3>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:3px solid #14246b;border-radius:6px;padding:14px;">
                                <b style="color:#14246b;font-size:0.92rem;display:block;margin-bottom:4px;">1. Software Engineering & UI/UX</b>
                                <p style="color:#475569;font-size:0.84rem;line-height:1.6;margin:0;">Software Testing, Quality Assurance, UI/UX Design, Human-Computer Interaction, Game Development.</p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:3px solid #0d9488;border-radius:6px;padding:14px;">
                                <b style="color:#0d9488;font-size:0.92rem;display:block;margin-bottom:4px;">2. Cloud Computing, Network & IoT</b>
                                <p style="color:#475569;font-size:0.84rem;line-height:1.6;margin:0;">Internet of Things (IoT), Computer Networks, Cloud Infrastructure, Virtual Machine Services.</p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:3px solid #4f46e5;border-radius:6px;padding:14px;">
                                <b style="color:#4f46e5;font-size:0.92rem;display:block;margin-bottom:4px;">3. Data Science, Smart Systems & NLP</b>
                                <p style="color:#475569;font-size:0.84rem;line-height:1.6;margin:0;">Big Data Analytics, Decision Support Systems (SPK), Natural Language Processing, Sentiment Analysis.</p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:3px solid #d97706;border-radius:6px;padding:14px;">
                                <b style="color:#d97706;font-size:0.92rem;display:block;margin-bottom:4px;">4. Digital Transformation & Business</b>
                                <p style="color:#475569;font-size:0.84rem;line-height:1.6;margin:0;">Digital Business, Digital Innovation, Technopreneurship, E-Commerce, Digital Community Empowerment.</p>
                            </div>
                        </div>
                    </div>
                    """)

                # TAB 2: CURRENT ISSUE (TERBITAN TERKINI)
                with gr.Tab("📖 Current Issue (Terbitan Terkini)"):
                    gr.HTML("""
                    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:24px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:16px;">
                            <div>
                                <h2 style="color:#14246b;font-size:1.3rem;font-weight:800;margin:0;">Vol. 1 No. 1 (2026): J-DIGITEK Edisi Perdana</h2>
                                <span style="color:#64748b;font-size:0.85rem;">Published: Scheduled for June 2026 &bull; Status: In Progress (Call for Papers)</span>
                            </div>
                        </div>
                    </div>
                    """)
                    published_container = gr.HTML(value=render_published_html("Semua Track"))

                # TAB 3: SUBMISSIONS (PENGAJUAN NASKAH)
                with gr.Tab("📝 Submissions (Pengajuan Naskah)"):
                    gr.Markdown("### Online Manuscript Submission\nSilakan isi formulir pengajuan naskah ilmiah di bawah ini. Naskah yang dikirimkan akan langsung tersimpan di Cloud Database Supabase dan diproses oleh Dewan Redaksi.")
                    
                    sub_title = gr.Textbox(label="Judul Naskah Ilmiah (Article Title) *", placeholder="Contoh: Analisis Sentimen Opini Publik Menggunakan Naive Bayes Classifier...")
                    sub_authors = gr.Textbox(label="Nama Penulis & Dosen Pembimbing (Authors) *", placeholder="Contoh: Arpan Mualief Saprizal (Mahasiswa), Ir. Nor Anisa, S.Kom., M.Kom. (Dosen Pembimbing)")
                    
                    with gr.Row():
                        sub_affil = gr.Textbox(label="Afiliasi Institusi (Affiliation)", value="Program Studi Informatika, Universitas Sari Mulia")
                        sub_email = gr.Textbox(label="Email Korespondensi", placeholder="penulis@unism.ac.id")
                    
                    sub_track = gr.Dropdown(
                        label="Pilih Bidang Fokus (Section / Track) *",
                        choices=[
                            "Track 1: Software Engineering, UI/UX & Game",
                            "Track 2: Cloud Computing, Network & IoT",
                            "Track 3: Data Science, Smart Systems & NLP",
                            "Track 4: Digital Transformation & Business"
                        ],
                        value="Track 3: Data Science, Smart Systems & NLP"
                    )
                    
                    sub_abstract = gr.TextArea(label="Abstrak Naskah (Abstract) *", placeholder="Ringkasan naskah meliputi latar belakang, metodologi, hasil pengujian, dan simpulan...", lines=5)
                    sub_keywords = gr.Textbox(label="Kata Kunci (Keywords)", placeholder="Contoh: Machine Learning, NLP, Cloud, IoT, UI/UX")
                    sub_file = gr.File(label="Upload Berkas Naskah Lengkap (PDF)", file_types=[".pdf", ".docx"])
                    
                    sub_btn = gr.Button("🚀 Kirim Naskah ke Dewan Redaksi (Submit)", variant="primary", size="lg")
                    sub_output = gr.TextArea(label="Tanda Terima Pengajuan Naskah (Submission Receipt)", interactive=False, lines=6)

                    sub_btn.click(
                        fn=submit_manuscript,
                        inputs=[sub_title, sub_authors, sub_affil, sub_email, sub_track, sub_abstract, sub_keywords, sub_file],
                        outputs=[sub_output]
                    )

                # TAB 4: EDITORIAL WORKSPACE (KHUSUS BU NOR ANISA)
                with gr.Tab("👩‍🏫 Editorial Team Portal (Dasbor Bu Nor Anisa)"):
                    gr.Markdown("### Dasbor Pengelolaan Editorial & Review Naskah\nKhusus untuk Editor-in-Chief (Ir. Nor Anisa, S.Kom., M.Kom.) untuk meninjau naskah masuk dan mengambil keputusan publikasi.")
                    
                    with gr.Row():
                        editor_pin = gr.Textbox(label="PIN Dewan Redaksi", type="password", placeholder="Masukkan PIN Rahasia...", scale=3)
                        editor_login_btn = gr.Button("🔓 Buka Antrean Redaksi", variant="primary", scale=1)

                    editor_status = gr.Markdown("Status: *Menunggu verifikasi PIN Dewan Redaksi*")
                    editor_table = gr.Dataframe(
                        headers=["ID", "Judul Naskah", "Penulis", "Bidang Fokus (Track)", "Status Editorial", "Tanggal Masuk"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        label="Daftar Seluruh Naskah Masuk (Real-Time Cloud Supabase)",
                        interactive=False
                    )

                    editor_login_btn.click(
                        fn=verify_editor_and_load,
                        inputs=[editor_pin],
                        outputs=[editor_status, editor_table]
                    )

                    gr.Markdown("---")
                    gr.Markdown("#### Formulir Keputusan Editorial & Reviewer")
                    with gr.Row():
                        with gr.Column(scale=1):
                            eval_id = gr.Number(label="Nomor ID Naskah", precision=0, placeholder="Contoh: 1")
                            eval_load_btn = gr.Button("🔍 Buka Naskah", variant="secondary")
                            eval_details = gr.TextArea(label="Rincian Naskah", interactive=False, lines=6)
                        with gr.Column(scale=2):
                            eval_abstract = gr.TextArea(label="Teks Abstrak Naskah", interactive=False, lines=4)
                            eval_status = gr.Radio(
                                label="Keputusan Dewan Redaksi",
                                choices=["Submitted", "Under Review", "Revision Required", "Accepted", "Published"],
                                value="Accepted"
                            )
                            eval_notes = gr.TextArea(label="Catatan Reviewer / Catatan Revisi untuk Penulis", lines=3, placeholder="Catatan evaluasi untuk disampaikan kepada penulis...")
                            eval_save_btn = gr.Button("💾 Simpan Keputusan Editorial", variant="primary", size="lg")
                            eval_result = gr.Markdown("")

                    eval_load_btn.click(
                        fn=load_single_article,
                        inputs=[editor_pin, eval_id],
                        outputs=[eval_details, eval_abstract, eval_status, eval_notes, gr.Textbox(visible=False)]
                    )

                    eval_save_btn.click(
                        fn=update_article_decision,
                        inputs=[editor_pin, eval_id, eval_status, eval_notes],
                        outputs=[eval_result, editor_table]
                    )

        # KOLOM KANAN (SIDEBAR KHAS OJS 3.5 GAUDEAMUS STYLE - 25%)
        with gr.Column(scale=1):
            # 1. TOMBOL SUBMISSION BESAR GAUDEAMUS
            gr.HTML("""
            <div style="margin-bottom:16px;">
                <a href="#tab-2" class="btn-ojs-submission">
                    📝 Make a Submission &rarr;
                </a>
            </div>
            """)

            # 2. TEMPLATE NASKAH (MANUSCRIPT TEMPLATE)
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Article Template</div>
                <div class="ojs-sidebar-body" style="text-align:center;">
                    <p style="margin:0 0 10px 0;font-size:0.84rem;color:#475569;">
                        Gunakan template resmi Microsoft Word berikut dalam menyusun naskah Anda:
                    </p>
                    <a href="https://github.com/noura-nis/j-digitek" target="_blank" style="display:inline-block;background:#14246b;color:#ffffff;text-decoration:none;padding:8px 16px;border-radius:6px;font-size:0.84rem;font-weight:700;">
                        📥 Download Template (.docx)
                    </a>
                </div>
            </div>
            """)

            # 3. ADDITIONAL MENU KHAS OJS
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Additional Menu</div>
                <div class="ojs-sidebar-body" style="padding:8px 0;">
                    <ul style="list-style:none;padding:0;margin:0;font-size:0.86rem;">
                        <li style="padding:6px 16px;border-bottom:1px solid #f1f5f9;"><a href="#tab-0" style="color:#14246b;text-decoration:none;font-weight:600;">&bull; Focus and Scope</a></li>
                        <li style="padding:6px 16px;border-bottom:1px solid #f1f5f9;"><a href="#tab-2" style="color:#14246b;text-decoration:none;font-weight:600;">&bull; Author Guidelines</a></li>
                        <li style="padding:6px 16px;border-bottom:1px solid #f1f5f9;"><span style="color:#14246b;font-weight:600;">&bull; Peer Review Process</span></li>
                        <li style="padding:6px 16px;border-bottom:1px solid #f1f5f9;"><span style="color:#14246b;font-weight:600;">&bull; Publication Ethics</span></li>
                        <li style="padding:6px 16px;"><span style="color:#10b981;font-weight:700;">&bull; Author Fees: Rp 0 (Free)</span></li>
                    </ul>
                </div>
            </div>
            """)

            # 4. DEWAN REDAKSI (EDITORIAL TEAM)
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Editorial Board</div>
                <div class="ojs-sidebar-body">
                    <span style="color:#64748b;font-size:0.75rem;font-weight:700;display:block;">EDITOR-IN-CHIEF:</span>
                    <b style="color:#14246b;font-size:0.92rem;display:block;">Ir. Nor Anisa, S.Kom., M.Kom.</b>
                    <span style="color:#475569;font-size:0.8rem;display:block;">Dosen, Peneliti NLP & Insinyur Profesional PII</span>
                    <hr style="border:0;border-top:1px solid #e2e8f0;margin:10px 0;">
                    <span style="color:#64748b;font-size:0.75rem;font-weight:700;display:block;">MANAGING EDITORS:</span>
                    <span style="color:#334155;font-weight:600;font-size:0.84rem;">AI Engineering & Research Lab Team</span>
                </div>
            </div>
            """)

            # 5. AKREDITASI & PENGINDEKSAN (INDEXING)
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Indexing & Accreditation</div>
                <div class="ojs-sidebar-body" style="text-align:center;">
                    <div style="display:flex;flex-direction:column;gap:8px;font-size:0.84rem;font-weight:700;">
                        <div style="background:#f1f5f9;border:1px solid #cbd5e1;padding:6px;border-radius:4px;color:#14246b;">Google Scholar</div>
                        <div style="background:#f1f5f9;border:1px solid #cbd5e1;padding:6px;border-radius:4px;color:#14246b;">GARUDA Kemdikbudristek</div>
                        <div style="background:#f1f5f9;border:1px solid #cbd5e1;padding:6px;border-radius:4px;color:#14246b;">Crossref (DOI System)</div>
                        <div style="background:#f1f5f9;border:1px solid #cbd5e1;padding:6px;border-radius:4px;color:#14246b;">Akreditasi SINTA</div>
                    </div>
                </div>
            </div>
            """)

            # 6. TOOLS PENELITIAN (MENDELEY & TURNITIN)
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Plagiarism & Reference Tools</div>
                <div class="ojs-sidebar-body" style="text-align:center;">
                    <div style="display:flex;justify-content:center;gap:12px;align-items:center;padding:6px 0;">
                        <span style="background:#f1f5f9;padding:6px 12px;border-radius:6px;font-size:0.8rem;font-weight:700;color:#990000;border:1px solid #fecaca;">Mendeley</span>
                        <span style="background:#f1f5f9;padding:6px 12px;border-radius:6px;font-size:0.8rem;font-weight:700;color:#0284c7;border:1px solid #bae6fd;">Turnitin / OpenPlag</span>
                    </div>
                </div>
            </div>
            """)

            # 7. STATISTIK PENGUNJUNG
            gr.HTML("""
            <div class="ojs-sidebar-card">
                <div class="ojs-sidebar-header">Visitor Statistics</div>
                <div class="ojs-sidebar-body" style="text-align:center;">
                    <div style="background:#f8fafc;padding:10px;border-radius:6px;border:1px solid #e2e8f0;">
                        <span style="font-size:1.3rem;font-weight:900;color:#14246b;display:block;">1,420+</span>
                        <span style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:700;">Total Pageviews</span>
                    </div>
                </div>
            </div>
            """)

    # 4. FOOTER KHAS OJS GAUDEAMUS STYLE
    gr.HTML("""
    <div class="ojs-footer">
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:30px;margin-bottom:24px;">
            <div>
                <h4 style="color:#ffb23e;font-size:1.05rem;font-weight:800;margin:0 0 10px 0;">J-DIGITEK</h4>
                <p style="font-size:0.85rem;color:#cbd5e1;line-height:1.6;margin:0 0 10px 0;">
                    Journal of Digital Innovation and Applied Engineering Technology &bull; Jurnal ilmiah berkala akses terbuka untuk diseminasi riset informatika dan transformasi digital.
                </p>
                <span style="color:#94a3b8;font-size:0.8rem;">E-ISSN: 2988-xxxx &bull; P-ISSN: 2988-yyyy</span>
            </div>
            <div>
                <h4 style="color:#ffb23e;font-size:1.05rem;font-weight:800;margin:0 0 10px 0;">Official Journal Information</h4>
                <div style="font-size:0.85rem;color:#cbd5e1;line-height:1.7;">
                    <b>Pimpinan Redaksi:</b> Ir. Nor Anisa, S.Kom., M.Kom.<br>
                    <b>Laboratorium Riset:</b> AI Engineering & Research Lab<br>
                    <b>Kontak Redaksi:</b> editor.jdigitek@noranisa.id<br>
                    <b>Asisten Editorial WhatsApp:</b> 0851-5513-3070 (CS Nadia 24/7)
                </div>
            </div>
            <div>
                <h4 style="color:#ffb23e;font-size:1.05rem;font-weight:800;margin:0 0 10px 0;">License & Open Access</h4>
                <p style="font-size:0.82rem;color:#cbd5e1;line-height:1.6;margin:0 0 8px 0;">
                    This work is licensed under a <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" style="color:#ffb23e;text-decoration:none;">Creative Commons Attribution 4.0 International License (CC BY 4.0)</a>.
                </p>
                <div style="background:rgba(255,255,255,0.08);padding:8px 12px;border-radius:6px;font-size:0.78rem;color:#94a3b8;">
                    Hak cipta artikel tetap berada pada penulis (Author Retention).
                </div>
            </div>
        </div>
        <hr style="border:0;border-top:1px solid rgba(255,255,255,0.15);margin:20px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;font-size:0.8rem;color:#94a3b8;">
            <div>&copy; 2026 J-DIGITEK. Seluruh Hak Cipta Dilindungi.</div>
            <div>Powered by Open Journal Systems / Cloud Supabase Architecture</div>
        </div>
    </div>
    """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False, css=ojs_css)
