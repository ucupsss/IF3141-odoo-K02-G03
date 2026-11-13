# Catatan revisi laporan agar selaras dengan implementasi

Disusun 10 November 2026 setelah modul `kopitera_master` versi `17.0.1.2.0` selesai. Dokumen ini daftar bagian Milestone 2, 3, dan 4 yang perlu disesuaikan oleh pemilik bagian masing-masing. Usulan kalimat bersifat saran; sesuaikan gaya penulisan dengan laporan.

## 1. Keputusan platform (berlaku untuk M2, M3, M4)

Laporan menyebut **Odoo Online edisi Standard** dengan modul **PLM (Enterprise)** dan larangan modul kustom. Implementasi tugas besar mengikuti *IF3141 - Tutorial Odoo*:

- **Odoo 17 Community** dijalankan melalui **Docker** (PostgreSQL 16), bukan Odoo Online.
- PLM/ECO adalah fitur Enterprise dan tidak tersedia. Alur pengajuan, pemeriksaan, persetujuan, rilis, versi, dan pemulihan dibuat sebagai **modul kustom `kopitera_master`** (syarat tutorial: minimal satu modul *custom add-on from scratch*).
- Modul bawaan yang tetap dipakai: **Manufacturing (`mrp`)** dan **Inventory (`stock`)**. Setiap resep yang dirilis disalin otomatis menjadi **Bill of Materials** aktif; BoM versi lama diarsipkan.

Usulan kalimat pengganti umum:

> Sistem dibangun di atas ERP Odoo 17 Community yang dijalankan secara mandiri (self-hosted) menggunakan Docker. Alur pengajuan, pemeriksaan, persetujuan, rilis, dan versi resep diimplementasikan sebagai modul kustom `kopitera_master`, sedangkan resep yang berlaku disinkronkan menjadi Bill of Materials pada modul Manufacturing.

## 2. Milestone 2

| Bagian | Isi sekarang | Usulan perubahan |
|---|---|---|
| II.1.1 paragraf 2 | Persetujuan dan riwayat versi melalui modul PLM/ECO | Melalui modul kustom `kopitera_master`; resep berlaku disinkronkan ke BoM Manufacturing |
| Tabel 2.1 Metode Implementasi | Odoo Standard (Odoo Online) oleh konsultan | Odoo 17 Community self-hosted dengan modul kustom; konfigurasi/pengembangan oleh pengembang eksternal |
| Tabel 2.1 Langkah 4 | Konfigurasi PLM | Pengembangan modul kustom alur persetujuan, riwayat, dan pemulihan versi |
| Tabel 2.2 Cost | Lisensi Odoo Standard Rp137.500/pengguna/bulan | Odoo Community tidak berlisensi per pengguna; biaya berubah menjadi server/VPS dan pemeliharaan. **Hitung ulang** total tahun pertama dan nilai *Cost* di Tabel 2.13–2.14 (pemilik bagian) |
| Tabel 2.2 Technical | *Hosting* dan pencadangan disediakan Odoo Online; tanpa kode khusus | Server Docker dikelola pengembang eksternal; pencadangan memakai `scripts/export_db`; ada modul kustom |
| III.4 Batasan | "paket Standard di Odoo Online tidak mendukung modul kustom" | Hapus; ganti dengan batasan Community (tanpa fitur Enterprise seperti PLM) |
| IV.2 Information Technology | Berlangganan Odoo Standard di Odoo Online | Menjalankan Odoo 17 Community di server sendiri/VPS dengan modul kustom dan pencadangan terjadwal |

## 3. Milestone 3

| ID | Usulan perubahan |
|---|---|
| Bab I.1 | "dibangun di atas ERP Odoo Online" → "dibangun di atas Odoo 17 Community (self-hosted) dengan modul kustom `kopitera_master`" |
| TL-01 | Odoo 17 Community (Docker) |
| TL-02 | Modul kustom `kopitera_master` + Manufacturing (BoM) + Inventory; PLM dihapus |
| TJ-02 | Server/VPS yang menjalankan container Odoo dan PostgreSQL, diakses lewat HTTPS |
| BW-01 | "mengajukan perubahan melalui Engineering Change Order" → "melalui Pengajuan Resep" |
| FR-05, FR-06, FR-07, FR-08 | Ganti istilah ECO/PLM dengan pengajuan resep pada modul kustom. FR-08: tombol **Rilis ke Seluruh Cabang** (bukan *Apply Changes*) |
| FR-11 | Log audit tersimpan pada model Log Audit (permanen, tidak dapat diubah/dihapus) dan chatter |
| QR-2 | 2FA tersedia lewat modul Community `auth_totp`; HTTPS bergantung pada konfigurasi server |
| QR-3 | SLA Odoo Cloud tidak berlaku. Ganti dengan target pencadangan sendiri (mis. backup harian via `scripts/export_db`) |
| QR-6 | Sudah diterapkan: takaran ditampilkan dengan ketelitian 0,1 |
| AR-1 | Bukan "tanpa instalasi lokal": sistem berjalan pada satu server Docker, pengguna cabang cukup memakai peramban |
| AR-4, DR-5 | Bukan "hanya modul bawaan": modul kustom `kopitera_master` di atas `mail`, `mrp`, `stock` |
| DR-1, DR-3 | Biaya lisensi diganti biaya server dan pemeliharaan (hitung ulang) |
| DR-6 | Ekspor Excel/CSV sudah tersedia lewat menu Laporan; cadangan basis data lewat `scripts/export_db` |

## 4. Milestone 4

| Bagian | Masalah | Usulan |
|---|---|---|
| DFD Level 2 Proses 3 (subproses 3.3) | Menyebut rilis berjalan **otomatis** saat jadwal terpicu | Rilis **manual** oleh Manager Area pada/sesudah tanggal rilis (sesuai FR-08, UC-06, dan implementasi) |
| Kamus Data DFD | DF-08, DF-09, DF-10, DF-11, DF-12, DF-14 adalah data keluaran tetapi kolom *Source* berisi entitas dan *Destination* berisi proses | Tukar: *Source* = proses, *Destination* = entitas |
| Kamus Data DFD DF-11 | Typo "Hear Bar" | "Head Bar" |
| Penomoran tabel/gambar Bab I | Tabel 1.3 tidak ada; Tabel 1.8 dipakai dua kali; seluruh tabel kelas berlabel "Tabel 1.9"; Gambar 1.5/1.6 dipakai ganda | Urutkan ulang. Jika urutan: 1.1 Kamus Data, 1.2 Basis Data, 1.3 Aktor, 1.4 Use Case, 1.5–1.17 Detail UC, 1.18–1.34 Kelas, maka Screen Mockup mulai **Tabel 1.35** dan Pemetaan Layar **Tabel 1.57** (sudah dipakai di `M4-I7-User-Interface-Kopitera.docx`) |
| I.7.1 dan I.7.2 | Masih template | Salin dari `docs/M4-I7-User-Interface-Kopitera.docx` |
| Tabel Aktor A-05 Head Floor | — | Sudah sesuai: Head Floor kini punya grup sendiri (laporan + notifikasi rilis) |

## 5. Pemetaan ERD/Class Diagram ke model Odoo

ERD dan class diagram (bagian A) sudah hampir 1:1 dengan implementasi. Satu perbedaan: **Pengajuan resep dan Versi Resep disimpan pada satu model** (`kopitera.recipe`). Pengajuan yang dirilis *menjadi* versi berlaku, dan versi lama berstatus Arsip. Ini konsisten dengan relasi ERD "Pengajuan menghasilkan satu Versi Resep" (1:1). Saran: tambahkan satu paragraf penjelasan di bawah ERD atau tabel berikut.

| Entitas ERD / Kelas | Model Odoo | Catatan |
|---|---|---|
| Akun | `kopitera.account` (+ `res.users`) | Nama, login, jabatan, cabang, peran, status |
| Menu | `kopitera.menu` | Jenis menu, kategori, alergen, status ketersediaan, `active`, `revision`, resep berlaku |
| Bahan Baku | `kopitera.ingredient` | Satuan baku g/kg/ml/l/pcs, area penggunaan |
| Pengajuan (menu/bahan) | `kopitera.master.change` | Snapshot data sebelum dan sesudah |
| Pengajuan (resep) + Versi Resep | `kopitera.recipe` | Status draf → … → berlaku/arsip; `previous_recipe_id`, `restored_from_id` (= ID Versi Asal) |
| Komposisi Resep | `kopitera.recipe.line` | Takaran dan satuan takaran (sekategori dengan satuan baku) |
| Log Audit | `kopitera.audit.log` | Permanen; nilai sebelum/sesudah |
| Notifikasi | `kopitera.notification` | Status baca, penerima |
| Log Migrasi | `kopitera.migration.log` | Jumlah berhasil/gagal, catatan |
| FormDataInduk, HalamanPengajuan, HalamanData, HalamanAdmin | View form/list Odoo, wizard laporan, wizard pemulihan, wizard migrasi | Kelas *boundary* |
| KontrolDataInduk, KontrolPengajuan, KontrolData, KontrolAdmin | Method `action_*` pada model | Kelas *control* |
| — | `mrp.bom` | Salinan baca resep berlaku (BoM Manufacturing) |

## 6. Untuk Bab II (rencana pengujian, bagian B)

Skenario uji dapat mengacu pada skrip yang sudah lulus. Setiap baris `expect`/`denied` adalah satu kasus uji dengan hasil yang diharapkan:

- `scripts/check_kopitera.py`: 25 pemeriksaan alur resep (FR-04, FR-05, FR-07, FR-08, FR-10)
- `scripts/check_kopitera_master.py`: 41 pemeriksaan menu/bahan (FR-01, FR-02, FR-03)
- `scripts/check_kopitera_v120.py`: 70 pemeriksaan perbandingan, log audit, pemulihan, akun, laporan, notifikasi, migrasi, BoM (FR-06, FR-09, FR-10, FR-11, FR-12)

## 7. Pembaruan 14 November 2026 (versi 17.0.1.3.0)

Setelah Milestone 4 dilengkapi tim, sistem disesuaikan dengan laporan (bukan sebaliknya): kategori dan status ketersediaan menu, jumlah porsi, satuan takaran, usulan tanggal rilis, satuan kg/liter, nama unik, penolakan pengajuan ganda, laporan CSV dengan filter kategori dan nomor versi, serta nama tombol **Sesuai, Teruskan** dan **Nonaktifkan**. Rincian ada di `COBA-FITUR-V130.md`. Screenshot `docs/screenshots/m4/` dan `M4-I7-User-Interface-Kopitera.docx` sudah diambil ulang dari versi ini (Screen Mockup Tabel 1.36 sampai 1.57, Pemetaan Layar Tabel 1.58).
