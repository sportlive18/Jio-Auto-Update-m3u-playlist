# Update JioTV Playlist Script
$url = "https://raw.githubusercontent.com/alex4528x/m3u/main/jtv.m3u"
$output = "jiotv.m3u"

Write-Host "Updating JioTV playlist from source..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $url -OutFile $output
    Write-Host "Successfully updated $output" -ForegroundColor Green
} catch {
    Write-Host "Failed to update playlist: $_" -ForegroundColor Red
}
