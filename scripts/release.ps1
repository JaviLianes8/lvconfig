# Build and upload to PyPI. Run scripts/check.ps1 first.
# The token is read from a secret store, never git.
$ErrorActionPreference = "Stop"

# Build only from a clean, committed tree, so nothing untracked reaches the artifacts.
$dirty = git status --porcelain --untracked-files=all
if ($dirty) { throw "The working tree is not clean; commit or remove these first:`n$dirty" }

$token = $env:PYPI_TOKEN
if (-not $token -and (Test-Path "C:\secrets\pypi-token.txt")) {
    $token = (Get-Content "C:\secrets\pypi-token.txt" -Raw).Trim()
}
if (-not $token) {
    throw "No PyPI token. Set `$env:PYPI_TOKEN or save it to C:\secrets\pypi-token.txt (never commit it)."
}

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
python -m twine check --strict dist/*

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $token
try { python -m twine upload dist/* } finally { Remove-Item Env:\TWINE_PASSWORD -ErrorAction SilentlyContinue }
