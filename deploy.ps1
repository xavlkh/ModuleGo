# deploy.ps1 — Manual deploy via SSH from Windows
# Usage:
#   .\deploy.ps1 dev     # Deploy dev branch image
#   .\deploy.ps1 prod    # Deploy prod (latest) image

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Env
)

$EC2_IP = "52.77.236.110"
$SSH_KEY = "admin.pem"

if ($Env -eq "prod") {
    $REMOTE_DIR = "~/modulego-prod"
    $PORT = 5000
} else {
    $REMOTE_DIR = "~/modulego-dev"
    $PORT = 5001
}

Write-Host "==> Deploying $Env to $EC2_IP..." -ForegroundColor Cyan

Write-Host "    Pulling latest image..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$EC2_IP "cd $REMOTE_DIR && docker compose pull"

Write-Host "    Restarting containers..."
ssh -i $SSH_KEY ubuntu@$EC2_IP "cd $REMOTE_DIR && docker compose up -d"

Write-Host "    Waiting for app to start..."
Start-Sleep -Seconds 10

Write-Host "    Verifying..."
$status = ssh -i $SSH_KEY ubuntu@$EC2_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost:$PORT"

if ($status -eq "200") {
    Write-Host "==> Deploy complete! http://${EC2_IP}:${PORT}" -ForegroundColor Green
} else {
    Write-Host "==> Deploy finished but app returned status $status" -ForegroundColor Yellow
}
