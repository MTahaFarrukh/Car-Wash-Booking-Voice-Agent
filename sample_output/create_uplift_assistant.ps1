# Create Uplift AI voice assistant for car wash booking.
# Usage: .\sample_output\create_uplift_assistant.ps1

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
$jsonFile = Join-Path $projectRoot "agents\uplift_assistant.json"

if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env file not found. Copy .env.example to .env first."
    exit 1
}

$apiKey = (Get-Content $envFile | Where-Object { $_ -match '^UPLIFT_API_KEY=' }) -replace '^UPLIFT_API_KEY=', ''
if (-not $apiKey -or $apiKey -eq "your_uplift_api_key") {
    Write-Host "ERROR: Set UPLIFT_API_KEY in .env first."
    exit 1
}

$body = Get-Content $jsonFile -Raw

$response = Invoke-RestMethod `
    -Uri "https://api.upliftai.org/v1/realtime-assistants" `
    -Method POST `
    -Headers @{
        Authorization = "Bearer $apiKey"
        "Content-Type" = "application/json"
    } `
    -Body $body

Write-Host ""
Write-Host "Assistant created successfully!"
Write-Host "Assistant ID: $($response.realtimeAssistantId)"
Write-Host ""
Write-Host "Add this to your .env file:"
Write-Host "UPLIFT_ASSISTANT_ID=$($response.realtimeAssistantId)"
Write-Host ""
Write-Host "Next: open sample_output/voice_client.html and paste the Assistant ID."
