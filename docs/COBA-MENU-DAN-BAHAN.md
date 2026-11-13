# Mencoba pengajuan menu dan bahan baku

Pembaruan lokal 10 November 2026. Semua contoh di bawah adalah data fiktif untuk tugas. Modul `kopitera_master` versi `17.0.1.1.0` sudah dipasang di Odoo lokal.

## Membuka

1. Pastikan Docker dan Odoo berjalan, lalu buka http://localhost:8070/web.
2. Muat ulang halaman agar menu baru tampil. Login sebagai `headbar.kopitera`.
3. Pilih aplikasi **Kopitera** → **Pengajuan**. Tersedia **Pengajuan Menu** dan **Pengajuan Bahan**.
4. Password tiap akun tetap berada di `AKUN-UJI-LOKAL.txt` di folder proyek. Jangan mengunggah file tersebut.

## Contoh pada instalasi pengembangan

| Contoh | Tempat | Kondisi awal setelah pemeriksaan browser |
|---|---|---|
| Es Teh Lemon — Contoh | Pengajuan Menu | Menunggu Pemeriksaan; sudah dikirim oleh akun Head Bar saat verifikasi |
| Sirup Vanila — Contoh | Pengajuan Bahan | Draf; bisa kamu kirim sendiri |

Pada instalasi baru, `scripts/seed_master_demo.py` membuat kedua contoh dalam status Draf. Pengaju perlu mengirim contoh menu terlebih dahulu sebelum mengikuti langkah pemeriksa di bawah.

Nomor pengajuan dapat melewati beberapa angka karena pengujian menggunakan sequence yang sama. Ini normal; pengujian membatalkan datanya, tetapi nomor sequence yang terpakai tidak dikembalikan.

## Melanjutkan contoh menu

1. Login `reviewerbar.kopitera`, buka **Pengajuan Menu → Es Teh Lemon — Contoh**.
2. Buka tab **Perbandingan** untuk melihat kondisi data sebelumnya dan usulan. Untuk menu baru, belum ada data sebelumnya.
3. Pada tab **Pemeriksaan dan Keputusan**, isi Catatan Pemeriksaan. Simpan, lalu pilih **Sesuai, Teruskan**. Jika perlu koreksi, gunakan **Minta Perbaikan**; pengaju harus mengubah lalu mengirim ulang draf.
4. Login `manager.kopitera`. Buka pengajuan yang sama, isi **Tanggal Rilis** dan **Alasan Keputusan**, simpan, lalu klik **Setujui**. Gunakan tanggal hari ini jika ingin langsung mencoba rilis.
5. Klik **Rilis Perubahan**, lalu konfirmasi. Baru pada tahap ini menu dibuat di Katalog Menu.
6. Head Bar kemudian dapat membuka menu tersebut dan memilih **Ajukan Resep / Perubahan** untuk menyusun resepnya. Pengguna cabang melihat menu setelah tersedia resep yang berlaku.

## Membuat menu atau bahan baru

1. Login sebagai Head Bar atau Head Kitchen sesuai divisi.
2. Buka **Pengajuan Menu** atau **Pengajuan Bahan**, klik **New**.
3. Pilih **Tambah Baru**, isi divisi dan nama yang diusulkan.
4. Untuk menu, isi deskripsi dan informasi alergen. Untuk bahan, pilih satuan baku dan area penggunaan. Isi alasan pengajuan.
5. Simpan, lalu klik **Kirim untuk Diperiksa**. Lanjutkan melalui pemeriksa berbeda, Manager Area, dan rilis seperti contoh di atas.

Draf tidak membuat data aktif. Persetujuan juga belum membuat data aktif; tindakan rilis yang menerapkannya.

## Mengubah atau menonaktifkan data

1. Dari **Katalog Menu** atau **Bahan Baku**, buka detail yang dituju.
2. Klik **Ajukan Ubah / Nonaktifkan Menu** atau **Ajukan Ubah / Nonaktifkan Bahan**. Sistem membuat draf dengan data saat ini.
3. Pilih **Ubah Data** untuk mengganti isian, atau **Nonaktifkan** untuk menghentikan penggunaan. Isi alasan.
4. Kirim melalui pemeriksaan, persetujuan, dan rilis. Pengguna biasa tidak mendapat akses edit langsung ke data master.

Aturan yang perlu diketahui:

- Bahan yang dipakai resep berlaku **tidak dapat dinonaktifkan**. Pemeriksaan dilakukan saat pengajuan dikirim dan diperiksa lagi saat rilis.
- Satuan bahan yang sudah digunakan dalam resep **tidak dapat diganti** karena dapat mengubah makna takaran, termasuk pada arsip. Ajukan bahan baru jika memang perlu satuan berbeda.
- Area penggunaan bahan bersama tidak boleh dipersempit sehingga mengecualikan divisi yang masih menggunakannya dalam resep berlaku.
- Menonaktifkan menu mengarsipkan resep berlakunya. Data dan arsip tetap disimpan, tetapi menu tidak tampil sebagai data berlaku bagi staf.
- Resep yang menggunakan menu atau bahan nonaktif tidak dapat diajukan/dirilis.
- Jika data tujuan berubah setelah pengajuan dikirim, rilis ditolak. Manager Area dapat memilih **Minta Pembaruan**, lalu pengaju memperbarui draf dan mengulangi pemeriksaan/persetujuan.
- **Minta Pembaruan** juga tersedia untuk resep yang sudah disetujui tetapi perlu diperbaiki sebelum rilis, misalnya karena bahannya dinonaktifkan.

## Apa yang sudah dan belum dicakup

UC-01 dan UC-02 kini memiliki alur tambah/ubah/nonaktif, dengan pemeriksaan, persetujuan, rilis, serta snapshot data sebelum/sesudah pada pengajuan. Pemeriksaan teknis dilakukan Head Bar/Head Kitchen; Manager Area tidak menggantikan peran pemeriksa hanya karena memiliki hak persetujuan.

Perbandingan gramasi resep, pemulihan versi, akun, laporan, notifikasi, dan migrasi Excel dijelaskan di `COBA-FITUR-LANJUTAN.md`.

## Pengujian pengembangan

Jalankan dari folder repo setelah menghentikan web sementara. Semua perubahan pengujian dibatalkan di akhir transaksi.

```powershell
docker compose stop web
Get-Content -Raw scripts/check_kopitera.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
Get-Content -Raw scripts/check_kopitera_master.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
docker compose up -d
```

`scripts/seed_master_demo.py` hanya menambah dua contoh bila belum ada, dan tidak mereset contoh yang sudah kamu proses. Gunakan melalui Odoo shell jika memasang di database lokal anggota lain setelah akun uji tersedia.
