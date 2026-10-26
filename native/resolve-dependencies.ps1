[CmdletBinding()]
param([string]$OutputDirectory = "$PSScriptRoot\vendor")

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$artifacts = @(
    @{ Name = 'commons-logging-1.1.1.jar'; Url = 'https://repo1.maven.org/maven2/commons-logging/commons-logging/1.1.1/commons-logging-1.1.1.jar' },
    @{ Name = 'commons-lang-2.5.jar'; Url = 'https://repo1.maven.org/maven2/commons-lang/commons-lang/2.5/commons-lang-2.5.jar' },
    @{ Name = 'commons-codec-1.6.jar'; Url = 'https://repo1.maven.org/maven2/commons-codec/commons-codec/1.6/commons-codec-1.6.jar' },
    @{ Name = 'commons-collections-3.2.jar'; Url = 'https://repo1.maven.org/maven2/commons-collections/commons-collections/3.2/commons-collections-3.2.jar' }
)
foreach ($artifact in $artifacts) {
    $destination = Join-Path $OutputDirectory $artifact.Name
    if (-not (Test-Path -LiteralPath $destination)) {
        Invoke-WebRequest -Uri $artifact.Url -OutFile $destination
    }
    if ((Get-Item -LiteralPath $destination).Length -lt 1000) { throw "Downloaded dependency is unexpectedly small: $destination" }
}
Write-Output "Cisco IPC runtime dependencies are available in $OutputDirectory"
