# 🐳 CTFd + CTFd-Whale (Out-of-the-Box Edition)

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-Ready-blue?logo=docker)](https://docs.docker.com/compose/)
[![CTFd Version](https://img.shields.io/badge/CTFd-v3.7+-red.svg?logo=ctfd)](https://github.com/CTFd/CTFd)
[![CTFd-Whale](https://img.shields.io/badge/Plugin-CTFd--Whale-0db7ed.svg?logo=docker)](https://github.com/frankli0324/ctfd-whale)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

> **Solusi All-in-One CTFd + CTFd-Whale siap pakai!**
> 
> Dibuat khusus bagi Anda yang **mager setup manual dari nol**. Setup CTFd bersama CTFd-Whale dari awal biasanya memakan waktu berjam-jam karena sering tersangkut masalah konfigurasi: race condition Docker Swarm overlay network, error perizinan Docker socket, dependensi Python 3.11 yang bentrok, hingga sinkronisasi Fast Reverse Proxy (FRP).
> 
> Repositori ini menggabungkan dan menyelaraskan seluruh komponen tersebut sehingga Anda cukup menjalankan **`docker compose up -d`** dan semuanya langsung berjalan normal!

---

## 📌 Daftar Isi
- [Keunggulan Repositori Ini](#-keunggulan-repositori-ini)
- [Arsitektur & Komponen](#-arsitektur--komponen)
- [Prasyarat Sistem](#-prasyarat-sistem)
- [Cara Menjalankan (Quick Start)](#-cara-menjalankan-quick-start)
- [Akses Layanan](#-akses-layanan)
- [Panduan Membuat Soal Dynamic Docker](#-panduan-membuat-soal-dynamic-docker)
  - [1. Soal Web (HTTP Subdomain)](#1-soal-web-http-subdomain)
  - [2. Soal Binary / Pwn (Direct TCP / Netcat)](#2-soal-binary--pwn-direct-tcp--netcat)
- [Cara Reset Total (Fresh Install)](#-cara-reset-total-fresh-install)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Credits](#-credits)

---

## 🚀 Keunggulan Repositori Ini

* ✅ **Zero-Config FRP:** FRP Server (`frps`) dan FRP Client (`frpc`) sudah saling terhubung dan tersambung otomatis ke API CTFd-Whale.
* ✅ **Python 3.11 Compatible:** Library `docker`, `Flask-APScheduler`, dan `flask-redis` pada plugin sudah di-patch agar tidak bentrok dengan `redis-py` milik core CTFd.
* ✅ **Docker Swarm Overlay Ready:** Konfigurasi network `ctfd_containers` sudah diproteksi agar tidak memicu race condition *"network not found"* pada Docker Engine terbaru.
* ✅ **Root Docker Socket Access:** Service CTFd sudah dikonfigurasi untuk dapat membaca `/var/run/docker.sock` host tanpa masalah permission.
* ✅ **One-Click Clean Slate:** Disediakan script `./reset.sh` untuk menghapus bersih seluruh database dan cache saat ingin mengadakan kompetisi baru dari nol.

---

## 🏗 Arsitektur & Komponen

```
                  [ Player Browser / Terminal ]
                                |
        +-----------------------+-----------------------+
        | Port 80 / 8000                                | Port 8080 (HTTP)
        v                                               | Port 10000-10100 (TCP)
   [ Nginx / CTFd ]                                     v
        |                                            [ frps ]
        | (Manages DB & Containers via Docker Sock)     |
        v                                               | (Tunneling)
  [ CTFd-Whale ] <--- API (Port 7400) ---> [ frpc ] <---+
        |                                     |
        | (Spawns Services via Swarm)         | (Routes Traffic)
        v                                     v
  +-----------------------------------------------------+
  |               ctfd_containers Network               |
  |  [ Chall Container #1 ]    [ Chall Container #2 ]  |
  +-----------------------------------------------------+
```

Stack ini terdiri dari 6 service container:
1. **`ctfd`**: Web application CTFd utama (Flask, Gunicorn).
2. **`ctfd-whale`**: Plugin dynamic challenge container di dalam CTFd.
3. **`db`**: MariaDB 10.11 sebagai database penyimpanan soal, user, dan flag.
4. **`cache`**: Redis 4 untuk caching sesi dan lock container.
5. **`nginx`**: Web server reverse-proxy untuk port HTTP 80.
6. **`frps` & `frpc`**: Fast Reverse Proxy untuk memetakan port/subdomain soal dynamic ke pemain secara terisolasi.

---

## ⚙️ Prasyarat Sistem

1. **Docker Engine & Docker Compose v2** terpasang di host Linux Anda.
2. **Inisialisasi Docker Swarm** (CTFd-Whale menggunakan API Swarm untuk scheduling container):
   ```bash
   docker swarm init
   ```
3. **Beri label node manager** (Whale membutuhkan label `name=linux-1` untuk penempatan container):
   ```bash
   docker node update --label-add "name=linux-1" $(docker node ls -q)
   ```

---

## 🏁 Cara Menjalankan (Quick Start)

1. **Clone repositori ini:**
   ```bash
   git clone https://github.com/Rizzkiy/CTF-Platform.git
   cd CTF-Platform
   ```

2. **Jalankan container:**
   ```bash
   docker compose up -d
   ```
   *(Jika pertama kali atau ingin re-build image CTFd, gunakan: `docker compose up -d --build`)*

3. **Cek status container:**
   ```bash
   docker compose ps
   ```
   Semua container (`ctfd`, `nginx`, `db`, `cache`, `frps`, `frpc`) harus berstatus **Up**.

---

## 🌐 Akses Layanan

| Layanan | Alamat / URL | Keterangan |
| :--- | :--- | :--- |
| **CTFd Web UI (Nginx)** | `http://localhost` (Port 80) | Akses utama untuk peserta & admin |
| **CTFd Direct Port** | `http://localhost:8000` | Akses langsung ke service Flask/Gunicorn |
| **Dynamic Challenge HTTP** | `http://<uuid>.127.0.0.1.nip.io:8080` | URL soal web otomatis via FRP |
| **Dynamic Challenge TCP** | `nc 127.0.0.1 <port>` | Rentang port `10000` - `10100` untuk soal Pwn/Binary |

### Verifikasi Awal
1. Buka browser ke **`http://localhost`** dan selesaikan setup akun admin pertama Anda.
2. Masuk ke **Admin Panel** $\rightarrow$ **Plugins** $\rightarrow$ **Whale**.
3. Pastikan semua indikator self-check (Docker connection, Swarm node, Frp API) menampilkan status **Available** tanpa tanda error.

---

## 🎯 Panduan Membuat Soal Dynamic Docker

Masuk ke **Admin Panel** $\rightarrow$ **Challenges** $\rightarrow$ klik tombol **`+`** (New Challenge), lalu pilih tipe **`dynamic_docker`**.

### 1. Soal Web (HTTP Subdomain)
* **Name**: Nama Challenge (misal: *Simple Web Exploitation*)
* **Category**: `web`
* **Docker Image**: Image Docker publik atau lokal (misal: `ctftraining/qwb_2019_smarthome`)
* **Redirect Type**: Pilih **`HTTP`**
* **Redirect Port**: Port web server di dalam container (biasanya **`80`**)
* **Initial / Minimum / Decay**: Konfigurasi dynamic score CTFd
* **Memory Limit**: `128m` (sesuaikan kebutuhan)
* **CPU Limit**: `0.5`

> **Akses Peserta:** Ketika peserta menekan tombol **Start Container**, Whale akan memberikan tautan otomatis dengan subdomain acak, misalnya:  
> `http://a1b2c3d4-e5f6-7890.127.0.0.1.nip.io:8080`

---

### 2. Soal Binary / Pwn (Direct TCP / Netcat)
* **Name**: Nama Challenge (misal: *Ret2Libc Warmup*)
* **Category**: `pwn`
* **Docker Image**: Image Docker soal Anda
* **Redirect Type**: Pilih **`Direct`**
* **Redirect Port**: Port internal service binary (misal: `9999` atau `1337`)

> **Akses Peserta:** Ketika peserta menekan tombol **Start Container**, Whale akan menampilkan perintah Netcat:  
> `nc 127.0.0.1 10005` (port acak pada rentang 10000–10100)

---

## 🧹 Cara Reset Total (Fresh Install)

Jika kompetisi sudah selesai atau Anda ingin membersihkan seluruh data (akun admin, user, submissions, cache) kembali ke halaman `/setup` awal:

Cukup jalankan script pembersih yang sudah disediakan:
```bash
./reset.sh
```

Script ini akan:
1. Mematikan seluruh container & volume compose (`docker compose down -v`).
2. Menghapus folder bind-mount database & cache (`sudo rm -rf .data`).
3. Menghapus file secret key (`.ctfd_secret_key`).
4. Membersihkan sisa container soal Swarm yang masih berjalan.

Setelah reset, cukup jalankan kembali `docker compose up -d`.

---

## ❓ Troubleshooting & FAQ

#### 1. Frpc error: *"login to server failed / connection refused"*
* Pastikan container `ctfd-frps-1` sudah menyala dan port `7000` di network internal tidak diblokir.
* Di setup ini, `frpc` memiliki `depends_on: [frps]` sehingga otomatis menunggu server menyala terlebih dahulu.

#### 2. Error: *"This node is not a swarm manager"*
* Swarm belum diinisialisasi pada Docker host. Jalankan:
  ```bash
  docker swarm init
  ```

#### 3. Error: *"No Suitable Nodes"* saat peserta start container
* Node Docker belum diberi label yang sesuai. Jalankan:
  ```bash
  docker node update --label-add "name=linux-1" $(docker node ls -q)
  ```

#### 4. Mengganti Domain Publik (VPS / Server Online)
Jika ingin mendeploy di VPS atau server ber-domain publik (bukan localhost):
* Edit file `docker-compose.yml` pada bagian service `frps`:
  Ganti `--subdomain_host=127.0.0.1.nip.io` dengan domain Anda (misal: `--subdomain_host=ctf.domainanda.com`).
* Buka pengaturan **Admin Panel** $\rightarrow$ **Plugins** $\rightarrow$ **Whale** $\rightarrow$ **Router**, lalu sesuaikan `Frp HTTP Domain Suffix` dan `Frp Direct IP Address` dengan domain/IP publik VPS Anda.

---

## 📄 Credits

* [CTFd](https://github.com/CTFd/CTFd) - Capture The Flag framework by Kevin Chung and the CTFd community.
* [ctfd-whale](https://github.com/frankli0324/ctfd-whale) - Dynamic docker challenge plugin by Frank Li (`frankli0324`).
* [fatedier/frp](https://github.com/fatedier/frp) - Fast Reverse Proxy.
