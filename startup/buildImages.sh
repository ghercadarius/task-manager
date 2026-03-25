#!/bin/bash

set -e
cd .. || exit 1

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

echo "Docker images built and loaded into Minikube successfully."