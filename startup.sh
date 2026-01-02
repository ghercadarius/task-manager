#!/bin/bash

set -e

echo "Deleting existing deployments..."
kubectl delete -f ./envoy/envoy-deployment.yaml
kubectl delete -f ./login/login-service-deployment.yaml
kubectl delete -f ./user/user-service-deployment.yaml

# Build Docker images
echo "Building Docker images..."
docker build -t login-service ./login
minikube image load login-service:latest

docker build -t user-service ./user
minikube image load user-service:latest

echo "Applying Kubernetes deployment for gateway..."
kubectl apply -f ./envoy/envoy-deployment.yaml

echo "Applying Kubernetes deployment for login..."
kubectl apply -f ./login/login-service-deployment.yaml

echo "Applying Kubernetes deployment for user..."
kubectl apply -f ./user/user-service-deployment.yaml

echo "All services started successfully!"