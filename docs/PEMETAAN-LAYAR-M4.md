# Pemetaan layar Milestone 4 — Kopitera

Tanggal penyusunan: 10 November 2026. Acuan: tabel UC-01–UC-13 pada laporan Milestone 4 kelompok K02/G03. Pilihan tampilan: screenshot langsung Odoo 17 Community lokal. Dokumen ini merupakan rencana kerja dan catatan cakupan, bukan bukti bahwa semua layar telah selesai.

## Keputusan rancangan

- Rilis dijalankan **manual oleh Manager Area**, pada atau setelah tanggal rilis. Ini mengikuti UC-06 dan Milestone 3. Narasi DFD proses 3.3 di Milestone 4 yang masih menyebut rilis otomatis perlu diperbaiki oleh penanggung jawab DFD.
- Pengaju tidak boleh menjadi pemeriksa untuk pengajuannya sendiri. Akun pemeriksa tambahan adalah akun uji untuk peran Head Bar/Head Kitchen yang sama, bukan aktor organisasi baru.
- Isi resep aktif tidak berubah ketika draf dibuat, diperiksa, atau disetujui. Rilis mengaktifkan versi baru dan mengarsipkan versi sebelumnya.
- Staf Bar hanya membaca resep minuman yang berlaku; Staf Kitchen hanya resep makanan yang berlaku. Manager on Duty dan Head Floor membaca keduanya.
- Modul tahap pertama menyimpan resep pada model Kopitera tersendiri. Sinkronisasi ke Manufacturing / `mrp.bom`, konversi satuan, dan integrasi dRetail belum dilakukan. Hindari menyebut prototipe ini sebagai implementasi BoM Manufacturing lengkap dalam laporan.

## Daftar 22 layar / keadaan layar

Satu form Odoo dapat menghasilkan beberapa screenshot karena aktor, status, dan tombol yang tampil berbeda. ID L01–L22 adalah usulan penomoran layar untuk laporan; jumlah akhir harus mengikuti kebutuhan skenario, bukan kuota gambar.

| ID | Nama layar / keadaan | UC terkait | Pengguna | Kesiapan tahap pertama |
|---|---|---|---|---|
| L01 | Login | Prasyarat semua UC | Semua pengguna | Bawaan Odoo; siap |
| L02 | Katalog menu | UC-01, UC-10 | Head Bar/Kitchen, Manager Area, pengguna cabang | Daftar baca dan pengajuan tambah/ubah/nonaktif tersedia |
| L03 | Detail menu dan tautan resep berlaku | UC-01, UC-10 | Pengguna sesuai divisi | Detail baca tersedia |
| L04 | Form pengajuan menu baru/ubah/nonaktif | UC-01 | Head Bar/Kitchen | Tersedia; diperiksa, disetujui, lalu dirilis |
| L05 | Daftar dan detail bahan baku | UC-02 | Head Bar/Kitchen, Manager Area | Data referensi baca tersedia |
| L06 | Form pengajuan bahan baru/ubah/nonaktif | UC-02 | Head Bar/Kitchen | Tersedia; penonaktifan bahan yang dipakai resep berlaku ditolak |
| L07 | Daftar pengajuan resep dengan filter status | UC-03, UC-04, UC-05, UC-06 | Head Bar/Kitchen, Manager Area | Tersedia |
| L08 | Form draf resep: komposisi, gramasi, langkah, alasan | UC-03 | Head Bar/Kitchen pengaju | Tersedia; termasuk keadaan Perlu Perbaikan |
| L09 | Pemeriksaan dan catatan perbaikan | UC-04 | Head Bar/Kitchen selain pengaju | Tersedia pada form berstatus Menunggu Pemeriksaan |
| L10 | Perbandingan usulan dengan versi berlaku | UC-04, UC-08 | Pemeriksa, Manager Area | Perbandingan menu/bahan tersedia; perbandingan gramasi resep belum |
| L11 | Persetujuan/penolakan dan tanggal rilis | UC-05 | Manager Area | Tersedia pada form berstatus Menunggu Persetujuan |
| L12 | Daftar pengajuan menunggu rilis | UC-06 | Manager Area | Tersedia melalui filter Menunggu Rilis |
| L13 | Konfirmasi rilis dan hasil versi berlaku | UC-06 | Manager Area | Tombol, dialog konfirmasi, dan status hasil tersedia |
| L14 | Daftar riwayat versi resep | UC-07 | Head Bar/Kitchen, Manager Area | Daftar versi tersedia; data contoh awal hanya versi 1 |
| L15 | Detail versi arsip dan riwayat aktivitas | UC-07 | Head Bar/Kitchen, Manager Area | Form versi dan chatter tersedia; perbandingan nilai gramasi lama/baru belum lengkap |
| L16 | Form pemulihan versi dan alasan | UC-08 | Manager Area | Belum dibuat |
| L17 | Daftar akun pengguna | UC-09 | Manager Area | Pengelolaan bawaan hanya admin; delegasi aman ke Manager Area belum dibuat |
| L18 | Tambah/ubah/nonaktifkan akun dan peran | UC-09 | Manager Area | Akun uji sudah disiapkan; form khusus pengelolaan oleh Manager Area belum dibuat |
| L19 | Resep berlaku untuk staf, baca saja | UC-10 | Staf Bar/Kitchen, Manager on Duty, Head Floor | Tersedia dengan batas divisi dan status |
| L20 | Filter, pratinjau, dan ekspor laporan | UC-11 | Pengguna yang berhak sesuai laporan | Ekspor daftar bawaan Odoo; laporan PDF dan formulir rekap khusus belum dibuat |
| L21 | Notifikasi dan tautan ke pengajuan | UC-12 | Head Bar/Kitchen, Manager Area, Head Floor | Aktivitas pemeriksaan/persetujuan tersedia; notifikasi rilis ke seluruh penerima belum lengkap |
| L22 | Impor Excel dan ringkasan berhasil/gagal | UC-13 | Pengembang Eksternal | Belum dibuat sebagai alur migrasi lengkap; data referensi tahap pertama dimuat melalui XML |

## Pemetaan use case ke layar

| Use case | Layar |
|---|---|
| UC-01 Mengelola Data Menu | L02, L03, L04 |
| UC-02 Mengelola Data Bahan Baku | L05, L06 |
| UC-03 Mengelola Resep dan Gramasi | L07, L08 |
| UC-04 Memeriksa Pengajuan | L07, L09, L10 |
| UC-05 Menyetujui atau Menolak Pengajuan | L07, L11 |
| UC-06 Merilis Perubahan | L12, L13 |
| UC-07 Melihat Riwayat dan Versi Resep | L14, L15 |
| UC-08 Memulihkan Versi Resep | L15, L16, L10 |
| UC-09 Mengelola Akun dan Hak Akses | L17, L18 |
| UC-10 Melihat Data Berlaku | L02, L03, L19 |
| UC-11 Membuat Laporan Rekap dan Ekspor | L20 |
| UC-12 Menerima Notifikasi Pengajuan dan Rilis | L21, layar pengajuan/menu tujuan |
| UC-13 Memigrasikan Data Awal dari Excel | L22 |

## Urutan pengerjaan berikutnya

1. Validasi bersama anggota A/B/D bahwa aktor, alur manual, dan penomoran UC konsisten.
2. Pengajuan menu/bahan telah tersedia. Validasi kesesuaian isian dan skenarionya bersama anggota A/B sebelum mengambil screenshot final.
3. Lengkapi perbandingan versi, pemulihan, pengelolaan akun oleh Manager Area, laporan, notifikasi rilis, dan migrasi.
4. Ambil screenshot menggunakan akun yang sesuai, termasuk keadaan perbaikan, penolakan, dan versi arsip. Hindari akun admin untuk membuktikan pembatasan akses staf.
5. Masukkan setiap screenshot ke I.7.1 dengan Nama Layar, Deskripsi, Pengguna, dan Tampilan Layar. Gunakan pemetaan di atas sebagai dasar I.7.2.

Laporan Word asli belum diubah. Tahap pertama ini mendukung demonstrasi alur utama dan bukan penyelesaian seluruh tugas orang C atau seluruh Milestone 4.

## Pembaruan tahap kedua — 10 November 2026

UC-01/02 sudah tersedia dalam menu Pengajuan Menu dan Pengajuan Bahan. Snapshot data sebelum/sesudah, pemeriksaan ulang saat data berubah, serta validasi bahan aktif sudah diuji. Contoh Es Teh Lemon berada pada Menunggu Pemeriksaan setelah dikirim melalui browser; Sirup Vanila masih Draf. Lihat `COBA-MENU-DAN-BAHAN.md`.
