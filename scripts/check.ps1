# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each step stops the script on failure: native commands do not honour
# $ErrorActionPreference, so the exit code is checked after every one.
$ErrorActionPreference = "Stop"

ruff format --check .
if ($LASTEXITCODE) { exit $LASTEXITCODE }
ruff check .
if ($LASTEXITCODE) { exit $LASTEXITCODE }
mypy --strict src
if ($LASTEXITCODE) { exit $LASTEXITCODE }
pytest
exit $LASTEXITCODE
