# JalRakshak AI — 1-Click Push to GitHub Script for ritish-5a
param(
    [string]$RepoName = "JalRakshak-AI"
)

$git = "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🚀 JalRakshak AI — GitHub Repository Synchronizer" -ForegroundColor Green
Write-Host " GitHub Account: ritish-5a" -ForegroundColor Yellow
Write-Host " Target Repo: https://github.com/ritish-5a/$RepoName.git" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Check if remote exists
$remoteExists = & $git remote
if ($remoteExists -contains "origin") {
    & $git remote remove origin
}

& $git remote add origin "https://github.com/ritish-5a/$RepoName.git"
Write-Host "`n[1/2] Remote origin configured: https://github.com/ritish-5a/$RepoName.git" -ForegroundColor Green

Write-Host "[2/2] Pushing main branch to GitHub..." -ForegroundColor Green
& $git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUCCESS! Repository pushed to https://github.com/ritish-5a/$RepoName" -ForegroundColor Green
    Write-Host "👉 Next Step: Go to https://vercel.com/new and click IMPORT on '$RepoName'!" -ForegroundColor Yellow
} else {
    Write-Host "`n⚠️ Note: If authentication prompt appears, enter your GitHub personal access token or sign in." -ForegroundColor Amber
}
