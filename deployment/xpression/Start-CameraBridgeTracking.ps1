<# Run with Windows PowerShell 5.1: powershell.exe -STA -File .\Start-CameraBridgeTracking.ps1 ... #>
[CmdletBinding()]
param(
    [string]$Source = '192.168.96.122',
    [string]$BindAddress = '0.0.0.0',
    [ValidateRange(1024,65535)][int]$Port = 40001,
    [ValidateRange(0,255)][int]$CameraId = 1,
    [string]$Scene = '',
    [string]$Camera = 'Camera1',
    [int]$Framebuffer = 0,
    [int]$Layer = 0,
    [double]$PanSign = -1,
    [double]$TiltSign = 1,
    [double]$RollSign = -1,
    [double]$RotXOffset = 0,
    [double]$RotYOffset = 0,
    [double]$RotZOffset = 0,
    [string]$LensCsv = '',
    [switch]$CheckOnly,
    [int]$PacketLimit = 0,
    [string]$Sdk = 'C:\Program Files\XPressionStudio\net\xpression.net.dll'
)
$ErrorActionPreference = 'Stop'
if (-not $CheckOnly -and -not $Scene) { throw 'Set -Scene to the exact name of the scene on the selected output layer.' }
if (-not (Test-Path -LiteralPath $Sdk)) { throw 'Set -Sdk to the installed XPression xpression.net.dll file.' }
Add-Type -Path $Sdk
Add-Type -Path (Join-Path $PSScriptRoot 'CameraBridgeTracking.cs') -ReferencedAssemblies $Sdk
[CameraBridgeTracking]::Run($Source, $BindAddress, $Port, $CameraId, $Scene, $Camera,
    $Framebuffer, $Layer, $PanSign, $TiltSign, $RollSign,
    $RotXOffset, $RotYOffset, $RotZOffset, $LensCsv, [bool]$CheckOnly, $PacketLimit)
