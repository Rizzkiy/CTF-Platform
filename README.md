# 🚀 CTFd + CTFd-Compose (Dynamic Docker Compose Platform)

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-Ready-blue?logo=docker)](https://docs.docker.com/compose/)
[![CTFd Version](https://img.shields.io/badge/CTFd-v3.7+-red.svg?logo=ctfd)](https://github.com/CTFd/CTFd)
[![Plugin](https://img.shields.io/badge/Plugin-CTFd--Compose-0db7ed.svg?logo=docker)](CTFd/plugins/ctfd_compose)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

> **Solusi All-in-One CTF Platform dengan Dynamic Docker Container berbasis `docker-compose.yml`!**
> 
> Capek dan pusing setup **CTFd-Whale** yang ribet karena harus Docker Swarm, routing FRP client-server, overlay network yang sering hilang, dan konfigurasi template rumit?
> 
> Proyek ini menghadirkan **`ctfd_compose`** — plugin modern dan sederhana untuk men-deploy dynamic container per-pemain langsung dari folder berisi file **`docker-compose.yml`**! Anda tinggal meletakkan folder soal di `challenges/<nama_soal>/` dan CTFd akan otomatis mengatur deployment via `docker compose`.
> 
> Cocok untuk Anda yang **mager setup dari nol**: tinggal jalankan **`docker compose up -d --build`** dan platform langsung siap digunakan!

---

## 📌 Daftar Isi
- [Kenapa Beralih dari CTFd-Whale ke CTFd-Compose?](#-kenapa-beralih-dari-ctfd-whale-ke-ctfd-compose)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Cara Menjalankan (Quick Start)](#-cara-menjalankan-quick-start)
- [Panduan Membuat Soal Baru](#-panduan-membuat-soal-baru)
  - [1. Struktur Folder Soal](#1-struktur-folder-soal)
  - [2. Contoh Soal Web (HTTP)](#2-contoh-soal-web-http)
  - [3. Contoh Soal Pwn / Netcat (TCP)](#3-contoh-soal-pwn--netcat-tcp)
  - [4. Mendaftarkan Soal di Admin CTFd](#4-mendaftarkan-soal-di-admin-ctfd)
- [Fitur Admin Dashboard](#-fitur-admin-dashboard)
- [Cara Reset Total (Fresh Install)](#-cara-reset-total-fresh-install)
- [Lisensi](#-lisensi)

---

## 💡 Kenapa Beralih dari CTFd-Whale ke CTFd-Compose?

| Fitur | CTFd-Whale 🐳 | CTFd-Compose 🚀 (Repositori Ini) |
|---|---|---|
| **Format Soal** | Harus Dockerfile terpisah & image registry | Cukup folder dengan **`docker-compose.yml`** |
| **Docker Swarm** | **Wajib** (Sering error overlay network & label) | **Tidak butuh Swarm** (Docker standalone biasa) |
| **FRP / Proxy** | Wajib setup FRPS & FRPC + token rahasia | **Direct Port Mapping** (Lebih cepat & stabil) |
| **Rebuild Soal** | Sulit, harus push ke registry lagi | **1 Klik Rebuild** (`docker compose up -d --build`) |
| **Restart Container** | Manual via docker service cli | **1 Klik Restart** langsung dari Admin Panel |
| **Auto Cleanup** | Mengandalkan scheduler complex | **Background Worker** otomatis hapus container expired |

---

## ✨ Fitur Utama

* 🎮 **Kontrol Pemain Lengkap:**
  * **Launch Instance:** Menjalankan instance baru via `docker compose up -d`.
  * **Timer & Countdown:** Menampilkan waktu hitung mundur durasi kontainer secara realtime.
  * **Renew Time:** Menambah durasi waktu aktif container (misal +10 menit) dengan batas maksimal yang dapat diatur admin.
  * **Destroy Instance:** Menghentikan dan menghapus container + volume (`docker compose down -v`).
* 🚩 **Dynamic Flag Otomatis:**
  * Flag unik dihasilkan secara dinamis untuk setiap kontainer yang dibuat.
  * Flag di-inject ke dalam kontainer melalui environment variable `${FLAG}`.
  * CTFd memverifikasi flag secara otomatis saat pemain melakukan submit.
* 🔌 **Port Host Otomatis:**
  * Port host (rentang 30000–40000) dialokasikan otomatis dan di-inject via variable `${PORT}`.
* 🛠 **Admin Management Dashboard:**
  * Halaman `/admin/compose` di admin panel untuk memonitor semua container yang sedang aktif.
  * Tombol **Restart**, **Rebuild & Start**, dan **Force Destroy**.
  * Otomatis mendeteksi folder-folder soal yang tersedia di direktori `challenges/`.
* 🧹 **Auto-Expiry Cleanup:**
  * Background worker yang otomatis memeriksa kontainer kadaluarsa dan membersihkannya tanpa membebani server.

---

## 🏗 Arsitektur Sistem

```
                     [ Pemain (Browser / Netcat) ]
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v (Port 80 / 8000)                                  v (Port 30000 - 40000)
    [ Nginx / CTFd ]                                   [ Host Docker Engine ]
         |                                                   |
         | (Mount /var/run/docker.sock)                      | (Isolated Containers)
         v                                                   v
   [ Plugin ctfd_compose ] ---- docker compose ----> [ Chall Instance User A ]
   (DB: MariaDB & Cache: Redis)                      [ Chall Instance User B ]
```

---

## 🏁 Cara Menjalankan (Quick Start)

1. **Pastikan Docker dan Docker Compose sudah terpasang di host Linux Anda.**
   Tidak perlu menginisialisasi Docker Swarm!

2. **Clone repositori ini:**
   ```bash
   git clone https://github.com/Rizzkiy/CTF-Platform.git
   cd CTF-Platform
   ```

3. **Jalankan platform:**
   ```bash
   docker compose up -d --build
   ```

4. **Buka browser:**
   * Akses CTFd di: **`http://localhost`** (atau `http://IP-SERVER-ANDA`)
   * Ikuti wizard setup awal (masukkan nama event, buat akun admin).

---

## 📦 Panduan Membuat Soal Baru

### 1. Struktur Folder Soal
Semua soal diletakkan di dalam folder `challenges/<nama_soal>/`.

Contoh struktur direktori:
```
challenges/
├── web_sample/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── index.php
└── pwn_sample/
    ├── docker-compose.yml
    ├── Dockerfile
    └── server.py
```

### 2. Contoh Soal Web (HTTP)
Buat file `challenges/web_sample/docker-compose.yml`:
```yaml
services:
  web:
    build: .
    ports:
      - "${PORT}:80"
    environment:
      - FLAG=${FLAG}
```
* **`${PORT}`**: Port host dinamis yang disediakan oleh CTFd.
* **`${FLAG}`**: Flag dinamis yang di-generate CTFd untuk pemain tersebut.

### 3. Contoh Soal Pwn / Netcat (TCP)
Buat file `challenges/pwn_sample/docker-compose.yml`:
```yaml
services:
  chall:
    build: .
    ports:
      - "${PORT}:1337"
    environment:
      - FLAG=${FLAG}
```

### 4. Mendaftarkan Soal di Admin CTFd
1. Masuk ke **Admin Panel** CTFd.
2. Klik **Challenges** -> **+ Create Challenge**.
3. Pilih tipe challenge: **`compose`**.
4. Isi form:
   * **Name**: Nama Soal (misal: *Easy Web Login*)
   * **Category**: Web / Pwn / Misc
   * **Compose Directory**: Pilih dari dropdown atau ketik nama folder di dalam `challenges/` (misal: `web_sample`).
   * **Service Port**: Port internal container (misal: `80` untuk web, `1337` untuk nc).
   * **Connection Protocol**: Pilih `HTTP` (link browser) atau `Direct / Netcat` (`nc host port`).
   * **Container Lifetime**: Durasi container aktif dalam detik (default `1200` = 20 menit).
   * **Max Extensions**: Batas perpanjangan waktu (default `3` kali).
   * **Dynamic Flag per Container**: Centang untuk mengaktifkan flag dinamis per-pemain.
   * **Dynamic Flag Template**: Pola flag, contoh: `CTF{compose_{token}}`.
5. Klik **Create** dan atur status menjadi **Visible**.
6. Selesai! Saat pemain membuka soal, akan muncul tombol **🚀 Launch Instance**.

---

## 🛡 Fitur Admin Dashboard

Di navbar Admin Panel, terdapat menu **`Compose Containers`** (`/admin/compose`):
* Menampilkan jumlah seluruh kontainer aktif secara realtime.
* Daftar folder soal yang terdeteksi di `challenges/`.
* Tabel kontainer aktif:
  * Pemain yang menjalankan
  * Soal terkait & folder compose
  * Port host yang digunakan
  * Flag yang di-generate
  * Sisa waktu aktif
  * Tombol aksi:
    * 🔄 **Restart**: Menjalankan `docker compose restart`.
    * 🔨 **Rebuild**: Menjalankan `docker compose up -d --build`.
    * 🗑 **Destroy**: Menghapus container seketika.

---

## 🧹 Cara Reset Total (Fresh Install)

Jika ingin membersihkan seluruh data (database kompetisi, sesi, dan sisa container) untuk memulai event baru:
```bash
./reset.sh
docker compose up -d --build
```

---

## 📄 Lisensi
CTFd dilisensikan di bawah lisensi Apache 2.0. Plugin `ctfd_compose` dibuat sebagai solusi dynamic challenge berbasis Docker Compose.
