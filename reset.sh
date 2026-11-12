#!/bin/bash
set -e

echo "==> Menghentikan container CTFd..."
docker compose down -v

echo "==> Menghapus data persisten (.data & .ctfd_secret_key)..."
sudo rm -rf .data
rm -f .ctfd_secret_key

echo "==> Membersihkan sisa container challenge jika ada..."
docker service rm $(docker service ls -q --filter "label=whale_id") 2>/dev/null || true

echo ""
echo "[✓] Selesai! Data CTFd sudah bersih total."
echo "Silakan jalankan 'docker compose up -d' untuk memulai instalasi baru."
