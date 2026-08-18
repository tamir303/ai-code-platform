#!/bin/bash
# =============================================================================
# GPU Validation Script — Run inside a container or on the host
# Checks NVIDIA driver, toolkit, and Docker GPU passthrough.
#
# Usage:
#   chmod +x scripts/validate-gpu.sh
#   ./scripts/validate-gpu.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}[FAIL]${NC} $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "============================================="
echo " GPU Environment Validation"
echo "============================================="

# Host-level checks
check "NVIDIA driver loaded (nvidia-smi)" command -v nvidia-smi
check "Docker installed" command -v docker
check "NVIDIA Container Toolkit (nvidia-ctk)" command -v nvidia-ctk

# Driver details
if command -v nvidia-smi &> /dev/null; then
    echo ""
    echo "--- GPU Info ---"
    nvidia-smi --query-gpu=index,name,driver_version,memory.total,temperature.gpu \
        --format=csv,noheader 2>/dev/null | while IFS=',' read -r idx name driver mem temp; do
        echo -e "  GPU $idx:$name | Driver:$driver | VRAM:$mem | Temp:$temp°C"
    done
    echo ""

    # CUDA version from driver
    CUDA_VER=$(nvidia-smi | grep -oP 'CUDA Version: \K[0-9.]+' 2>/dev/null || echo "unknown")
    echo -e "  CUDA Version (driver): ${GREEN}$CUDA_VER${NC}"
fi

# Docker runtime check
if command -v docker &> /dev/null; then
    echo ""
    echo "--- Docker Runtime ---"
    if docker info 2>/dev/null | grep -q nvidia; then
        echo -e "  ${GREEN}[PASS]${NC} NVIDIA runtime registered in Docker"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[FAIL]${NC} NVIDIA runtime NOT found in Docker (run setup-nvidia-toolkit.sh)"
        FAIL=$((FAIL + 1))
    fi

    DEFAULT_RT=$(docker info 2>/dev/null | grep -oP 'Default Runtime: \K\S+' || echo "unknown")
    echo "  Default Runtime: $DEFAULT_RT"
fi

# Container GPU passthrough test
if command -v docker &> /dev/null; then
    echo ""
    echo "--- Container GPU Passthrough ---"
    if docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi > /dev/null 2>&1; then
        echo -e "  ${GREEN}[PASS]${NC} GPU accessible from Docker containers"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[FAIL]${NC} Cannot access GPU from Docker containers"
        FAIL=$((FAIL + 1))
    fi
fi

# Summary
echo ""
echo "============================================="
echo -e "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "============================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
