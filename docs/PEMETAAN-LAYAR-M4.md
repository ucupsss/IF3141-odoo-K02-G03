# Pemetaan layar Milestone 4 — Kopitera

Diperbarui 14 November 2026 untuk modul `kopitera_master` versi `17.0.1.3.0`. Tampilan berupa screenshot langsung Odoo 17 Community, diambil dengan akun aktor yang sesuai. Seluruh 22 layar sudah tersedia dan diverifikasi.

- Screenshot final: `docs/screenshots/m4/` (nama berkas diawali ID layar).
- Isi siap salin untuk laporan (Tabel Screen Mockup 1.36–1.57 dan Tabel Pemetaan Layar 1.58): `docs/M4-I7-User-Interface-Kopitera.docx`.
- Penomoran tabel mengasumsikan penomoran Bab I sudah diurutkan ulang (lihat `CATATAN-REVISI-LAPORAN.md`).

## Keputusan rancangan

- Rilis dijalankan **manual oleh Manager Area** pada atau setelah tanggal rilis (UC-06, FR-08).
- Pengaju tidak boleh memeriksa pengajuannya sendiri. Akun `reviewerbar`/`reviewerkitchen` adalah akun uji kedua untuk peran Head Bar/Head Kitchen, bukan aktor baru.
- Isi resep berlaku tidak berubah selama pengajuan diproses. Rilis mengaktifkan versi baru, mengarsipkan versi lama, dan memperbarui BoM Manufacturing.
- Staf Bar hanya membaca resep minuman berlaku; Staf Kitchen hanya makanan. Manager on Duty dan Head Floor membaca keduanya. Head Floor juga menerima notifikasi rilis dan dapat membuat laporan.

## Daftar layar

| ID | Nama layar | UC | Pengguna | Berkas screenshot |
|---|---|---|---|---|
| L01 | Login | Semua | Semua pengguna | `L01_login.png` |
| L02 | Katalog Menu | UC-01, UC-10 | Head, Manager, pengguna cabang | `L02_katalog_menu.png` |
| L03 | Detail Menu | UC-01, UC-10 | Head Bar/Kitchen | `L03_detail_menu.png` |
| L04 | Pengajuan Menu | UC-01 | Head Bar/Kitchen | `L04_pengajuan_menu.png`, `L04b_…perbandingan.png` |
| L05 | Daftar Bahan Baku | UC-02 | Head Bar/Kitchen, Manager | `L05_bahan_baku.png` |
| L06 | Pengajuan Bahan Baku | UC-02 | Head Bar/Kitchen | `L06_pengajuan_bahan.png` |
| L07 | Daftar Pengajuan Resep | UC-03/04/05 | Head Bar/Kitchen, Manager | `L07_daftar_pengajuan_resep.png` |
| L08 | Draf Resep dan Gramasi | UC-03 | Head Bar/Kitchen (pengaju) | `L08_draf_resep.png` |
| L09 | Pemeriksaan Pengajuan | UC-04 | Head Bar/Kitchen (pemeriksa) | `L09_pemeriksaan.png` |
| L10 | Perbandingan Gramasi | UC-04 | Pemeriksa, Manager | `L10_perbandingan_gramasi.png` |
| L11 | Persetujuan/Penolakan | UC-05 | Manager Area | `L11_persetujuan.png` |
| L12 | Menunggu Rilis | UC-06 | Manager Area | `L12_menunggu_rilis.png` |
| L13 | Konfirmasi dan Hasil Rilis | UC-06 | Manager Area | `L13_konfirmasi_rilis.png`, `L13b_hasil_rilis.png` |
| L14 | Riwayat Versi Resep | UC-07 | Head Bar/Kitchen, Manager | `L14_riwayat_versi.png` |
| L15 | Detail Versi Arsip dan Log Audit | UC-07, UC-08 | Head Bar/Kitchen, Manager | `L15_detail_versi_arsip.png`, `L15b_…perbandingan.png`, `L15c_log_audit.png` |
| L16 | Pemulihan Versi | UC-08 | Manager Area | `L16_pemulihan_versi.png` |
| L17 | Daftar Akun Pengguna | UC-09 | Manager Area | `L17_daftar_akun.png` |
| L18 | Form Akun dan Peran | UC-09 | Manager Area | `L18_form_akun.png` |
| L19 | Resep Berlaku (baca saja) | UC-10 | Staf, MoD, Head Floor | `L19a_…`, `L19_resep_berlaku_staf.png` |
| L20 | Laporan Rekap dan Ekspor | UC-11 | Manager, Head Bar/Kitchen, Head Floor | `L20_laporan.png`, `L20b_pdf_lembar_resep-1.png`, `L20c_pdf_riwayat-1.png` |
| L21 | Notifikasi | UC-12 | Manager, Head Bar/Kitchen, Head Floor | `L21_notifikasi.png` (Head Floor), `L21b_notifikasi_manager.png` |
| L22 | Migrasi Data Awal dan Log Migrasi | UC-13 | Pengembang Eksternal | `L22a_…unggah`, `L22_…pratinjau`, `L22b_…selesai`, `L22c_log_migrasi.png` |

## Pemetaan use case ke layar (I.7.2)

| Use case | Layar |
|---|---|
| Prasyarat semua UC | L01 |
| UC-01 Mengelola Data Menu | L02, L03, L04 |
| UC-02 Mengelola Data Bahan Baku | L05, L06 |
| UC-03 Mengelola Resep dan Gramasi | L07, L08 |
| UC-04 Memeriksa Pengajuan | L07, L09, L10 |
| UC-05 Menyetujui atau Menolak Pengajuan | L07, L11 |
| UC-06 Merilis Perubahan | L12, L13 |
| UC-07 Melihat Riwayat dan Versi Resep | L14, L15 |
| UC-08 Memulihkan Versi Resep | L15, L16 |
| UC-09 Mengelola Akun dan Hak Akses | L17, L18 |
| UC-10 Melihat Data Berlaku | L02, L03, L19 |
| UC-11 Membuat Laporan Rekap dan Ekspor | L20 |
| UC-12 Menerima Notifikasi Pengajuan dan Rilis | L21 |
| UC-13 Memigrasikan Data Awal dari Excel | L22 |

## Mengambil ulang screenshot

Screenshot dibuat dari database demo bersih: `setup_kopitera_demo.py` → `seed_master_demo.py` → beberapa pengajuan pada tiap status (draf, menunggu pemeriksaan, menunggu persetujuan, menunggu rilis, ditolak, versi arsip). Jika ingin mengambil ulang di laptop sendiri, gunakan akun aktor yang sesuai, bukan admin, agar pembatasan akses terlihat.
