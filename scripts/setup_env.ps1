# PowerShell setup script to create a virtualenv and install pinned dependencies
param(
    [string]$venvPath = ".venv"
)

python -m venv $venvPath
Write-Host "Created venv at $venvPath"

Write-Host "Activating venv..."
# For interactive use: .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
& $venvPath\Scripts\python.exe -m pip install -U pip setuptools wheel

Write-Host "Installing pinned scientific stack for pymc3 compatibility..."
& $venvPath\Scripts\python.exe -m pip install numpy==1.21.6 scipy==1.7.3 protobuf==3.20.3

Write-Host "Installing project requirements..."
& $venvPath\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Setup complete. To activate the virtualenv run:`n.\$venvPath\Scripts\Activate.ps1` in PowerShell"
