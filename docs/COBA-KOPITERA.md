# Cara mencoba Kopitera — tahap pertama

## Membuka aplikasi

1. Jalankan Docker Desktop.
2. Buka PowerShell di folder repository, lalu jalankan:

   ```powershell
   docker compose up -d
   ```

3. Buka http://localhost:8070/web?debug=1 lalu pilih aplikasi **Kopitera** dari menu aplikasi kiri atas. Muat ulang halaman jika aplikasi baru belum terlihat.
4. Gunakan akun uji pada `AKUN-UJI-LOKAL.txt` di folder proyek. File ini berisi kata sandi lokal dan tidak masuk GitHub. Kredensial admin tetap berada di `AKSES-LOKAL.txt`.

## Akun yang disediakan

| Login | Peran | Pemakaian |
|---|---|---|
| headbar.kopitera | Head Bar — pengaju | Membuat dan mengubah draf minuman |
| reviewerbar.kopitera | Head Bar — pemeriksa | Memeriksa draf minuman milik pengguna lain |
| headkitchen.kopitera | Head Kitchen — pengaju | Membuat dan mengubah draf makanan |
| reviewerkitchen.kopitera | Head Kitchen — pemeriksa | Memeriksa draf makanan milik pengguna lain |
| manager.kopitera | Manager Area | Persetujuan, penolakan, dan rilis kedua divisi |
| stafbar.kopitera | Staf Bar | Membaca resep minuman yang berlaku |
| stafkitchen.kopitera | Staf Kitchen | Membaca resep makanan yang berlaku |
| mod.kopitera | Manager on Duty | Membaca resep berlaku kedua divisi |
| headfloor.kopitera | Head Floor | Membaca resep berlaku kedua divisi, menerima notifikasi rilis, membuat laporan |
| dev.kopitera | Pengembang Eksternal | Migrasi data awal dari Excel dan Log Migrasi |

Akun `dev.kopitera` mewakili Pengembang Eksternal (admin juga dapat menjalankan migrasi). Dua akun per peran head membantu memperagakan pengaju dan pemeriksa berbeda. Cabang setiap akun tercatat pada Administrasi → Akun Pengguna.

## Latihan pertama: perubahan Es Kopi Susu

Data resep awal Es Kopi Susu dan Nasi Goreng sepenuhnya fiktif. Masing-masing sudah memiliki versi 1 yang berlaku dan satu draf latihan. Angka takaran bukan rekomendasi produksi.

1. Login **headbar.kopitera**. Buka Kopitera → Pengajuan → Pengajuan Resep, lalu pilih draf Es Kopi Susu.
2. Pada tab Komposisi dan Gramasi, ubah Sirup Gula Aren dari 20 menjadi 15 ml. Pada tab Pengajuan dan Pemeriksaan, isi alasan, misalnya “Contoh pengurangan rasa manis untuk latihan”. Simpan, lalu klik **Kirim untuk Diperiksa**.
3. Logout dan login **reviewerbar.kopitera**. Buka pengajuan yang sama. Isi Catatan Pemeriksaan, simpan, lalu klik **Sesuai, Teruskan**. Tombol **Minta Perbaikan** mengembalikan draf kepada pengaju.
4. Login **manager.kopitera**. Isi Tanggal Rilis dengan tanggal hari ini dan Alasan Keputusan, simpan, lalu klik **Setujui**. Resep versi 1 tetap berlaku pada tahap ini.
5. Klik **Rilis ke Seluruh Cabang** dan konfirmasi. Resep menjadi versi 2; versi 1 masuk Riwayat → Riwayat Versi Resep dengan status Arsip, dan BoM Manufacturing ikut diperbarui. Rilis sebelum tanggal yang ditetapkan ditolak oleh sistem.
6. Login **stafbar.kopitera**, buka Kopitera → Data Induk → Resep Berlaku. Pastikan Es Kopi Susu versi 2 tampil dengan takaran baru dan tidak dapat diedit. Nasi Goreng tidak tampil pada akun Staf Bar.

Untuk latihan berikutnya, Head Bar dapat membuka Data Induk → Katalog Menu → Es Kopi Susu → **Ajukan Resep / Perubahan**. Sistem menyalin resep berlaku ke draf baru. Menggunakan browser privat atau profil browser terpisah dapat memudahkan pergantian akun; tab biasa dalam satu profil berbagi sesi login yang sama.

## Fitur lanjutan

Perbandingan gramasi, log audit, pemulihan versi, akun dan peran, laporan, notifikasi, migrasi Excel, dan sinkronisasi BoM sudah tersedia sejak versi 17.0.1.2.0. Lihat `COBA-FITUR-LANJUTAN.md`. Penyesuaian dengan laporan Milestone 4 (kategori menu, jumlah porsi, satuan takaran, laporan CSV) ada di `COBA-FITUR-V130.md`. Modul ini prototipe tugas besar, bukan implementasi produksi.

## Memasang di laptop anggota lain

Setelah mengikuti README untuk menyiapkan database dan login admin lokal:

```powershell
docker compose stop web
docker compose run --rm web odoo -d odoo_app -i kopitera_master --stop-after-init --without-demo=all
docker compose up -d
```

XML modul menyediakan menu dan bahan contoh, tanpa password atau akun kelompok. `scripts/setup_kopitera_demo.py` dapat membuat akun uji dan resep awal secara lokal, menggunakan Python standar dan `AKSES-LOKAL.txt` dengan baris `Database: ...`, `Login: ...`, dan `Password: ...`. Script menyimpan password acak ke `AKUN-UJI-LOKAL.txt`; kedua berkas wajib tetap diabaikan Git. Script memakai alamat lokal port 8070. Tidak ada akun email sungguhan; akun uji memakai domain `example.test` dan notifikasi dalam aplikasi.

## Validasi pengembangan

Pengujian integrasi berada di `scripts/check_kopitera.py`. Jalankan lewat Odoo shell setelah akun contoh dibuat. Semua perubahan pengujian dibatalkan di akhir transaksi; data contoh tetap ada.

```powershell
docker compose stop web
Get-Content -Raw scripts/check_kopitera.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --log-level=warn
docker compose up -d
```

Referensi teknis: [keamanan Odoo 17](https://www.odoo.com/documentation/17.0/developer/reference/backend/security.html) dan [arsitektur tampilan Odoo 17](https://www.odoo.com/documentation/17.0/developer/reference/user_interface/view_architectures.html).
