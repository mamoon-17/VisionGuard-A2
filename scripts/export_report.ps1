param([string]$Source,[string]$Destination)
$ErrorActionPreference='Stop'
$wordApp=New-Object -ComObject Word.Application
$wordApp.Visible=$false
$wordApp.DisplayAlerts=0
$confirm=$false
$readOnly=$true
$document=$wordApp.Documents.Open([ref]$Source,[ref]$confirm,[ref]$readOnly)
try {
    $document.ExportAsFixedFormat($Destination,17)
    Write-Output ('Exported '+$Destination+' | pages='+$document.ComputeStatistics(2))
} finally {
    $document.Close(0)
    if ($wordApp.Documents.Count -eq 0) { $wordApp.Quit() }
}
