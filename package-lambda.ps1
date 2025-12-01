# package-lambda.ps1
# Package application code only (dependencies come from Lambda Layer)

Write-Host "Packaging application code (dependencies from Lambda Layer)..." -ForegroundColor Green

# Clean up
if (Test-Path "lambda-package") {
    Remove-Item -Path "lambda-package" -Recurse -Force
}
if (Test-Path "lambda-deployment.zip") {
    Remove-Item -Path "lambda-deployment.zip" -Force
}

# Create directory
New-Item -ItemType Directory -Force -Path "lambda-package" | Out-Null

# Copy ONLY application code (NO dependencies)
Write-Host "Copying application code..." -ForegroundColor Green
Copy-Item -Path "app" -Destination "lambda-package\app" -Recurse
Copy-Item -Path "main.py" -Destination "lambda-package\main.py"
Copy-Item -Path "lambda_handler.py" -Destination "lambda-package\lambda_handler.py"
if (Test-Path "config.py") {
    Copy-Item -Path "config.py" -Destination "lambda-package\config.py"
}

# Create zip file
Write-Host "Creating deployment package..." -ForegroundColor Green
Compress-Archive -Path "lambda-package\*" -DestinationPath "lambda-deployment.zip" -Force

$zipSize = (Get-Item "lambda-deployment.zip").Length / 1MB
Write-Host "`n✅ Deployment package created!" -ForegroundColor Green
Write-Host "File: lambda-deployment.zip" -ForegroundColor Cyan
Write-Host "Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Cyan
Write-Host "`n⚠️  IMPORTANT: Attach Lambda Layer to your function!" -ForegroundColor Yellow