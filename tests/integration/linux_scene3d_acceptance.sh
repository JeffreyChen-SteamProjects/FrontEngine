#!/bin/sh
# Run in a disposable Debian/Python container with the repository mounted read-only.
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y xvfb libgl1-mesa-dri libegl1 libopengl0 libxkbcommon-x11-0 libxcb-cursor0 \
    libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0 libpulse0 libasound2 \
    libnss3 libxss1 libgbm1 libxrandr2 libxtst6 libxdamage1 fonts-dejavu-core \
    build-essential linux-libc-dev libglib2.0-0 libfontconfig1 libdbus-1-3 \
    libfreetype6 libx11-xcb1 libgssapi-krb5-2 libxcomposite1 libxfixes3
python -m pip install --find-links /workspace/build/linux-wheels -r /workspace/requirements.txt \
    "PySide6==${FRONTENGINE_TEST_QT:-6.11.2}" pytest pyflakes
export PYTHONPATH=/workspace PYTHONDONTWRITEBYTECODE=1 QTWEBENGINE_DISABLE_SANDBOX=1
export LIBGL_ALWAYS_SOFTWARE=1 DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 >/tmp/scene3d-xvfb.log 2>&1 &
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
xvfb_pid=$!
cd /tmp
python -c 'from PySide6 import QtWidgets, QtOpenGLWidgets, QtMultimedia, QtWebEngineWidgets'
python -m pytest /workspace/tests -q -p no:cacheprovider --basetemp=/tmp/scene3d-pytest
report_base=$(mktemp -d /tmp/frontengine-scene3d-evidence-XXXXXX)
python -m tests.integration.scene3d_gl_smoke --report "$report_base/native"
echo "Native acceptance report: $report_base/native/result.json"
