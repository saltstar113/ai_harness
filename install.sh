#!/bin/bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo ""
echo "Installation complete."
echo "Run 'python run_cli.py credential set' to configure your API key."
echo "Run 'python run_cli.py --help' for usage."