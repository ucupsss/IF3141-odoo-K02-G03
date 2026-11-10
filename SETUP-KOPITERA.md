# Odoo lokal Kopitera

Setup mengikuti `IF3141 - Tutorial Odoo.docx`: Odoo 17 Community dan PostgreSQL 16 melalui Docker, menggunakan template https://github.com/reletz/IF3141-odoo.

## Membuka Odoo

1. Jalankan Docker Desktop dan tunggu sampai siap.
2. Buka terminal di folder proyek ini, lalu jalankan `docker compose up -d`.
3. Buka http://localhost:8070/web?debug=1. Parameter `debug=1` mengaktifkan mode developer pada sesi browser tersebut.
4. Login sebagai `admin`. Password lokal tersedia di `AKSES-LOKAL.txt` dan berbeda dari password bawaan tutorial.

Database yang digunakan: `odoo_app`. Nama perusahaan: Kopitera. Zona waktu administrator: Asia/Jakarta. Mata uang: IDR.

Odoo hanya dibuka pada alamat lokal laptop ini (127.0.0.1). PostgreSQL tidak membuka port ke host. Password PostgreSQL tersimpan di `.env`. `.env` dan `AKSES-LOKAL.txt` dikecualikan dari Git.

## Modul dasar

- Manufacturing (`mrp`): dasar resep sebagai Bill of Materials.
- Inventory (`stock`): dependensi Manufacturing; bukan perluasan lingkup tugas menjadi pengelolaan stok.
- Starter Cats (`starter_cats`): contoh resmi tutorial untuk memeriksa pemasangan custom add-on. Ini bukan modul Kopitera dan tidak dihitung sebagai modul buatan kelompok.

Modul PLM Enterprise tidak tersedia dalam Odoo Community. Alur pengajuan, pemeriksaan, persetujuan, rilis, versi, dan pemulihan resep diwujudkan melalui modul kustom `kopitera_master`. Resep yang berlaku disinkronkan menjadi Bill of Materials Manufacturing. Ke-13 use case Milestone 4 sudah tersedia.

## Perintah sehari-hari

Jalankan dari folder proyek ini:

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail 80 web
```

Untuk berhenti dengan data tetap tersimpan:

```powershell
docker compose down
```

Jangan menambahkan `-v` ketika berhenti karena opsi tersebut menghapus database dan filestore.

Setelah mengubah model modul, ikuti tutorial: gunakan `docker compose run --rm web odoo -d odoo_app -u NAMA_MODUL --stop-after-init`, bukan `exec`. File modul berada di `custom_addons/`.

Skrip backup bawaan tutorial tersedia pada `scripts/export_db.cmd`. Folder `dump/` untuk backup pribadi, bukan sarana berbagi data kelompok. Data referensi bersama sebaiknya ditulis sebagai XML dalam modul, sesuai tutorial.

## Repository kelompok

Repository kelompok: https://github.com/ucupsss/IF3141-odoo-K02-G03, merupakan fork dari template asisten. Remote `origin` mengarah ke repository kelompok dan `upstream` ke template. Undangan collaborator belum dikirim.

Anggota lain yang baru meng-clone repository harus menyalin `.env.example` menjadi `.env`, mengganti `POSTGRES_PASSWORD`, lalu menjalankan langkah Quick Start pada README. Untuk mengikuti alamat lokal pada panduan ini, gunakan `ODOO_PORT=127.0.0.1:8070`. Setiap anggota membuat password admin sendiri setelah login awal. `AKSES-LOKAL.txt` hanya tersedia pada laptop tempat setup ini dilakukan.

Pemasangan modul dasar pada database baru:

```powershell
docker compose stop web
docker compose run --rm web odoo -d odoo_app -i mrp,starter_cats --stop-after-init --without-demo=all
docker compose up -d
```

Pengaturan perusahaan, mata uang, dan zona waktu pada bagian awal merupakan kondisi instalasi lokal ini; anggota lain perlu mengaturnya sendiri sampai konfigurasi bersama dikemas sebagai XML dalam modul Kopitera. Jangan mengunggah file akses lokal, `.env`, atau dump database.

## Penyesuaian dokumen tugas

Platform implementasi sekarang adalah Odoo 17 Community lokal melalui Docker, mengikuti tutorial. Pernyataan Odoo Online Standard, penggunaan PLM Enterprise, serta larangan modul kustom pada Milestone 2 dan 3 perlu diselaraskan ketika revisi dokumen dilakukan. File laporan belum diubah pada tahap setup ini.

## Modul Kopitera

Modul `kopitera_master` versi `17.0.1.2.0` (bergantung pada `mail` dan `mrp`) mencakup UC-01 sampai UC-13:

- pengajuan menu, bahan, dan resep melalui pemeriksaan, persetujuan, serta rilis manual;
- perbandingan gramasi, log audit permanen, riwayat versi, dan pemulihan versi;
- akun dan peran yang dikelola Manager Area;
- laporan PDF/Excel dan notifikasi;
- migrasi data awal dari Excel beserta Log Migrasi;
- sinkronisasi resep berlaku ke BoM Manufacturing.

Validasi: 25 + 41 + 70 = **136 pemeriksaan** lulus, baik pada instalasi baru maupun upgrade dari 17.0.1.1.0.

- [Instalasi dan contoh resep](docs/COBA-KOPITERA.md)
- [Pengajuan menu dan bahan](docs/COBA-MENU-DAN-BAHAN.md)
- [Fitur lanjutan dan cara upgrade](docs/COBA-FITUR-LANJUTAN.md)
- [Pemetaan layar Milestone 4](docs/PEMETAAN-LAYAR-M4.md)
- [Catatan revisi laporan M2/M3/M4](docs/CATATAN-REVISI-LAPORAN.md)

Script setup membuat akun uji beserta password acak pada setiap instalasi lokal. Password disimpan hanya di `AKUN-UJI-LOKAL.txt`. Database, akun, dan status contoh dari laptop pengembang tidak disertakan dalam repository. Jika `setup_kopitera_demo.py` gagal pada `ZoneInfo` di Windows, jalankan `pip install tzdata` terlebih dahulu.
