# Mencoba fitur versi 17.0.1.3.0

Versi ini menyelaraskan sistem dengan ERD, use case, dan skenario uji Milestone 4 yang sudah ditulis tim, sehingga laporan tidak perlu diubah. Semua data contoh fiktif.

| Kebutuhan di laporan | Yang ditambahkan di sistem | Layar |
|---|---|---|
| Menu punya Jenis Menu, Kategori, Status Ketersediaan (ERD D-02, UC-01, FR-01) | Field **Kategori** (Kopi, Non-Kopi, Light Meals, Main Course, Rice Bowl, Pasta, Dessert) dan **Status Ketersediaan** (Tersedia, Musiman / Terbatas, Tidak Tersedia). Label Divisi menjadi **Jenis Menu**. Kategori, alergen, dan ketersediaan wajib diisi saat pengajuan menu. | L02, L03, L04 |
| Nama menu/bahan sudah terdaftar ditolak (FR-01, FR-02) | Pemeriksaan nama unik saat pengajuan dikirim | L04, L06 |
| Satuan baku gram, kilogram, mililiter, liter, buah (FR-02) | Satuan **kg** dan **liter** | L05, L06 |
| Penolakan penonaktifan bahan menampilkan resep yang memakainya (FR-03) | Pesan kesalahan menyebut nama menu/resepnya | L06 |
| Jumlah porsi, satuan takaran satu kategori (ERD D-05, D-06, FR-04) | Field **Jumlah Porsi** dan **Satuan Takaran** per baris (boleh g/kg atau ml/l asalkan sekategori dengan satuan baku). Perbandingan gramasi dihitung dalam satuan baku. | L08, L10, L19 |
| Ketelitian QR-6 | Bar 0,1 g/ml, Kitchen bilangan bulat g/ml (0,2 kg = 200 g diterima) | L08 |
| Usulan tanggal rilis dari pengaju (ERD D-04, FR-05) | Field **Usulan Tanggal Rilis** pada pengajuan resep dan menu/bahan. Tanggal rilis final tetap diisi Manager Area. | L04, L06, L08 |
| Pengajuan ganda ditolak (FR-05) | Menu yang masih punya pengajuan resep terkirim (Menunggu Pemeriksaan sampai Menunggu Rilis) tidak bisa diajukan lagi. Draf lain ditolak saat dikirim. | L03, L08 |
| Laporan: filter kategori, status, nomor versi, rentang tanggal; format PDF atau Excel/CSV (FR-12) | Filter **Kategori Menu** dan **Nomor Versi**, format **CSV**, kolom kategori, ketersediaan, dan jumlah porsi | L20 |
| Nama tombol di skenario uji | **Sesuai, Teruskan** dan **Nonaktifkan** (akun) | L09, L18 |

Templat migrasi Excel juga bertambah kolom opsional: Menu (**Kategori**, **Status Ketersediaan**, **Jumlah Porsi**) dan Resep (**Satuan**). Contoh terbaru ada di `docs/contoh-migrasi-kopitera.xlsx`.

## Upgrade dari versi 17.0.1.2.0

```powershell
cd "D:\ITB\sem 5\SISFOR\IF3141-odoo-K02-G03"
docker compose stop web
docker compose run --rm web odoo -d odoo_app -u kopitera_master --stop-after-init --without-demo=all
docker compose up -d
```

Saat upgrade, skrip migrasi otomatis mengisi **Kategori** menu lama dari jenis menunya (minuman berisi kata "kopi" menjadi Kopi, minuman lain Non-Kopi, makanan menjadi Main Course), mengisi **Status Ketersediaan** = Tersedia dan **Jumlah Porsi** = 1, serta mengisi **Satuan Takaran** setiap baris resep dengan satuan baku bahannya. Kategori yang kurang tepat dapat diubah lewat pengajuan menu.

Catatan: pengajuan menu yang sudah dikirim sebelum upgrade dan belum punya kategori perlu dikembalikan ke pengaju (Minta Perbaikan atau Minta Pembaruan) agar kategorinya diisi.

## Pengujian

```powershell
docker compose stop web
Get-Content -Raw scripts/check_kopitera_v130.py | docker compose run --rm -T web odoo shell -d odoo_app --no-http --dev=xml --log-level=warn
docker compose up -d
```

Hasil yang diharapkan: `KOPITERA_V130_CHECKS_PASSED=18`. Skrip lama (`check_kopitera.py`, `check_kopitera_master.py`, `check_kopitera_v120.py`) tetap lulus. Semua perubahan pengujian dibatalkan (rollback).
