#!/bin/bash
# =============================================================================
# NVIDIA Container Toolkit — Host Setup Script
# Target: Ubuntu 20.04 / 22.04 / 24.04 (Debian-based)
#
# Prerequisites:
#   - NVIDIA GPU drivers already installed (nvidia-smi should work)
#   - Docker Engine installed (docker --version should work)
#   - Root / sudo access
#
# Usage:
#   chmod +x scripts/setup-nvidia-toolkit.sh
#   sudo ./scripts/setup-nvidia-toolkit.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
echo "============================================="
echo " NVIDIA Container Toolkit — Setup"
echo "============================================="

if [ "$EUID" -ne 0 ]; then
    fail "Please run as root: sudo $0"
fi

if ! command -v docker &> /dev/null; then
    fail "Docker is not installed. Install Docker Engine first."
fi

if ! command -v nvidia-smi &> /dev/null; then
    fail "NVIDIA drivers not found. Install GPU drivers first (nvidia-smi must work)."
fi

log "Docker version: $(docker --version)"
log "NVIDIA driver detected:"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | while read -r line; do
    log "  GPU: $line"
done

# ---------------------------------------------------------------------------
# 2. Install NVIDIA Container Toolkit
# ---------------------------------------------------------------------------
if command -v nvidia-ctk &> /dev/null; then
    warn "NVIDIA Container Toolkit is already installed ($(nvidia-ctk --version 2>/dev/null || echo 'unknown version'))"
    warn "Proceeding to configure runtime..."
else
    log "Adding NVIDIA Container Toolkit repository..."

    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
        | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

    apt-get update -qq
    apt-get install -y nvidia-container-toolkit

    log "NVIDIA Container Toolkit installed successfully."
fi

# ---------------------------------------------------------------------------
# 3. Configure Docker runtime
# ---------------------------------------------------------------------------
log "Configuring Docker to use nvidia runtime..."
nvidia-ctk runtime configure --runtime=docker

# Set nvidia as the default runtime (optional but recommended for this project)
if [ -f /etc/docker/daemon.json ]; then
    # Check if default-runtime is already set
    if ! grep -q '"default-runtime"' /etc/docker/daemon.json; then
        log "Setting nvidia as the default Docker runtime..."
        python3 -c "
import json
with open('/etc/docker/daemon.json', 'r') as f:
    cfg = json.load(f)
cfg['default-runtime'] = 'nvidia'
with open('/etc/docker/daemon.json', 'w') as f:
    json.dump(cfg, f, indent=2)
"
    else
        warn "default-runtime already configured in /etc/docker/daemon.json"
    fi
fi

# ---------------------------------------------------------------------------
# 4. Restart Docker daemon
# ---------------------------------------------------------------------------
log "Restarting Docker daemon..."
systemctl restart docker
sleep 2

# ---------------------------------------------------------------------------
# 5. Validate the installation
# ---------------------------------------------------------------------------
log "Validating GPU access from Docker..."

if docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi > /dev/null 2>&1; then
    log "GPU access from Docker containers is working!"
    echo ""
    docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
else
    fail "GPU access test failed. Check docker logs and driver compatibility."
fi

echo ""
echo "============================================="
log "Setup complete! Your system is ready."
echo ""
echo "  Next steps:"
echo "    1. cd ai-code-platform"
echo "    2. docker compose -f docker-compose.dev.yaml --env-file .env.dev up -d"
echo ""
echo "============================================="
