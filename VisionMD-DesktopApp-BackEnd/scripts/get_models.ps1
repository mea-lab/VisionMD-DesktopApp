$ErrorActionPreference = "Stop"

$WiLorUrl = "https://www.dropbox.com/scl/fi/p7vxvq3prz4r46dzqoqer/pretrained_models.zip?rlkey=zwc2qnlgexrmxp7zd34cd5jio&st=c4pin9f0&dl=1"
$HandUrl = "https://www.dropbox.com/scl/fi/ft9pcyce80hyxeuni9u7c/best_hand_model.pt?rlkey=hdghmzs69snszakdahb77cf84&st=7oealk32&dl=1"
$MetrabsUrl = "https://www.dropbox.com/scl/fi/nzd62nooitrh68suvau2e/metrabs_eff2l_384px_800k_28ds_pytorch.zip?rlkey=cjycmqo5c6j188jb7en1esu5i&st=dvblobch&dl=1"

$ModelDir = Join-Path $PSScriptRoot "..\app\analysis\models"
$WiLorDir = Join-Path $ModelDir "wilor_mini\pretrained_models"
$HandDir = Join-Path $ModelDir "hand_detector"
$MetrabsDir = Join-Path $ModelDir "metrabs_eff2l_384px_800k_28ds_pytorch"
$WorkDir = Join-Path ([IO.Path]::GetTempPath()) ("visionmd-models-" + [guid]::NewGuid())

function Test-ModelFile([string] $Path, [string] $ExpectedHash) {
    return (Test-Path -LiteralPath $Path -PathType Leaf) -and
        ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash)
}

function Get-Download([string] $Url, [string] $Destination) {
    Write-Host "Downloading $(Split-Path $Destination -Leaf)..."
    & curl.exe --fail --location --retry 3 --output $Destination $Url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
}

function Install-ArchiveFile([string] $Root, [string] $Name, [string] $Hash, [string] $Destination) {
    $matches = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Filter $Name)
    if ($matches.Count -ne 1) { throw "Expected exactly one $Name in the downloaded archive; found $($matches.Count)." }
    if (-not (Test-ModelFile $matches[0].FullName $Hash)) { throw "SHA-256 mismatch for $Name." }
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination -Parent) | Out-Null
    Copy-Item -LiteralPath $matches[0].FullName -Destination $Destination -Force
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
try {
    if (-not (Test-Path -LiteralPath $ModelDir -PathType Container)) { throw "Model directory does not exist: $ModelDir" }

    $PosePath = Join-Path $ModelDir "yolo11n-pose.pt"
    if (-not (Test-ModelFile $PosePath "869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0")) {
        $PoseDownload = Join-Path $WorkDir "yolo11n-pose.pt"
        Get-Download "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt" $PoseDownload
        if (-not (Test-ModelFile $PoseDownload "869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0")) { throw "YOLO pose SHA-256 mismatch." }
        Copy-Item -LiteralPath $PoseDownload -Destination $PosePath -Force
    }

    $wilorFiles = @(
        @("wilor_final.ckpt", "3e97aafc7dd08d883a4cc5a027df61fdb6fda6136dbd1319405413862ada6bb2"),
        @("detector.pt", "5ef3df44e42d2db52d4ffe91f83a22ce9925e2acc9abebf453f2c5d22e380033"),
        @("MANO_RIGHT.pkl", "45d60aa3b27ef9107a7afd4e00808f307fd91111e1cfa35afd5c4a62de264767"),
        @("mano_mean_params.npz", "efc0ec58e4a5cef78f3abfb4e8f91623b8950be9eff8b8e0dbb0d036ebc63988")
    )
    $wilorOk = $true
    foreach ($entry in $wilorFiles) {
        if (-not (Test-ModelFile (Join-Path $WiLorDir $entry[0]) $entry[1])) { $wilorOk = $false }
    }
    if ($wilorOk) {
        Write-Host "WiLoR models already exist and passed verification."
    } else {
        $archive = Join-Path $WorkDir "pretrained_models.zip"
        $extract = Join-Path $WorkDir "wilor"
        Get-Download $WiLorUrl $archive
        Expand-Archive -LiteralPath $archive -DestinationPath $extract -Force
        foreach ($entry in $wilorFiles) {
            Install-ArchiveFile $extract $entry[0] $entry[1] (Join-Path $WiLorDir $entry[0])
        }
        Write-Host "WiLoR models installed in $WiLorDir"
    }

    $handHash = "12ec0eb2ec19324b85728c14a9de7dc4c2b0c93249ff79daff19fc9a2b58cb21"
    $handTarget = Join-Path $HandDir "best_hand_model.pt"
    if (Test-ModelFile $handTarget $handHash) {
        Write-Host "Hand detector already exists and passed verification."
    } else {
        $handDownload = Join-Path $WorkDir "best_hand_model.pt"
        Get-Download $HandUrl $handDownload
        if (-not (Test-ModelFile $handDownload $handHash)) { throw "SHA-256 mismatch for best_hand_model.pt." }
        New-Item -ItemType Directory -Force -Path $HandDir | Out-Null
        Copy-Item -LiteralPath $handDownload -Destination $handTarget -Force
        Write-Host "Hand detector installed in $HandDir"
    }

    $metrabsFiles = @(
        @("ckpt.pt", "cd9be4587f364d1c19bcdecfa2a5db1baa457ae1f100fe3aca29aef23437c1c3"),
        @("config.yaml", "2ae9620540d6487c071d88bed723cae28e68e040fe38ee0e819c6be695af0d95"),
        @("joint_info.npz", "de211b8679238955ada9a0f0b06bfccc2ea8fc5914d6feb9b3fd2d0b2b1cd97b"),
        @("joint_transform_matrix.npy", "a1dd2b3c4807c1abd447300f142fe97673c40b510fac7d2cd2d6aa132a6a27cc"),
        @("skeleton_infos.pkl", "952849909e6ad179ea297365e91534a2d06f0884e0a34cb7b5998ff1522a96c5")
    )
    $metrabsOk = $true
    foreach ($entry in $metrabsFiles) {
        if (-not (Test-ModelFile (Join-Path $MetrabsDir $entry[0]) $entry[1])) { $metrabsOk = $false }
    }
    if ($metrabsOk) {
        Write-Host "MeTRAbs model already exists and passed verification."
    } else {
        $archive = Join-Path $WorkDir "metrabs.zip"
        $extract = Join-Path $WorkDir "metrabs"
        Get-Download $MetrabsUrl $archive
        Expand-Archive -LiteralPath $archive -DestinationPath $extract -Force
        foreach ($entry in $metrabsFiles) {
            Install-ArchiveFile $extract $entry[0] $entry[1] (Join-Path $MetrabsDir $entry[0])
        }
        Write-Host "MeTRAbs model installed in $MetrabsDir"
    }

    Write-Host "All VisionMD model assets are installed and verified."
} finally {
    Remove-Item -LiteralPath $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
}
