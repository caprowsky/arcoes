#!/bin/bash
# Script per installare pip, le dipendenze e avviare lo script di download
set -e

# Installa pip se non presente
if ! command -v pip3 &> /dev/null; then
    echo "pip3 non trovato. Installazione..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Installa le dipendenze
pip3 install -r requirements.txt

# Avvia lo script di download
python3 download_arcoes.py
