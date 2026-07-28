#!/usr/bin/env bash
# deploy.sh — Build the ModuleGo image, load it into minikube, and apply K8s manifests.
# Usage: ./deploy.sh
set -euo pipefail

echo "==> Checking minikube status..."
if ! minikube status --format='{{.Host}}' 2>/dev/null | grep -q Running; then
  echo "    Starting minikube..."
  minikube start
fi

echo "==> Building Docker image inside minikube..."
# Use minikube's Docker daemon so the image is available to K8s without a registry.
eval $(minikube docker-env)
docker build -t modulego:latest .

echo "==> Loading image into minikube (fallback if docker-env didn't take effect)..."
# docker-env doesn't always persist across shell sessions; explicit load is safer.
minikube image load modulego:latest

echo "==> Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml

echo "==> Waiting for pods to be ready..."
kubectl -n modulego wait --for=condition=ready pod -l app=postgres --timeout=120s
kubectl -n modulego wait --for=condition=ready pod -l app=modulego --timeout=120s

echo ""
echo "==> Deployment complete!"
echo "    Access the app:"
kubectl -n modulego get svc modulego
echo ""
echo "    Or port-forward:"
echo "    kubectl -n modulego port-forward svc/modulego 5000:5000"
echo "    Then open http://localhost:5000"
