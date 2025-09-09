<#
.SYNOPSIS
    Sets up a Python virtual environment and installs dependencies for the BLS appointment automation script.
#>

# Create a virtual environment
Write-Host "Creating virtual environment..."
python -m venv venv

# Activate the virtual environment
Write-Host "Activating virtual environment..."
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing dependencies..."
pip install -r requirements.txt

# Install Tesseract OCR (required for pytesseract)
Write-Host "Installing Tesseract OCR..."
# Download and install Tesseract OCR for Windows
$tesseractUrl = "https://github.com/UB-Mannheim/tesseract/wiki"
Write-Host "Please download and install Tesseract OCR from $tesseractUrl"
Write-Host "After installation, add Tesseract to your system PATH."
Write-Host "Example PATH entry: C:\Program Files\Tesseract-OCR"

# Deactivate the virtual environment
Write-Host "Deactivating virtual environment..."
deactivate

Write-Host "`nVirtual environment setup complete!"
Write-Host "To activate, run: .\venv\Scripts\Activate.ps1"
