$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
& .venv\Scripts\python.exe -m pip install -r requirements.lock
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
& .venv\Scripts\python.exe -m pip install --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw "package installation failed" }
& .venv\Scripts\python.exe -m portal_tsinder init
if ($LASTEXITCODE -ne 0) { throw "initialization failed" }
& .venv\Scripts\python.exe -m portal_tsinder serve
