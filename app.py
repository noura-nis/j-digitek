# -*- coding: utf-8 -*-
"""
J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan
Journal of Digital Innovation and Applied Engineering Technology
Pimpinan Redaksi (Editor-in-Chief): Ir. Nor Anisa, S.Kom., M.Kom.
Standar Tata Kelola Jurnal Ilmiah OJS & Supabase PostgreSQL
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

# Konfigurasi Supabase Cloud
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
        return "⚠️ Mohon lengkapi seluruh formulir wajib (Judul, Penulis, Track, dan Abstrak naskah)."

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
        "reviewer_notes": "Naskah telah masuk ke antrean editorial J-DIGITEK dan siap ditelaah oleh Dewan Redaksi."
    }

    res = query_supabase("j_digitek_articles", method="POST", data=payload)
    if res and len(res) > 0:
        art_id = res[0].get("id")
        return f"""✅ BUKTI TANDA TERIMA PENGAJUAN NASKAH (SUBMISSION RECEIPT)
===================================================================
Nomor Registrasi : J-DIGITEK-2026-{art_id:04d}
Judul Naskah     : {title}
Penulis Utama    : {authors}
Bidang Fokus     : {track}
Afiliasi         : {affiliation or 'Universitas Sari Mulia'}
Status Naskah    : Submitted (Menunggu Review Dewan Redaksi)
Tanggal Masuk    : {datetime.now().strftime('%d %B %Y, %H:%M')} WITA

Naskah Anda telah terdaftar permanen di basis data Cloud Supabase J-DIGITEK.
Pimpinan Redaksi (Ir. Nor Anisa, S.Kom., M.Kom.) akan meninjau kelayakan naskah melalui proses Peer-Review."""
    else:
        return "❌ Terjadi kendala saat menyimpan naskah ke database. Mohon ulangi kembali."

def verify_editor_and_load(pin):
    if pin != EDITOR_PIN:
        return "❌ PIN Akses Salah! Hanya Dewan Redaksi yang memiliki otorisasi.", []
    articles = get_all_articles()
    table_data = []
    for a in articles:
        table_data.append([
            str(a.get("id")),
            a.get("title", "")[:45] + "...",
            a.get("authors", "")[:30],
            a.get("track", "")[:28],
            a.get("status", "Submitted"),
            a.get("created_at", "2026-10-25")[:10]
        ])
    return f"🟢 Selamat Datang, Bu Nor Anisa! Ditemukan total {len(articles)} berkas naskah dalam antrean.", table_data

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
        return f"Naskah ID #{aid} tidak ditemukan dalam database.", "", "Submitted", "", ""
    art = res[0]
    detail = f"""📄 INFORMASI NASKAH #{art.get('id')}
--------------------------------------------------
Judul     : {art.get('title')}
Penulis   : {art.get('authors')}
Afiliasi  : {art.get('affiliation')}
Email     : {art.get('email')}
Track     : {art.get('track')}
File PDF  : {art.get('pdf_filename') or 'Tidak melampirkan berkas fisik'}
Kata Kunci: {art.get('keywords')}"""
    return detail, art.get("abstract", ""), art.get("status", "Submitted"), art.get("reviewer_notes", ""), art.get("keywords", "")

def update_article_decision(pin, article_id, new_status, notes):
    if pin != EDITOR_PIN:
        return "❌ Akses ditolak. PIN salah.", []
    if not article_id:
        return "❌ Tentukan ID naskah terlebih dahulu.", []
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
        <div style="background:#ffffff;border:2px dashed #cbd5e1;border-radius:12px;padding:50px 20px;text-align:center;margin-top:16px;">
            <div style="font-size:2.8rem;margin-bottom:12px;">📭</div>
            <h3 style="color:#0f172a;font-size:1.25rem;font-weight:800;margin:0 0 8px 0;">Belum Ada Naskah yang Diterbitkan</h3>
            <p style="color:#475569;font-size:0.92rem;margin:0 auto;max-width:600px;line-height:1.7;">
                Jurnal <b>J-DIGITEK</b> saat ini sedang dalam periode <b>Call for Papers (Penerimaan Naskah)</b> untuk <b>Edisi Perdana (Volume 1 Nomor 1, 2026)</b>. 
                Naskah yang diajukan oleh mahasiswa bimbingan atau peneliti luar akan melalui tahapan telaah sejawat (peer-review) oleh Editor-in-Chief sebelum resmi tayang di sini.
            </p>
            <div style="margin-top:20px;">
                <span style="background:#dbeafe;color:#1e40af;padding:6px 16px;border-radius:20px;font-size:0.82rem;font-weight:700;">Status: Open for Submissions (Vol. 1 No. 1, 2026)</span>
            </div>
        </div>
        """

    html = "<div style='display:flex;flex-direction:column;gap:20px;margin-top:15px;'>"
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
        <div style="background:#ffffff;border:1px solid #cbd5e1;border-left:6px solid #1e40af;border-radius:10px;padding:22px;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:4px 12px;border-radius:16px;font-size:0.78rem;font-weight:700;">{track}</span>
                <span style="color:#64748b;font-size:0.82rem;font-weight:600;">Vol. {vol} No. {issue} ({year})</span>
            </div>
            <h3 style="color:#0f172a;font-size:1.2rem;font-weight:800;margin:0 0 10px 0;line-height:1.45;">{title}</h3>
            <p style="color:#334155;font-size:0.9rem;margin:0 0 14px 0;"><b>Penulis:</b> {authors} &bull; <span style="color:#64748b;">{affiliation}</span></p>
            <div style="background:#f8fafc;padding:14px;border-radius:8px;margin-bottom:14px;border:1px solid #e2e8f0;">
                <b style="color:#0f172a;font-size:0.84rem;text-transform:uppercase;letter-spacing:0.5px;">Abstrak:</b>
                <p style="color:#334155;font-size:0.88rem;line-height:1.65;margin:6px 0 0 0;">{abstract}</p>
            </div>
            <div style="background:#f1f5f9;padding:12px 16px;border-radius:8px;font-size:0.82rem;color:#334155;">
                <b style="color:#0f172a;">Sitasi APA 7th:</b> <code style="color:#1e3a8a;background:#e2e8f0;padding:3px 8px;border-radius:4px;word-break:break-word;">{apa}</code>
            </div>
        </div>
        """
    html += "</div>"
    return html


# Tema Resmi Gradio Academic
academic_theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate"
).set(
    body_background_fill="#f8fafc",
    block_background_fill="#ffffff",
    block_border_color="#cbd5e1",
    input_background_fill="#ffffff",
    input_border_color="#94a3b8",
    body_text_color="#0f172a",
    block_title_text_color="#0f172a"
)

# Custom CSS Anti-Tabrakan Dark Mode & Standar Jurnal Ilmiah Internasional
clean_academic_css = """
/* Paksa Seluruh Halaman Tampil dalam Mode Terang Bersih & Kontras Tinggi */
:root, html, body {
    color-scheme: light !important;
    background-color: #f8fafc !important;
    color: #0f172a !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
}

.gradio-container {
    max-width: 1240px !important;
    margin: 0 auto !important;
    padding: 16px !important;
    background-color: #f8fafc !important;
}

/* Header Banner Jurnal Akademik */
.journal-header {
    background: linear-gradient(135deg, #0b192c 0%, #1e3e62 100%);
    border-radius: 12px;
    padding: 32px 36px;
    color: #ffffff;
    margin-bottom: 24px;
    box-shadow: 0 4px 14px rgba(11, 25, 44, 0.15);
    border: 1px solid #1e3e62;
}

/* Navigasi Tab Jurnal Ilmiah yang Kontras & Jelas */
.tab-nav {
    border-bottom: 2px solid #cbd5e1 !important;
    margin-bottom: 20px !important;
    gap: 8px !important;
}

.tab-nav button {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #334155 !important;
    padding: 12px 20px !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-bottom: none !important;
    border-radius: 8px 8px 0 0 !important;
    transition: all 0.2s ease !important;
}

.tab-nav button:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

.tab-nav button.selected {
    background: #1e3e62 !important;
    color: #ffffff !important;
    border-color: #1e3e62 !important;
}

/* Seluruh Input, Textbox, dan Textarea Wajib Berlatar Belakang Putih & Berteks Gelap Tajam */
input, textarea, select {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 6px !important;
    font-size: 0.92rem !important;
}

input:focus, textarea:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.15) !important;
}

/* Label Formulir */
label, .label-wrap span {
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    margin-bottom: 4px !important;
}

/* Tombol Utama dan Sekunder */
button.primary {
    background: #1e3e62 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 10px 22px !important;
}

button.primary:hover {
    background: #0b192c !important;
}

button.secondary {
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border: 1.5px solid #cbd5e1 !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
}

/* Kartu Sidebar & Konten */
.journal-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 24px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}

/* Tabel Editorial */
table {
    border: 1px solid #cbd5e1 !important;
}
th {
    background-color: #1e3e62 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    padding: 10px 14px !important;
}
td {
    color: #0f172a !important;
    background-color: #ffffff !important;
    border-bottom: 1px solid #e2e8f0 !important;
    padding: 10px 14px !important;
}
tr:nth-child(even) td {
    background-color: #f8fafc !important;
}
"""

with gr.Blocks(title="J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan", theme=academic_theme, css=clean_academic_css) as app:
    # BANNER RESMI JURNAL ILMIAH
    gr.HTML("""
    <div class="journal-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div>
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="background:#000000;color:#ffffff;border:1px solid #38bdf8;padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;">E-JOURNAL PORTAL</span>
                    <span style="background:rgba(255,255,255,0.15);padding:3px 12px;border-radius:20px;font-size:0.75rem;font-weight:600;">OPEN ACCESS PEER-REVIEWED</span>
                </div>
                <h1 style="color:#ffffff;font-size:2.2rem;font-weight:900;margin:0 0 6px 0;letter-spacing:-0.5px;">J-DIGITEK</h1>
                <h2 style="color:#93c5fd;font-size:1.15rem;font-weight:700;margin:0 0 12px 0;">Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan</h2>
                <p style="color:#e2e8f0;font-size:0.9rem;margin:0;max-width:850px;line-height:1.6;">
                    Pimpinan Redaksi (Editor-in-Chief): <b style="color:#ffffff;">Ir. Nor Anisa, S.Kom., M.Kom.</b><br>
                    Wadah resmi publikasi karya ilmiah dosen dan tugas akhir mahasiswa di bidang komputasi awan, IoT, rekayasa perangkat lunak, sains data, UI/UX, dan bisnis digital.
                </p>
            </div>
            <div style="background:rgba(0,0,0,0.25);border:1px solid rgba(255,255,255,0.2);padding:14px 20px;border-radius:8px;text-align:right;">
                <span style="color:#94a3b8;font-size:0.78rem;font-weight:600;display:block;">ISSN STATUS</span>
                <b style="color:#ffffff;font-size:0.95rem;display:block;margin-bottom:4px;">E-ISSN: 2988-xxxx</b>
                <span style="background:#10b981;color:#ffffff;padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:800;">CALL FOR PAPERS</span>
            </div>
        </div>
    </div>
    """)

    # TATA LETAK 2 KOLOM KHAS JURNAL ILMIAH (KONTEN 75% + SIDEBAR 25%)
    with gr.Row():
        # KOLOM UTAMA (MAIN COLUMN)
        with gr.Column(scale=3):
            with gr.Tabs():
                # TAB 1: BERANDA
                with gr.Tab("🏛️ Beranda & Ruang Lingkup"):
                    gr.HTML("""
                    <div class="journal-card">
                        <h3 style="color:#0f172a;font-size:1.3rem;font-weight:800;margin-top:0;border-bottom:2px solid #e2e8f0;padding-bottom:10px;">Fokus dan Ruang Lingkup (Focus & Scope)</h3>
                        <p style="color:#334155;font-size:0.95rem;line-height:1.75;margin-bottom:20px;">
                            <b>J-DIGITEK (Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan)</b> adalah jurnal ilmiah nasional berstandar terbuka (Open Access) yang mempublikasikan hasil penelitian orisinal dan pengembangan sistem terapan. Jurnal ini menaungi 4 Track keilmuan utama:
                        </p>
                        
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;">
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:4px solid #0284c7;border-radius:8px;padding:16px;">
                                <b style="color:#0f172a;font-size:0.95rem;display:block;margin-bottom:6px;">Track 1: Rekayasa Software, UI/UX & Game</b>
                                <p style="color:#475569;font-size:0.85rem;line-height:1.6;margin:0;">
                                    Software Testing, Pengujian Kualitas Sistem, UI/UX Design, Interaksi Manusia & Komputer (IMK), dan Pengembangan Aplikasi Game Edukatif.
                                </p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:4px solid #0d9488;border-radius:8px;padding:16px;">
                                <b style="color:#0f172a;font-size:0.95rem;display:block;margin-bottom:6px;">Track 2: Cloud Computing, Jaringan & IoT</b>
                                <p style="color:#475569;font-size:0.85rem;line-height:1.6;margin:0;">
                                    Pengantar IoT, Smart Device Sensor, Jaringan Komputer, Infrastruktur Cloud, dan Layanan Virtual Machine untuk Otomasi Server.
                                </p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:4px solid #4f46e5;border-radius:8px;padding:16px;">
                                <b style="color:#0f172a;font-size:0.95rem;display:block;margin-bottom:6px;">Track 3: Sains Data, Sistem Cerdas & NLP</b>
                                <p style="color:#475569;font-size:0.85rem;line-height:1.6;margin:0;">
                                    Big Data Analytics, Sistem Pendukung Keputusan (SPK), Analisis Sentimen Media Sosial, dan Pemrosesan Bahasa Alami (NLP).
                                </p>
                            </div>
                            <div style="background:#f8fafc;border:1px solid #cbd5e1;border-top:4px solid #d97706;border-radius:8px;padding:16px;">
                                <b style="color:#0f172a;font-size:0.95rem;display:block;margin-bottom:6px;">Track 4: Transformasi Digital & Bisnis</b>
                                <p style="color:#475569;font-size:0.85rem;line-height:1.6;margin:0;">
                                    Transformasi Digital UMKM, Bisnis Digital, Digital Innovation, Kewirausahaan Teknologi, dan Digital Community.
                                </p>
                            </div>
                        </div>

                        <h3 style="color:#0f172a;font-size:1.15rem;font-weight:800;border-bottom:2px solid #e2e8f0;padding-bottom:8px;margin-bottom:12px;">Pengumuman Dewan Redaksi</h3>
                        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:16px;">
                            <b style="color:#1e40af;font-size:0.95rem;display:block;margin-bottom:4px;">📢 Call for Papers: Volume 1 Nomor 1 (Edisi Perdana 2026)</b>
                            <p style="color:#1e3a8a;font-size:0.88rem;line-height:1.6;margin:0;">
                                Dewan Redaksi J-DIGITEK mengundang para dosen, mahasiswa tingkat akhir, dan praktisi industri untuk mengajukan naskah hasil penelitian dan tugas akhir. Seluruh naskah yang masuk akan ditelaah oleh tim reviewer profesional di bawah pimpinan <b>Ir. Nor Anisa, S.Kom., M.Kom.</b>
                            </p>
                        </div>
                    </div>
                    """)

                # TAB 2: PENGAJUAN NASKAH
                with gr.Tab("📝 Pengajuan Naskah (Submit Paper)"):
                    gr.Markdown("### Formulir Pengajuan Naskah Ilmiah (Author Submission)\nPastikan naskah ditulis mengikuti kaidah ilmiah yang baku dan memuat kebaruan (novelty). Seluruh isian bertanda * wajib diisi.")
                    
                    sub_title = gr.Textbox(label="Judul Naskah Ilmiah *", placeholder="Contoh: Analisis Sentimen Opini Publik Menggunakan Naive Bayes...")
                    sub_authors = gr.Textbox(label="Nama Penulis & Dosen Pembimbing *", placeholder="Contoh: Arpan Mualief Saprizal (Mahasiswa), Ir. Nor Anisa, S.Kom., M.Kom. (Dosen Pembimbing)")
                    
                    with gr.Row():
                        sub_affil = gr.Textbox(label="Afiliasi Kampus / Program Studi", value="Program Studi Informatika, Universitas Sari Mulia")
                        sub_email = gr.Textbox(label="Alamat Email Korespondensi", placeholder="penulis@unism.ac.id")
                    
                    sub_track = gr.Dropdown(
                        label="Pilih Bidang Fokus (Track) *",
                        choices=[
                            "Track 1: Rekayasa Software, UI/UX & Game",
                            "Track 2: Cloud Computing, Jaringan & IoT",
                            "Track 3: Sains Data, Sistem Cerdas & NLP",
                            "Track 4: Transformasi Digital & Bisnis"
                        ],
                        value="Track 3: Sains Data, Sistem Cerdas & NLP"
                    )
                    
                    sub_abstract = gr.TextArea(label="Abstrak Naskah (Bahasa Indonesia / Inggris) *", placeholder="Ringkasan latar belakang, metodologi, hasil temuan, dan kesimpulan...", lines=5)
                    sub_keywords = gr.Textbox(label="Kata Kunci (Keywords)", placeholder="Contoh: Machine Learning, NLP, Cloud, IoT, UI/UX")
                    sub_file = gr.File(label="Lampirkan Dokumen Naskah Lengkap (PDF)", file_types=[".pdf", ".docx"])
                    
                    sub_btn = gr.Button("🚀 Kirimkan Naskah ke Dewan Redaksi", variant="primary", size="lg")
                    sub_output = gr.TextArea(label="Bukti Tanda Terima Pengajuan (Submission Receipt)", interactive=False, lines=6)

                    sub_btn.click(
                        fn=submit_manuscript,
                        inputs=[sub_title, sub_authors, sub_affil, sub_email, sub_track, sub_abstract, sub_keywords, sub_file],
                        outputs=[sub_output]
                    )

                # TAB 3: DASBOR EDITOR
                with gr.Tab("👩‍🏫 Ruang Redaksi & Reviewer (Khusus Bu Nor Anisa)"):
                    gr.Markdown("### Portal Dewan Redaksi & Evaluasi Naskah\nHalaman khusus untuk Editor-in-Chief (Ir. Nor Anisa, S.Kom., M.Kom.) untuk memantau, memeriksa, dan memutuskan status naskah yang diajukan penulis.")
                    
                    with gr.Row():
                        editor_pin = gr.Textbox(label="Masukkan PIN Editor", type="password", placeholder="PIN Rahasia Dewan Redaksi...", scale=3)
                        editor_login_btn = gr.Button("🔓 Buka Antrean Redaksi", variant="primary", scale=1)

                    editor_status = gr.Markdown("Status: *Menunggu verifikasi PIN Dewan Redaksi*")
                    editor_table = gr.Dataframe(
                        headers=["ID", "Judul Naskah", "Penulis", "Bidang Fokus (Track)", "Status Editorial", "Tanggal Masuk"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        label="Tabel Antrean Naskah Masuk (Real-Time Cloud Supabase)",
                        interactive=False
                    )

                    editor_login_btn.click(
                        fn=verify_editor_and_load,
                        inputs=[editor_pin],
                        outputs=[editor_status, editor_table]
                    )

                    gr.Markdown("---")
                    gr.Markdown("#### Formulir Evaluasi Peer-Review & Keputusan Editorial")
                    with gr.Row():
                        with gr.Column(scale=1):
                            eval_id = gr.Number(label="Nomor ID Naskah", precision=0, placeholder="Contoh: 1")
                            eval_load_btn = gr.Button("🔍 Buka Rincian Naskah", variant="secondary")
                            eval_details = gr.TextArea(label="Metadata Naskah", interactive=False, lines=6)
                        with gr.Column(scale=2):
                            eval_abstract = gr.TextArea(label="Teks Abstrak Naskah", interactive=False, lines=4)
                            eval_status = gr.Radio(
                                label="Keputusan Dewan Redaksi (Editorial Decision)",
                                choices=["Submitted", "Under Review", "Revision Required", "Accepted", "Published"],
                                value="Accepted"
                            )
                            eval_notes = gr.TextArea(label="Catatan Reviewer / Instruksi Revisi untuk Penulis", lines=3, placeholder="Tuliskan catatan perbaikan atau rekomendasi penerbitan...")
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

                # TAB 4: ARSIP & TERBITAN
                with gr.Tab("📚 Terbitan & Arsip Publikasi"):
                    with gr.Row():
                        gr.Markdown("### Volume 1 Nomor 1 (Edisi Perdana 2026)\nArtikel ilmiah yang telah dinyatakan lolos uji kelayakan dan resmi disetujui terbit oleh Dewan Redaksi.")
                        track_filter = gr.Dropdown(
                            label="Filter Berdasarkan Track",
                            choices=[
                                "Semua Track",
                                "Track 1: Rekayasa Software, UI/UX & Game",
                                "Track 2: Cloud Computing, Jaringan & IoT",
                                "Track 3: Sains Data, Sistem Cerdas & NLP",
                                "Track 4: Transformasi Digital & Bisnis"
                            ],
                            value="Semua Track",
                            scale=1
                        )

                    published_container = gr.HTML(value=render_published_html("Semua Track"))

                    track_filter.change(
                        fn=render_published_html,
                        inputs=[track_filter],
                        outputs=[published_container]
                    )

        # KOLOM SAMPING (SIDEBAR KHAS JURNAL ILMIAH INTERNASIONAL)
        with gr.Column(scale=1):
            gr.HTML("""
            <div style="display:flex;flex-direction:column;gap:18px;">
                <!-- Kotak 1: Dewan Redaksi -->
                <div style="background:#ffffff;border:1px solid #cbd5e1;border-top:4px solid #1e3e62;border-radius:8px;padding:16px;">
                    <b style="color:#0f172a;font-size:0.92rem;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Dewan Redaksi</b>
                    <div style="font-size:0.86rem;color:#334155;line-height:1.6;">
                        <span style="color:#64748b;font-size:0.78rem;display:block;">EDITOR-IN-CHIEF:</span>
                        <b style="color:#0f172a;">Ir. Nor Anisa, S.Kom., M.Kom.</b>
                        <span style="color:#64748b;font-size:0.8rem;display:block;margin-top:2px;">Insinyur Profesional PII & Peneliti NLP</span>
                        <hr style="border:0;border-top:1px solid #e2e8f0;margin:10px 0;">
                        <span style="color:#64748b;font-size:0.78rem;display:block;">MANAGING EDITORS:</span>
                        <b>AI Engineering & Research Lab</b>
                    </div>
                </div>

                <!-- Kotak 2: Informasi Terbitan -->
                <div style="background:#ffffff;border:1px solid #cbd5e1;border-top:4px solid #0d9488;border-radius:8px;padding:16px;">
                    <b style="color:#0f172a;font-size:0.92rem;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Informasi Jurnal</b>
                    <div style="font-size:0.85rem;color:#334155;line-height:1.6;">
                        &bull; <b>Frekuensi:</b> 2x Setahun (Juni & Des)<br>
                        &bull; <b>Bahasa:</b> Indonesia & Inggris<br>
                        &bull; <b>Aksesibilitas:</b> 100% Open Access<br>
                        &bull; <b>Peer Review:</b> Double-Blind Review<br>
                        &bull; <b>Biaya Penulis (APC):</b> Rp 0 (Bebas Biaya)
                    </div>
                </div>

                <!-- Kotak 3: Target Pengindeksan -->
                <div style="background:#ffffff;border:1px solid #cbd5e1;border-top:4px solid #d97706;border-radius:8px;padding:16px;">
                    <b style="color:#0f172a;font-size:0.92rem;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Target Pengindeksan</b>
                    <div style="display:flex;flex-direction:column;gap:6px;font-size:0.82rem;color:#334155;font-weight:600;">
                        <span style="background:#f1f5f9;padding:4px 8px;border-radius:4px;">&bull; Google Scholar</span>
                        <span style="background:#f1f5f9;padding:4px 8px;border-radius:4px;">&bull; GARUDA (Kemendikbud)</span>
                        <span style="background:#f1f5f9;padding:4px 8px;border-radius:4px;">&bull; Crossref DOI System</span>
                        <span style="background:#f1f5f9;padding:4px 8px;border-radius:4px;">&bull; Akreditasi SINTA</span>
                    </div>
                </div>

                <!-- Kotak 4: Layanan Bantuan & CS Nadia -->
                <div style="background:#ffffff;border:1px solid #cbd5e1;border-top:4px solid #2563eb;border-radius:8px;padding:16px;">
                    <b style="color:#0f172a;font-size:0.92rem;display:block;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Bantuan & Konsultasi</b>
                    <p style="color:#475569;font-size:0.82rem;line-height:1.5;margin:0 0 10px 0;">
                        Pertanyaan seputar template naskah dan alur publikasi dapat dikonsultasikan melalui layanan asistensi 24 jam.
                    </p>
                    <a href="https://wa.me/6285155133070?text=Halo%20Nadia,%20saya%20ingin%20konsultasi%20pengajuan%20naskah%20J-DIGITEK" target="_blank" style="display:block;text-align:center;background:#10b981;color:#ffffff;text-decoration:none;padding:8px 12px;border-radius:6px;font-size:0.85rem;font-weight:700;">
                        WhatsApp Asisten CS &rarr;
                    </a>
                </div>
            </div>
            """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
