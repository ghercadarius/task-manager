#!/bin/bash

set -e

echo "Deleting existing deployments..."
kubectl delete -f ./login/login-service-deployment.yaml
kubectl delete -f ./user/user-service-deployment.yaml

# Build Docker images
echo "Building Docker images..."
docker build -t login-service ./login
minikube image load login-service:latest

docker build -t user-service ./user
minikube image load user-service:latest

echo "Applying Kubernetes deployment for login..."
kubectl apply -f ./login/login-service-deployment.yaml

echo "Applying Kubernetes deployment for user..."
kubectl apply -f ./user/user-service-deployment.yaml
