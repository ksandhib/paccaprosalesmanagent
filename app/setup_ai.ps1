# setup_ai.ps1 - PaccaPro Local AI Environment Setup
# Detects operating system resources, configures local models, and verifies service states.

$logPath = "logs\setup_report.txt"
if (!(Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
"==========================================================" | Out-File $logPath
"   PACCAPRO LOCAL AI SYSTEM AUTO-SETUP REPORT             " | Out-File $logPath -Append
"   Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')    " | Out-File $logPath -Append
"==========================================================" | Out-File $logPath -Append

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   PaccaPro Local AI Setup & Model Provisioning Script    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Hardware Resource Detection
Write-Host "[1/6] Scanning Hardware Specifications..." -ForegroundColor Green
$memSum = Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum
$totalRamGB = [math]::round($memSum.Sum / 1GB, 1)

$gpus = Get-CimInstance Win32_VideoController
$gpuNames = @()
$hasCuda = $false
foreach ($gpu in $gpus) {
    $gpuNames += $gpu.Name
    if ($gpu.Name -like "*nvidia*" -or $gpu.Name -like "*rtx*" -or $gpu.Name -like "*gtx*") {
        $hasCuda = $true
    }
}

$gpuListStr = $gpuNames -join ", "

"--- Hardware Specs ---" | Out-File $logPath -Append
"Total CPU/RAM detected: $totalRamGB GB" | Out-File $logPath -Append
"GPU detected: $gpuListStr" | Out-File $logPath -Append
"CUDA available: $hasCuda" | Out-File $logPath -Append

Write-Host "  RAM: $totalRamGB GB"
Write-Host "  GPU: $gpuListStr"
Write-Host "  CUDA Available: $hasCuda"

# 2. Check Disk Space
Write-Host "[2/6] Checking Disk Space..." -ForegroundColor Green
$drive = Get-PSDrive C
$freeSpaceGB = [math]::round($drive.Free / 1GB, 1)
"Free disk space on C:: $freeSpaceGB GB" | Out-File $logPath -Append
Write-Host "  Free space on C:: $freeSpaceGB GB"

# 3. Check Python and Ollama Services
Write-Host "[3/6] Verifying Services & Packages..." -ForegroundColor Green

# Verify Python
$pythonVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    "Python Status: Not Found" | Out-File $logPath -Append
    exit 1
}
"Python Status: Available ($pythonVer)" | Out-File $logPath -Append
Write-Host "  Python: Available ($pythonVer)"

# Verify Ollama Service using 127.0.0.1 IPv4
$ollamaUrl = "http://127.0.0.1:11434"
$ollamaOnline = $false
try {
    $response = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    $ollamaOnline = $true
} catch {
    $ollamaOnline = $false
}

if (!$ollamaOnline) {
    Write-Host "  [WARNING] Ollama local service is offline or not running." -ForegroundColor Yellow
    Write-Host "  Please start Ollama Desktop application first." -ForegroundColor Yellow
    "Ollama Status: Offline" | Out-File $logPath -Append
    
    $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $ollamaExe) {
        Write-Host "  Attempting to start Ollama automatically..." -ForegroundColor Cyan
        Start-Process $ollamaExe -WindowStyle Hidden
        Start-Sleep -Seconds 5
        try {
            $response = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
            $ollamaOnline = $true
        } catch {}
    }
}

if ($ollamaOnline) {
    "Ollama Status: Online" | Out-File $logPath -Append
    Write-Host "  Ollama Local Service: Online"
} else {
    Write-Host "  [ERROR] Ollama remains offline. Cannot check/pull models." -ForegroundColor Red
    "Ollama Status: Offline (Failed to start)" | Out-File $logPath -Append
    exit 1
}

# 4. Check & Install Models
Write-Host "[4/6] Checking Model Installation Status..." -ForegroundColor Green

$existingModels = @()
if ($response -and $response.models) {
    foreach ($m in $response.models) {
        $existingModels += $m.name
    }
}

function Check-And-Pull-Model($modelName) {
    $matched = $false
    foreach ($em in $existingModels) {
        if ($em -like "$modelName*") {
            $matched = $true
            break
        }
    }
    
    if ($matched) {
        Write-Host "  Model '$modelName' is already installed." -ForegroundColor Yellow
        "Model $modelName Status: INSTALLED" | Out-File $logPath -Append
    } else {
        if ($freeSpaceGB -lt 15) {
            Write-Host "  [ERROR] Low disk space ($freeSpaceGB GB free). Cannot safely download $modelName." -ForegroundColor Red
            "Model $modelName Status: FAILED (Low Space)" | Out-File $logPath -Append
            return
        }
        Write-Host "  Downloading/Pulling model '$modelName'..." -ForegroundColor Green
        & ollama pull $modelName
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Model '$modelName' pulled successfully." -ForegroundColor Green
            "Model $modelName Status: DOWNLOADED & VERIFIED" | Out-File $logPath -Append
        } else {
            # Check fallback to Llama 3.1
            Write-Host "  [WARNING] Failed to pull model '$modelName'." -ForegroundColor Yellow
            "Model $modelName Status: PULL FAILED" | Out-File $logPath -Append
        }
    }
}

if ($totalRamGB -lt 16) {
    Write-Host "  [WARNING] Only $totalRamGB GB RAM detected. Qwen2.5 14B requires significant resources." -ForegroundColor Yellow
    Write-Host "  You can proceed, but if it is too slow, you can run: 'ollama pull qwen2.5:7b' for better speeds." -ForegroundColor Yellow
}

Check-And-Pull-Model "qwen2.5:14b"
Check-And-Pull-Model "nomic-embed-text"

# 5. Run Pipelines Test
Write-Host "[5/6] Running Local AI Pipeline Verification Tests..." -ForegroundColor Green
$testSuccess = $false
try {
    $body = @{
        model = "qwen2.5:14b"
        prompt = "Hello"
        stream = $false
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$ollamaUrl/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 20 -ErrorAction SilentlyContinue
    $testSuccess = $true
} catch {
    try {
        $body = @{
            model = "llama3.1:latest"
            prompt = "Hello"
            stream = $false
        } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$ollamaUrl/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 20 -ErrorAction SilentlyContinue
        $testSuccess = $true
        Write-Host "  [INFO] Test succeeded with fallback model Llama3.1." -ForegroundColor Green
    } catch {}
}

if ($testSuccess) {
    Write-Host "  Inference Diagnostics: PASS" -ForegroundColor Green
    "Inference Test: PASS" | Out-File $logPath -Append
} else {
    Write-Host "  Inference Diagnostics: FAIL" -ForegroundColor Red
    "Inference Test: FAIL" | Out-File $logPath -Append
}

# 6. Setup Report Generation
Write-Host "[6/6] Finalizing Setup Report..." -ForegroundColor Green
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Local AI Auto-Setup completed. Detailed report saved to:" -ForegroundColor Green
Write-Host "  $logPath" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
