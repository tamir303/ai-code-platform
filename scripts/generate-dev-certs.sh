#!/bin/bash
# =============================================================================
# Generate self-signed SSL certificate for dev environment
# =============================================================================
set -euo pipefail

CERT_DIR="./nginx/certs"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/selfsigned.crt" ] && [ -f "$CERT_DIR/selfsigned.key" ]; then
    echo "[!] Certificates already exist in $CERT_DIR — skipping."
    echo "    Delete them first if you want to regenerate."
    exit 0
fi

echo "[*] Generating self-signed SSL certificate..."

openssl req -x509 -nodes \
    -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/selfsigned.key" \
    -out "$CERT_DIR/selfsigned.crt" \
    -subj "/C=IL/ST=Dev/L=Local/O=AI-Code-Platform/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "[✓] Certificate generated:"
echo "    Cert: $CERT_DIR/selfsigned.crt"
echo "    Key:  $CERT_DIR/selfsigned.key"
echo ""
echo "    Valid for 365 days."
echo "    Add to your browser's trusted certs to avoid warnings."
