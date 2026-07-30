# deploy.ps1 — Build the ModuleGo image, load it into minikube, and apply K8s manifests.
# Usage: .\deploy.ps1
$ErrorActionPreference = "Stop"

function Wait-ForKey {
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

try {
    Write-Host "==> Checking minikube status..."
    $status = minikube status --format='{{.Host}}' 2>$null
    if ($status -ne "Running") {
        Write-Host "    Starting minikube..."
        minikube start
    }

    Write-Host "==> Building Docker image inside minikube..."
    # Use minikube's Docker daemon so the image is available to K8s without a registry.
    $env:DOCKER_TLS_VERIFY = "1"
    $env:DOCKER_HOST = "tcp://$(minikube ip):2376"
    $env:DOCKER_CERT_PATH = "$HOME\.minikube\certs"
    docker build -t modulego:latest .

    Write-Host "==> Loading image into minikube (fallback if docker-env didn't take effect)..."
    # docker-env doesn't always persist across shell sessions; explicit load is safer.
    minikube image load modulego:latest

    Write-Host "==> Applying Kubernetes manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/postgres-secret.yaml
    kubectl apply -f k8s/postgres-pvc.yaml
    kubectl apply -f k8s/postgres-deployment.yaml
    kubectl apply -f k8s/postgres-service.yaml
    kubectl apply -f k8s/app-deployment.yaml
    kubectl apply -f k8s/app-service.yaml

    Write-Host "==> Waiting for pods to be ready..."
    kubectl -n modulego wait --for=condition=ready pod -l app=postgres --timeout=120s
    kubectl -n modulego wait --for=condition=ready pod -l app=modulego --timeout=120s

    Write-Host ""
    Write-Host "==> Deployment complete!"
    Write-Host "    Access the app:"
    kubectl -n modulego get svc modulego
    Write-Host ""
    Write-Host "    Or port-forward:"
    Write-Host "    kubectl -n modulego port-forward svc/modulego 5000:5000"
    Write-Host "    Then open http://localhost:5000"
}
catch {
    Write-Host "`n==> Deployment failed: $_" -ForegroundColor Red
}
finally {
    Wait-ForKey
}
