#!/bin/bash
set -e

echo "==> Menghentikan container CTFd..."
docker compose down -v

echo "==> Menghapus data persisten (.data & .ctfd_secret_key)..."
rm -rf .data
rm -f .ctfd_secret_key

echo "==> Membersihkan sisa container challenge jika ada..."
docker rm -f $(docker ps -aq --filter "name=ctfd_c") 2>/dev/null || true

echo ""
echo "[✓] Selesai! Data CTFd sudah bersih total."
echo "Silakan jalankan 'docker compose up -d --build' untuk memulai instalasi baru."
