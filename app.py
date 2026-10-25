# -*- coding: utf-8 -*-
"""
J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan
Journal of Digital Innovation and Applied Engineering Technology
Editor-in-Chief: Ir. Nor Anisa, S.Kom., M.Kom.
Powered by Gradio & Supabase Cloud PostgreSQL
"""

import os
import sys
import json
import base64
import urllib.request
import ssl
from datetime import datetime
import gradio as gr

try:
    import spaces
    has_spaces = True
except Exception:
    has_spaces = False

def gpu_fn(fn):
    if has_spaces:
        return spaces.GPU(fn)
    return fn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Konfigurasi Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hgfftqiyqowuvpwiybhs.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhnZmZ0cWl5cW93dXZwd2l5YmhzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MjM4MTMzNCwiZXhwIjoyMTA3OTU3MzM0fQ.bmLAmDCizeTS7KY2JWp3mG2YcMMllb_vhe0FXpkirW0")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

EDITOR_PIN = os.environ.get("EDITOR_PIN", "admin2026")

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
        return "⚠️ Mohon lengkapi seluruh formulir bertanda wajib (Judul, Penulis, Track, dan Abstrak)."

    pdf_base64 = ""
    pdf_filename = ""
    if file_obj is not None:
        try:
            filepath = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
            pdf_filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as err:
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
        "reviewer_notes": "Naskah telah masuk ke sistem antrean editorial J-DIGITEK."
    }

    res = query_supabase("j_digitek_articles", method="POST", data=payload)
    if res and len(res) > 0:
        art_id = res[0].get("id")
        return f"""✅ NASKAH BERHASIL DIKIRIM!
-------------------------------------------
ID Pengajuan: J-DIGITEK-{art_id:04d}
Judul: {title}
Penulis: {authors}
Track: {track}
Status: Submitted (Menunggu Review Tim Editor)

Bukti tanda terima ini telah disimpan permanen di basis data Supabase. Editor-in-Chief (Ir. Nor Anisa, S.Kom., M.Kom.) akan meninjau naskah Anda."""
    else:
        return "❌ Gagal menyimpan naskah ke database. Silakan periksa kembali koneksi."


def verify_editor_and_load(pin):
    if pin != EDITOR_PIN:
        return "❌ PIN Akses Editor Salah!", []
    articles = get_all_articles()
    table_data = []
    for a in articles:
        table_data.append([
            a.get("id"),
            a.get("title")[:45] + "...",
            a.get("authors")[:30],
            a.get("track")[:25],
            a.get("status"),
            a.get("created_at")[:10] if a.get("created_at") else "2026-10-25"
        ])
    return f"🟢 Akses Terverifikasi! Total {len(articles)} Naskah Terdaftar.", table_data


def load_single_article(pin, article_id):
    if pin != EDITOR_PIN:
        return "Akses ditolak.", "", "", "", ""
    try:
        aid = int(article_id)
    except:
        return "ID tidak valid.", "", "", "", ""
    res = query_supabase(f"j_digitek_articles?id=eq.{aid}")
    if not res or len(res) == 0:
        return "Naskah tidak ditemukan.", "", "", "", ""
    art = res[0]
    detail = f"""📄 RINCIAN NASKAH ID: {art.get('id')}
---------------------------------------------
Judul: {art.get('title')}
Penulis: {art.get('authors')}
Afiliasi: {art.get('affiliation')}
Email: {art.get('email')}
Track: {art.get('track')}
Status Saat Ini: {art.get('status')}
File Terlampir: {art.get('pdf_filename') or 'Tidak ada file'}"""
    return detail, art.get("abstract", ""), art.get("status", "Submitted"), art.get("reviewer_notes", ""), art.get("keywords", "")


def update_article_decision(pin, article_id, new_status, notes):
    if pin != EDITOR_PIN:
        return "❌ PIN Akses Editor Salah!", []
    try:
        aid = int(article_id)
    except:
        return "❌ Masukkan ID Naskah berupa angka yang valid.", []
    payload = {
        "status": new_status,
        "reviewer_notes": notes
    }
    res = query_supabase(f"j_digitek_articles?id=eq.{aid}", method="PATCH", data=payload)
    if res is not None:
        msg = f"✅ Keputusan Editor Berhasil Disimpan! Naskah #{aid} sekarang berstatus: {new_status}."
        _, updated_table = verify_editor_and_load(pin)
        return msg, updated_table
    return "❌ Gagal memperbarui status naskah.", []


def render_published_html(selected_track):
    articles = get_published_articles(selected_track)
    if not articles:
        return "<p style='color:#64748b;padding:20px;text-align:center;'>Belum ada naskah yang diterbitkan pada kategori ini.</p>"
    
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
        apa_citation = f"{authors} ({year}). {title}. J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan, {vol}({issue})."

        html += f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid #1e3a8a;border-radius:8px;padding:20px;box-shadow:0 2px 4px rgba(0,0,0,0.03);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="background:#e0f2fe;color:#0369a1;padding:4px 10px;border-radius:20px;font-size:0.75rem;font-weight:700;">{track}</span>
                <span style="color:#64748b;font-size:0.8rem;font-weight:600;">Vol. {vol} No. {issue} ({year})</span>
            </div>
            <h3 style="color:#0f172a;font-size:1.15rem;font-weight:800;margin:0 0 8px 0;line-height:1.4;">{title}</h3>
            <p style="color:#475569;font-size:0.88rem;margin:0 0 12px 0;"><b>Penulis:</b> {authors} &bull; <i style="color:#64748b;">{affiliation}</i></p>
            <div style="background:#f8fafc;padding:12px;border-radius:6px;margin-bottom:12px;border:1px solid #f1f5f9;">
                <b style="color:#1e293b;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px;">Abstrak:</b>
                <p style="color:#334155;font-size:0.85rem;line-height:1.6;margin:4px 0 0 0;">{abstract}</p>
            </div>
            <div style="background:#f1f5f9;padding:10px 14px;border-radius:6px;font-size:0.8rem;color:#334155;">
                <b>Sitasi APA 7th:</b> <code style="color:#0f172a;background:#e2e8f0;padding:2px 6px;border-radius:4px;">{apa_citation}</code>
            </div>
        </div>
        """
    html += "</div>"
    return html


# Tema & Desain Antarmuka Gradio
custom_css = """
body, .gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    background-color: #f8fafc !important;
}
.header-box {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
}
"""

with gr.Blocks(title="J-DIGITEK: Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan", css=custom_css) as app:
    with gr.Row():
        gr.HTML("""
        <div class="header-box">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                <span style="background:#38bdf8;color:#0f172a;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;">E-JOURNAL PORTAL</span>
                <span style="color:#cbd5e1;font-size:0.85rem;">ISSN Submission Ready &bull; Open Access</span>
            </div>
            <h1 style="color:white;font-size:1.85rem;font-weight:900;margin:0 0 6px 0;letter-spacing:-0.5px;">J-DIGITEK</h1>
            <p style="color:#93c5fd;font-size:1.05rem;font-weight:600;margin:0 0 10px 0;">Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan</p>
            <p style="color:#cbd5e1;font-size:0.85rem;margin:0;max-width:850px;line-height:1.5;">
                Pimpinan Redaksi (Editor-in-Chief): <b>Ir. Nor Anisa, S.Kom., M.Kom.</b> &bull; Menampung karya ilmiah orisinal mahasiswa & dosen di bidang komputasi awan, IoT, rekayasa perangkat lunak, sains data, UI/UX, dan transformasi bisnis digital.
            </p>
        </div>
        """)

    with gr.Tabs():
        # TAB 1: BERANDA & PROFIL
        with gr.Tab("🏛️ Beranda & Ruang Lingkup"):
            gr.HTML("""
            <div style="background:white;padding:24px;border-radius:10px;border:1px solid #e2e8f0;">
                <h2 style="color:#0f172a;font-size:1.3rem;font-weight:800;margin-top:0;">Tentang Jurnal J-DIGITEK</h2>
                <p style="color:#475569;line-height:1.7;font-size:0.92rem;">
                    <b>J-DIGITEK (Jurnal Inovasi Digital dan Rekayasa Teknologi Terapan)</b> adalah jurnal ilmiah berkala yang diterbitkan sebagai wadah diseminasi hasil penelitian, perancangan sistem, dan karya tugas akhir mahasiswa serta akademisi. Jurnal ini mengedepankan prinsip keterbukaan ilmiah (Open Access), bebas biaya publikasi bagi mahasiswa bimbingan, dan evaluasi peer-review berstandar nasional.
                </p>

                <h3 style="color:#1e3a8a;font-size:1.1rem;font-weight:800;margin-top:24px;">4 Bidang Fokus & Ruang Lingkup (Focus & Scope)</h3>
                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));gap:16px;margin-top:12px;">
                    <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;border-top:3px solid #0284c7;">
                        <h4 style="margin:0 0 8px 0;color:#0f172a;font-size:0.95rem;">Track 1: Rekayasa Software, UI/UX & Game</h4>
                        <p style="margin:0;color:#64748b;font-size:0.83rem;line-height:1.6;">
                            Software Testing, Pengujian Kualitas Perangkat Lunak, UI/UX Design, Interaksi Manusia & Komputer, serta Pengembangan Aplikasi Game Edukatif.
                        </p>
                    </div>
                    <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;border-top:3px solid #0d9488;">
                        <h4 style="margin:0 0 8px 0;color:#0f172a;font-size:0.95rem;">Track 2: Cloud Computing, Jaringan & IoT</h4>
                        <p style="margin:0;color:#64748b;font-size:0.83rem;line-height:1.6;">
                            Pengantar IoT, Smart Device, Jaringan Komputer, Infrastruktur Cloud, dan Layanan Virtual Machine untuk Otomasi Server.
                        </p>
                    </div>
                    <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;border-top:3px solid #6366f1;">
                        <h4 style="margin:0 0 8px 0;color:#0f172a;font-size:0.95rem;">Track 3: Sains Data, Sistem Cerdas & NLP</h4>
                        <p style="margin:0;color:#64748b;font-size:0.83rem;line-height:1.6;">
                            Big Data Analytics, Sistem Pendukung Keputusan (SPK), Analisis Sentimen Media Sosial, dan Pemrosesan Bahasa Alami (NLP).
                        </p>
                    </div>
                    <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;border-top:3px solid #f59e0b;">
                        <h4 style="margin:0 0 8px 0;color:#0f172a;font-size:0.95rem;">Track 4: Transformasi Digital & Bisnis</h4>
                        <p style="margin:0;color:#64748b;font-size:0.83rem;line-height:1.6;">
                            Transformasi Digital UMKM, Bisnis Digital, Digital Innovation, Kewirausahaan Teknologi, dan Pemberdayaan Digital Community.
                        </p>
                    </div>
                </div>

                <h3 style="color:#1e3a8a;font-size:1.1rem;font-weight:800;margin-top:24px;">Dewan Redaksi (Editorial Board)</h3>
                <div style="background:#f1f5f9;padding:14px;border-radius:8px;font-size:0.88rem;color:#334155;line-height:1.7;">
                    &bull; <b>Editor-in-Chief:</b> Ir. Nor Anisa, S.Kom., M.Kom. (Dosen, Peneliti NLP & Insinyur Profesional PII)<br>
                    &bull; <b>Managing Editors:</b> Tim Laboratorium AI Engineering & Research Lab<br>
                    &bull; <b>Frekuensi Penerbitan:</b> 2 Nomor per Tahun (Volume 1 Nomor 1, Juni 2026 & Volume 1 Nomor 2, Desember 2026)
                </div>
            </div>
            """)

        # TAB 2: PENGAJUAN NASKAH (SUBMISSION)
        with gr.Tab("📝 Pengajuan Naskah Mahasiswa (Submission)"):
            gr.Markdown("### Formulir Pengajuan Naskah Ilmiah Baru\nLengkapi seluruh isian di bawah ini untuk mendaftarkan naskah skripsi / artikel tugas akhir ke sistem antrean editorial J-DIGITEK.")
            with gr.Row():
                with gr.Column(scale=2):
                    sub_title = gr.Textbox(label="Judul Naskah Ilmiah *", placeholder="Contoh: Analisis Sentimen Opini Publik Menggunakan Algoritma Naive Bayes...")
                    sub_authors = gr.Textbox(label="Penulis (Mahasiswa & Dosen Pembimbing) *", placeholder="Contoh: Ahmad Fadilah (Mahasiswa), Ir. Nor Anisa, S.Kom., M.Kom. (Dosen Pembimbing)")
                    with gr.Row():
                        sub_affil = gr.Textbox(label="Afiliasi Kampus / Prodi", value="Program Studi Informatika, Universitas Sari Mulia")
                        sub_email = gr.Textbox(label="Email Korespondensi", placeholder="mahasiswa@unism.ac.id")
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
                    sub_abstract = gr.TextArea(label="Abstrak Naskah *", placeholder="Tuliskan latar belakang, metode, hasil temuan, dan kesimpulan singkat...", lines=6)
                    sub_keywords = gr.Textbox(label="Kata Kunci (Keywords)", placeholder="Contoh: Machine Learning, NLP, Cloud, IoT, UI/UX")
                with gr.Column(scale=1):
                    sub_file = gr.File(label="Unggah Berkas Naskah Lengkap (PDF)", file_types=[".pdf", ".docx"])
                    sub_btn = gr.Button("🚀 Kirimkan Naskah (Submit Manuscript)", variant="primary", size="lg")
                    sub_output = gr.TextArea(label="Bukti Tanda Terima Pengajuan", interactive=False, lines=8)

            sub_btn.click(
                fn=submit_manuscript,
                inputs=[sub_title, sub_authors, sub_affil, sub_email, sub_track, sub_abstract, sub_keywords, sub_file],
                outputs=[sub_output]
            )

        # TAB 3: RUANG KERJA EDITOR
        with gr.Tab("👩‍🏫 Dasbor Editor & Reviewer (Khusus Bu Nor Anisa)"):
            gr.Markdown("### Panel Pengelolaan Editorial & Penilaian Naskah Masuk\nKhusus untuk Dewan Redaksi dan Dosen Pembimbing (Ir. Nor Anisa, S.Kom., M.Kom.). Masukkan PIN Editor untuk membuka data naskah.")
            with gr.Row():
                editor_pin = gr.Textbox(label="PIN Akses Editor", type="password", placeholder="Masukkan PIN Editor...", scale=3)
                editor_login_btn = gr.Button("🔓 Buka Dasbor Editor", variant="secondary", scale=1)

            editor_status = gr.Markdown("Status: <i>Belum login</i>")
            editor_table = gr.Dataframe(
                headers=["ID", "Judul Naskah", "Penulis", "Track", "Status", "Tanggal"],
                datatype=["number", "str", "str", "str", "str", "str"],
                label="Daftar Seluruh Naskah Masuk",
                interactive=False
            )

            editor_login_btn.click(
                fn=verify_editor_and_load,
                inputs=[editor_pin],
                outputs=[editor_status, editor_table]
            )

            gr.Markdown("---")
            gr.Markdown("#### Formulir Keputusan Review & Penerbitan Naskah")
            with gr.Row():
                with gr.Column(scale=1):
                    eval_id = gr.Number(label="Masukkan ID Naskah yang Ingin Dinilai", precision=0)
                    eval_load_btn = gr.Button("🔍 Muat Rincian Naskah")
                    eval_details = gr.TextArea(label="Rincian Naskah", interactive=False, lines=6)
                with gr.Column(scale=2):
                    eval_abstract = gr.TextArea(label="Isi Abstrak Naskah", interactive=False, lines=5)
                    eval_status = gr.Radio(
                        label="Pilih Keputusan Editorial (Status)",
                        choices=["Submitted", "Under Review", "Revision Required", "Accepted", "Published"],
                        value="Accepted"
                    )
                    eval_notes = gr.TextArea(label="Catatan Reviewer / Catatan Perbaikan untuk Mahasiswa", lines=3)
                    eval_save_btn = gr.Button("💾 Simpan Keputusan & Terbitkan Artikel", variant="primary")
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

        # TAB 4: ARSIP & TERBITAN TERKINI
        with gr.Tab("📚 Terbitan & Arsip Publikasi (Vol. 1 No. 1, 2026)"):
            with gr.Row():
                gr.Markdown("### Volume 1 Nomor 1 (Edisi Perdana 2026)\nSeluruh artikel yang telah melalui proses peer-review dan disetujui terbit oleh Editor-in-Chief.")
                track_filter = gr.Dropdown(
                    label="Saring Berdasarkan Track",
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.launch(server_name="0.0.0.0", server_port=port, share=False)
