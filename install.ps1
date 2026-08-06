python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host ""
Write-Host "Installation complete."
Write-Host "Run 'python run_cli.py credential set' to configure your API key."
Write-Host "Run 'python run_cli.py --help' for usage."