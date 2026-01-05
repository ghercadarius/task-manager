#!/bin/bash

set -e

echo "Deleting existing deployments..."
kubectl delete -f ./envoy/envoy-deployment.yaml
kubectl delete -f ./login/login-service-deployment.yaml
kubectl delete -f ./user/user-service-deployment.yaml
kubectl delete -f ./database/postgres-deployment.yaml
kubectl delete -f ./team/team-service-deployment.yaml
kubectl delete -f ./task/task-service-deployment.yaml
kubectl delete -f ./note/note-service-deployment.yaml
kubectl delete -f ./database/pgadmin-deployment.yaml
kubectl delete -f ./database/pgadmin-service.yaml
kubectl delete -f ./database/pgadmin-configmap.yaml

cp database/models.py login/models.py
cp database/models.py team/models.py
cp database/models.py user/models.py
cp database/models.py task/models.py
cp database/models.py note/models.py

# Build Docker images
echo "Building Docker images..."
docker build -t login-service ./login
minikube image load login-service:latest
rm login/models.py

docker build -t user-service ./user
minikube image load user-service:latest
rm user/models.py

docker build -t team-service ./team
minikube image load team-service:latest
rm team/models.py

docker build -t task-service ./task
minikube image load task-service:latest
rm task/models.py

docker build -t note-service ./note
minikube image load note-service:latest
rm note/models.py

echo "Applying Kubernetes deployment for gateway..."
kubectl apply -f ./envoy/envoy-deployment.yaml

echo "Applying Kubernetes deployment for database..."
kubectl apply -f ./database/postgres-deployment.yaml

echo "Applying Kubernetes deployment for pgAdmin..."
kubectl apply -f ./database/pgadmin-configmap.yaml
sleep 2
kubectl apply -f ./database/pgadmin-deployment.yaml
sleep 2
kubectl apply -f ./database/pgadmin-service.yaml

sleep 5  # Wait for the database to be ready

echo "Applying Kubernetes deployment for login..."
kubectl apply -f ./login/login-service-deployment.yaml

echo "Applying Kubernetes deployment for user..."
kubectl apply -f ./user/user-service-deployment.yaml

echo "Applying Kubernetes deployment for team..."
kubectl apply -f ./team/team-service-deployment.yaml

echo "Applying Kubernetes deployment for task..."
kubectl apply -f ./task/task-service-deployment.yaml

echo "Applying Kubernetes deployment for note..."
kubectl apply -f ./note/note-service-deployment.yaml

echo "All services started successfully!"