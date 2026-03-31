#!/bin/bash
# ─────────────────────────────────────────
#  ServerWatch macOS 빌드 스크립트
#  실행: chmod +x build_mac.sh && ./build_mac.sh
# ─────────────────────────────────────────

# 이 스크립트가 있는 폴더로 이동 (어디서 실행해도 동작)
cd "$(dirname "$0")"

echo "📦 의존성 설치 중..."
pip3 install PyQt5 paramiko pyinstaller

echo ""
echo "🔨 빌드 중..."
python3 -m PyInstaller \
  --onefile \
  --windowed \
  --name "ServerWatch" \
  --hidden-import paramiko \
  --hidden-import PyQt5 \
  --hidden-import PyQt5.QtWidgets \
  --hidden-import PyQt5.QtCore \
  --hidden-import PyQt5.QtGui \
  --hidden-import cryptography \
  server_monitor.py

echo ""
echo "✅ 완료! 아래 경로에 생성되었습니다:"
echo "$(pwd)/dist/ServerWatch"
open "$(pwd)/dist/"
