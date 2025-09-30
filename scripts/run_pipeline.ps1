param(
    [string]$tz = ".\nlp_core\input\TZ_object.docx",
    [string]$ifc = "",
    [string]$bimOut = ".\bim_core\runs",
    [string]$mcpHost = "127.0.0.1",
    [int]$mcpPort = 9090,
    [switch]$AutoInstall
)

# -----------------------
# Repository root
# -----------------------
if ($PSScriptRoot) {
    $scriptPath = $PSScriptRoot
} else {
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = Split-Path -Parent $scriptPath

Write-Host "Repository root: $repoRoot"

# -----------------------
# Helper: Get python from venv
# -----------------------
function Get-VenvPython($componentPath) {
    $venvPath = Join-Path $repoRoot ".venv"
    if (Test-Path (Join-Path $venvPath "Scripts\python.exe")) {
        return (Join-Path $venvPath "Scripts\python.exe")
    }
    if ($componentPath -and (Test-Path (Join-Path $componentPath ".venv\Scripts\python.exe"))) {
        return (Join-Path $componentPath ".venv\Scripts\python.exe")
    }
    return "python"
}

# -----------------------
# Paths
# -----------------------
$nlpCli   = Join-Path $repoRoot "nlp_core\nlp_core\run_cli.py"
$bimCli   = Join-Path $repoRoot "bim_core\bim_core\run_cli.py"
$sendCli  = Join-Path $repoRoot "scripts\send_stubs_cli.py"
$nlpOut   = Join-Path $repoRoot "nlp_core\OUT\result.json"
$stubsFile = Join-Path $repoRoot "bim_core\runs\stubs.json"

Write-Host "Pipeline params:"
Write-Host " NLP TZ: $tz"
Write-Host " IFC: $ifc"
Write-Host " BIM out: $bimOut"
Write-Host " MCP: $mcpHost`:$mcpPort"
Write-Host " Auto-install enabled: $AutoInstall"
Write-Host ""

# -----------------------
# Step 1: NLP
# -----------------------
Write-Host "=== Step 1/4: NLP ==="
$nlpPython = Get-VenvPython (Join-Path $repoRoot "nlp_core")
Write-Host "Using python: $nlpPython"
$confirm = Read-Host "Confirm that venv and spaCy are already installed (y/N)"
if ($confirm -ne "y") {
    Write-Warning "NLP окружение не подтверждено. Прерывание."
    exit 10
}
& $nlpPython $nlpCli --tz $tz --out $nlpOut -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "NLP exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "NLP finished. Output: $nlpOut"

# -----------------------
# Step 2: BIM
# -----------------------
Write-Host ""
Write-Host "=== Step 2/4: BIM ==="
$bimPython = Get-VenvPython (Join-Path $repoRoot "bim_core")
$bimArgs = @("--tz", $nlpOut, "--out", $bimOut)
if ($ifc -ne "") { $bimArgs += @("--ifc", $ifc) }
& $bimPython $bimCli @bimArgs -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "BIM exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "BIM ok. stubs at $stubsFile"

# -----------------------
# Step 3: MCP check
# -----------------------
Write-Host ""
Write-Host "=== Step 3/4: Check MCP ${mcpHost}:${mcpPort} ==="
function Test-Port($h, $p) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($h, $p, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(1000)
        if ($ok) { $tcp.EndConnect($iar); $tcp.Close(); return $true } else { $tcp.Close(); return $false }
    } catch { return $false }
}
if (-not (Test-Port $mcpHost $mcpPort)) {
    Write-Warning "MCP not reachable on ${mcpHost}:${mcpPort}"
    Write-Host "Open FreeCAD and run in the Python Console:"
    Write-Host "  exec(open(r'$repoRoot\mcp_server\mcp_serverV3.py', encoding='utf-8').read())"
    $null = Read-Host "Press Enter when the MCP server is running"
    if (-not (Test-Port $mcpHost $mcpPort)) {
        Write-Error "MCP все ещё недоступен. Прерывание."
        exit 30
    }
}

# -----------------------
# Step 4: Send stubs
# -----------------------
Write-Host ""
Write-Host "=== Step 4/4: Send stubs ==="
$clientPy = Get-VenvPython ""
& $clientPy $sendCli --stubs $stubsFile --host $mcpHost --port $mcpPort -v
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Client exited with $LASTEXITCODE"
}
Write-Host "Pipeline finished. Check FreeCAD for placed objects."
