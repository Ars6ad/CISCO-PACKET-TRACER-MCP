[CmdletBinding()]
param(
    [string]$PacketTracerRoot = 'C:\Program Files\Cisco Packet Tracer 9.0.0',
    [string]$OutputDirectory = "$PSScriptRoot\build"
)

$ErrorActionPreference = 'Stop'
$sdk = Join-Path $PacketTracerRoot 'help\default\ipc\pt-cep-java-framework-9.0.0.0.jar'
$source = Join-Path $PSScriptRoot 'src\main\java\io\packetcraft\ptmp\PacketCraftPtmp.java'
if (-not (Get-Command javac -ErrorAction SilentlyContinue)) { throw 'JDK compiler (javac) is required.' }
if (-not (Test-Path -LiteralPath $sdk)) { throw "Cisco IPC SDK was not found: $sdk" }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
javac --release 8 -encoding UTF-8 -cp $sdk -d $OutputDirectory $source
if ($LASTEXITCODE -ne 0) { throw 'Native sidecar compilation failed.' }
Write-Output "Compiled PacketCraft PTMP sidecar to $OutputDirectory"
