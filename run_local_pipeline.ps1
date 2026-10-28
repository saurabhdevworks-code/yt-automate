# Full YouTube Automation Pipeline (Local PC Execution)
# This uses your authenticated Google Chrome profile (C:\notebooklm-playwright-profile)
# where Google NEVER blocks with password or 2FA challenge!

$ErrorActionPreference = "Stop"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting Full NotebookLM YouTube Automation Pipeline" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Load .env file if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
    Write-Host "Loaded environment variables from .env" -ForegroundColor Gray
}

# 1. Generate Research Pack
Write-Host "`n[1/5] Generating AI Research Pack..." -ForegroundColor Yellow
python -m src.generate_pack --settings config/settings.json --output output

# 2. Find latest research pack
$latest = Get-ChildItem output -Directory -Filter "research-*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) {
    Write-Host "[ERROR] No research pack found in output/" -ForegroundColor Red
    exit 1
}
Write-Host "Using research pack: $($latest.FullName)" -ForegroundColor Green

# 3. Copy files to output root
Copy-Item "$($latest.FullName)\research_brief.md" "output\notebooklm_research_brief.md" -Force
Copy-Item "$($latest.FullName)\notebooklm_prompt.txt" "output\notebooklm_prompt.txt" -Force
Copy-Item "$($latest.FullName)\metadata.json" "output\metadata.json" -Force

# 4. Run NotebookLM Automation with Local Profile
Write-Host "`n[2/5] Automating Google NotebookLM Video Overview..." -ForegroundColor Yellow
$profilePath = "C:\notebooklm-playwright-profile"
python -m src.notebooklm_automation `
    --sources "output\notebooklm_research_brief.md" `
    --prompt "output\notebooklm_prompt.txt" `
    --profile "$profilePath" `
    --output "output\notebooklm" `
    --timeout-minutes 75

# 5. Post-Process Video (Auto-trim last 3s outro & hide NotebookLM watermark)
$videoFile = "output\notebooklm\notebooklm_video.mp4"
if (Test-Path $videoFile) {
    Write-Host "`n[3/5] Post-Processing Video (Trimming 3s outro & replacing watermark)..." -ForegroundColor Yellow
    python -m src.video_processor `
        --video "$videoFile" `
        --mode auto `
        --metadata "output\metadata.json"
} else {
    Write-Host "`n[WARNING] Video file not found at $videoFile to post-process." -ForegroundColor Yellow
}

# 6. Generate Pro High-CTR Thumbnail
Write-Host "`n[4/5] Generating Pro High-CTR Thumbnail with AI & Headless Chrome..." -ForegroundColor Yellow
if (Test-Path "output\metadata.json") {
    python -m src.thumbnail --metadata "output\metadata.json" --video "$videoFile" --output "output\thumbnail.jpg"
} else {
    python -m src.thumbnail --text "किसान बदलेगा" --output "output\thumbnail.jpg"
}

# 7. Upload to YouTube
Write-Host "`n[5/5] Checking YouTube Upload..." -ForegroundColor Yellow
if (Test-Path $videoFile) {
    if ($env:YOUTUBE_CLIENT_ID -and $env:YOUTUBE_CLIENT_SECRET -and $env:YOUTUBE_REFRESH_TOKEN) {
        Write-Host "Uploading video to YouTube privately..." -ForegroundColor Cyan
        if (Test-Path "output\thumbnail.jpg") {
            python -m src.youtube_upload --video "$videoFile" --metadata "output\metadata.json" --privacy private --thumbnail "output\thumbnail.jpg" --result "output\upload_result.json"
        } else {
            python -m src.youtube_upload --video "$videoFile" --metadata "output\metadata.json" --privacy private --result "output\upload_result.json"
        }
        Write-Host "`n==========================================================" -ForegroundColor Green
        Write-Host "  SUCCESS! Video generated and uploaded to YouTube!" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
    } else {
        Write-Host "`n==========================================================" -ForegroundColor Green
        Write-Host "  SUCCESS! Video generated: $videoFile" -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "[NOTE] YouTube API secrets not in .env. Video is ready in output/notebooklm/ folder." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[ERROR] Video file not found at $videoFile" -ForegroundColor Red
}
