# Mencoba fitur versi 17.0.1.2.0

Fitur baru: perbandingan gramasi, log audit, pemulihan versi, akun dan peran oleh Manager Area, laporan PDF/Excel, notifikasi, migrasi Excel, dan sinkronisasi BoM Manufacturing. Semua data contoh fiktif. Password akun ada di `AKUN-UJI-LOKAL.txt` (tidak masuk Git).

Menu aplikasi Kopitera sekarang dikelompokkan: **Data Induk**, **Pengajuan**, **Riwayat**, **Laporan**, **Notifikasi**, **Administrasi**. Menu yang tampil berbeda untuk setiap peran.

## Upgrade dari versi 17.0.1.1.0

```powershell
cd "D:\ITB\sem 5\SISFOR\IF3141-odoo-K02-G03"
docker compose stop web
docker compose run --rm web odoo -d odoo_app -u kopitera_master --stop-after-init --without-demo=all
docker compose up -d
```

Saat upgrade, skrip migrasi otomatis:

- memindahkan `headfloor.kopitera` ke grup baru **Head Floor**;
- menambahkan admin ke grup **Pengembang Eksternal**;
- membuat data **Akun Pengguna** untuk akun uji yang sudah ada;
- menyalin resep yang sedang berlaku menjadi **BoM Manufacturing**;
- mengisi parameter `report.url = http://localhost:8069` bila belum ada, supaya PDF laporan bergaya di Docker.

Lalu jalankan skrip setup sekali lagi untuk membuat akun **`dev.kopitera`** (Pengembang Eksternal) dan mengisi cabang akun uji. Skrip tidak mereset pengajuan yang sudah kamu proses.

```powershell
python scripts/setup_kopitera_demo.py
```

## Perbandingan gramasi dan log audit (UC-04, UC-07)

1. Login `headbar.kopitera`. Buka **Data Induk → Katalog Menu → Es Kopi Susu → Ajukan Resep / Perubahan**. Ubah takaran, isi alasan, lalu **Kirim untuk Diperiksa**.
2. Login `reviewerbar.kopitera`. Buka pengajuan itu; tab **Perbandingan Gramasi** menampilkan takaran lama dan baru beserta selisihnya.
3. Setiap tindakan (diajukan, diperiksa, disetujui, dirilis) tercatat di tab **Log Audit** dan menu **Riwayat → Log Audit**. Log tidak dapat diubah atau dihapus.

## Pemulihan versi (UC-08)

1. Login `manager.kopitera`. Buka **Riwayat → Riwayat Versi Resep**, pilih versi berstatus **Arsip**.
2. Klik **Pulihkan Versi Ini**, isi alasan, lalu **Ajukan Pemulihan**.
3. Sistem membuat pengajuan baru dan mengirimkannya ke Head Bar/Head Kitchen. Setelah diperiksa, disetujui, dan dirilis, hasilnya menjadi nomor versi baru. Riwayat lama tetap utuh.

## Akun dan hak akses (UC-09)

Login `manager.kopitera` → **Administrasi → Akun Pengguna**. Manager Area dapat membuat akun (password awal minimal 8 karakter), mengganti peran, mengatur cabang, mengatur ulang password, serta menonaktifkan atau mengaktifkan kembali akun. Akun tidak dapat dihapus. Akun administrator sistem dan peran milik sendiri tidak dapat diubah dari menu ini.

## Laporan (UC-11)

Menu **Laporan** (Manager Area, Head Bar, Head Kitchen, Head Floor). Pilih jenis laporan:

- Rekap Katalog Menu Aktif
- Lembar Resep per Menu
- Rekap Riwayat Pembaruan

Lalu atur filter dan format (PDF atau Excel), lihat pratinjau, dan klik **Unduh Laporan**. Isi laporan mengikuti hak akses divisi pengguna.

## Notifikasi (UC-12)

Menu **Notifikasi** menampilkan pemberitahuan milik pengguna:

- Head Bar/Head Kitchen: pengajuan perlu diperiksa, dikembalikan, ditolak, atau disetujui.
- Manager Area: pengajuan perlu persetujuan.
- Head Floor: menu/resep yang dirilis.

Tombol **Buka** membuka pengajuannya, dan **Tandai Dibaca** menandainya sudah dibaca.

## Migrasi data awal dari Excel (UC-13)

1. Login `dev.kopitera` (atau admin). Buka **Administrasi → Migrasi Data Awal**.
2. Klik **Unduh Template** untuk format lembar *Menu*, *Bahan*, *Resep*, dan *Akun* (opsional), atau gunakan contoh `docs/contoh-migrasi-kopitera.xlsx`. Contoh ini sengaja memuat dua baris salah untuk memperlihatkan baris gagal.
3. Pilih berkas, klik **Periksa Berkas** untuk melihat pratinjau baris valid dan gagal, lalu **Impor Data Valid**.
4. Resep hasil impor langsung berlaku sebagai versi 1. Hasil impor tersimpan di **Administrasi → Log Migrasi**.
5. Akun hasil impor belum memiliki password. Manager Area mengaturnya lewat Akun Pengguna.

## BoM Manufacturing

Setiap rilis resep membuat BoM aktif untuk produk menu dan mengarsipkan BoM versi sebelumnya. Satuan `ml` ditambahkan karena Odoo 17 tidak menyediakannya. BoM dapat dilihat admin di **Manufacturing → Products → Bills of Materials**, juga pada field **BoM Manufacturing** di form resep. BoM adalah salinan baca; perubahan resep tetap melalui pengajuan Kopitera.

## Pengujian

```powershell
docker compose stop web
Get-Content -Raw scripts/check_kopitera.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
Get-Content -Raw scripts/check_kopitera_master.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
Get-Content -Raw scripts/check_kopitera_v120.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
docker compose up -d
```

Hasil yang diharapkan: `KOPITERA_CHECKS_PASSED=25`, `KOPITERA_MASTER_CHECKS_PASSED=41`, dan `KOPITERA_V120_CHECKS_PASSED=70`. Semua perubahan pengujian dibatalkan (rollback); nomor urut pengajuan dapat melompat karena sequence tidak ikut dikembalikan.
