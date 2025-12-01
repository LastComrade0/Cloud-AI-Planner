# PowerShell script to connect to RDS via AWS Systems Manager Session Manager
# This creates a port forwarding tunnel through an EC2 instance in the same VPC

param(
    [Parameter(Mandatory=$true)]
    [string]$InstanceId,
    
    [Parameter(Mandatory=$true)]
    [string]$RdsEndpoint,
    
    [Parameter(Mandatory=$false)]
    [int]$LocalPort = 5432,
    
    [Parameter(Mandatory=$false)]
    [int]$RemotePort = 5432
)

Write-Host "Starting SSM port forwarding session..." -ForegroundColor Green
Write-Host "Instance ID: $InstanceId" -ForegroundColor Cyan
Write-Host "RDS Endpoint: $RdsEndpoint" -ForegroundColor Cyan
Write-Host "Local Port: $LocalPort" -ForegroundColor Cyan
Write-Host "Remote Port: $RemotePort" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will forward localhost:$LocalPort to $RdsEndpoint`:$RemotePort" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the tunnel" -ForegroundColor Yellow
Write-Host ""

# Start the SSM port forwarding session
aws ssm start-session `
    --target $InstanceId `
    --document-name AWS-StartPortForwardingSessionToRemoteHost `
    --parameters "{
        \"host\": [\"$RdsEndpoint\"],
        \"portNumber\": [\"$RemotePort\"],
        \"localPortNumber\": [\"$LocalPort\"]
    }"

