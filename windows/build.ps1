#requires -Version 5.1
<#
.SYNOPSIS
  Build the Docker-edition and native-bootstrap Windows one-file EXEs.

.DESCRIPTION
  Creates .venv-build, installs pinned PyInstaller, builds both the stable
  Docker-edition launcher and the native-edition bootstrap/guide EXE, then
  smoke-tests both with --version/--help. Docker Desktop and native NTQQ are
  not required to build or smoke-test the executables.
#>
[CmdletBinding()]
param(
    [string]$Python = '',
    [switch]$SkipInstall,
    [switch]$Clean,
    [switch]$NoClean
)

$ErrorActionPreference = 'Stop'
$RootDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$VenvDir = Join-Path $RootDir '.venv-build'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'

function Get-BuildPython {
    if (-not [string]::IsNullOrWhiteSpace($Python)) {
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw "Python executable not found: $Python"
        }
        return [pscustomobject]@{ File = (Resolve-Path -LiteralPath $Python).Path; Prefix = @() }
    }
    foreach ($name in @('python.exe', 'python', 'py.exe', 'py')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -eq $command) {
            continue
        }
        $file = [string]$command.Source
        if ([string]::IsNullOrWhiteSpace($file)) {
            $file = [string]$command.Path
        }
        if ([string]::IsNullOrWhiteSpace($file)) {
            continue
        }
        if ($name -eq 'py.exe' -or $name -eq 'py') {
            return [pscustomobject]@{ File = $file; Prefix = @('-3') }
        }
        return [pscustomobject]@{ File = $file; Prefix = @() }
    }
    throw 'Python 3.10+ was not found. Install Python and reopen PowerShell, or pass -Python <path>.'
}

function Invoke-PythonChecked {
    param([string[]]$Arguments, [string]$Operation)
    $all = @($script:BasePythonPrefix) + @($Arguments)
    & $script:BasePythonFile @all
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed with exit code {1}" -f $Operation, $LASTEXITCODE)
    }
}

function Invoke-VenvPythonChecked {
    param([string[]]$Arguments, [string]$Operation)
    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed with exit code {1}" -f $Operation, $LASTEXITCODE)
    }
}

Push-Location $RootDir
try {
    Write-Host '=== QQ Bot Studio Windows build ===' -ForegroundColor Cyan
    $basePython = Get-BuildPython
    $script:BasePythonFile = $basePython.File
    $script:BasePythonPrefix = @($basePython.Prefix)
    $versionPolicy = & $script:BasePythonFile @($script:BasePythonPrefix) -c "import sys; print('%d.%d' % sys.version_info[:2])"
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not query the selected Python version.'
    }
    $versionParts = ([string]$versionPolicy).Trim().Split('.')
    $major = [int]$versionParts[0]
    $minor = [int]$versionParts[1]
    if ($major -ne 3 -or $minor -lt 10) {
        throw ("Python 3.10+ is required; selected {0}.{1}." -f $major, $minor)
    }
    Write-Host ("Python: {0} ({1}.{2})" -f $basePython.File, $major, $minor)

    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Host 'Creating .venv-build...'
        Invoke-PythonChecked -Arguments @('-m', 'venv', $VenvDir) -Operation 'python -m venv'
    }
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        throw "Build virtualenv Python was not created: $VenvPython"
    }

    if (-not $SkipInstall) {
        Write-Host 'Installing pinned build requirements...'
        Invoke-VenvPythonChecked -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip') -Operation 'pip upgrade'
        Invoke-VenvPythonChecked -Arguments @('-m', 'pip', 'install', '-r', (Join-Path $RootDir 'requirements-build.txt')) -Operation 'pip install requirements-build.txt'
    }

    if ($Clean -or -not $NoClean) {
        foreach ($path in @((Join-Path $RootDir 'build'), (Join-Path $RootDir 'dist'))) {
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Recurse -Force
            }
        }
    }

    $env:QQBOT_WINDOWS_ROOT = $RootDir
    $buildTargets = @(
        [pscustomobject]@{
            Name = 'Docker edition'
            Spec = (Join-Path $RootDir 'windows\qqbot-studio-windows.spec')
            ExeName = 'QQBotStudioWindows.exe'
        },
        [pscustomobject]@{
            Name = 'Native bootstrap edition'
            Spec = (Join-Path $RootDir 'windows\qqbot-studio-windows-native.spec')
            ExeName = 'QQBotStudioWindowsNative.exe'
        }
    )

    $results = @()
    foreach ($target in $buildTargets) {
        Write-Host ''
        Write-Host ("Running PyInstaller for {0}..." -f $target.Name) -ForegroundColor Cyan
        Invoke-VenvPythonChecked -Arguments @(
            '-m', 'PyInstaller',
            '--noconfirm',
            '--clean',
            $target.Spec
        ) -Operation ("PyInstaller " + $target.Name)

        $exePath = Join-Path $RootDir ('dist\' + $target.ExeName)
        if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
            throw "Expected build artifact was not produced: $exePath"
        }

        Write-Host ("Smoke-testing {0} (does not require Docker Desktop)..." -f $target.ExeName)
        & $exePath --version
        if ($LASTEXITCODE -ne 0) {
            throw ("{0} --version failed with exit code {1}" -f $target.ExeName, $LASTEXITCODE)
        }
        & $exePath --help | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw ("{0} --help failed with exit code {1}" -f $target.ExeName, $LASTEXITCODE)
        }

        $results += [pscustomobject]@{
            Name = $target.Name
            ExeName = $target.ExeName
            Path = $exePath
            Size = (Get-Item -LiteralPath $exePath).Length
            Hash = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }

    $checksumPath = Join-Path $RootDir 'dist\SHA256SUMS.txt'
    $checksumLines = @($results | ForEach-Object { "{0}  {1}" -f $_.Hash, $_.ExeName })
    Set-Content -LiteralPath $checksumPath -Value $checksumLines -Encoding Ascii
    Write-Host ''
    foreach ($result in $results) {
        Write-Host ("{0} artifact : {1}" -f $result.Name, $result.Path) -ForegroundColor Green
        Write-Host ("  Size       : {0} bytes" -f $result.Size)
        Write-Host ("  SHA256     : {0}" -f $result.Hash)
    }
    Write-Host ("Checksum     : {0}" -f $checksumPath) -ForegroundColor Green
} finally {
    Pop-Location
}
