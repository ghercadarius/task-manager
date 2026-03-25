# Task Manager

Project made by Darius Gherca and Cristian-Eduard Lungu for Cloud Computing Course.

Kubernetes-based microservices app. All requests are routed through Envoy Gateway. The project uses Postgres for database technology and pgAdmin for database management. Portainer is used for cluster management and overview. Monitoring is done via kube-prometheus-stack helm repository(Prometheus, Grafana, kube-state-metrics, node-exporter).

## Stack
- Gateway: Envoy (listeners for 80 - service, 8081 - pgadmin, 8082 - portainer, 8083 - grafana)
- DB: Postgres + pgAdmin
- Services: login with JWT validated by Envoy for all requests, User, Team, Note, Task (HTTP 8080)
- Cluster UI: Portainer
- Monitoring: Prometheus, Grafana, kube-state-metrics, node-exporter

All requests inside the cluster are processed by envoy and routed accordingly, and for the Task Manager services, the JWT authentication is handled solely by Envoy.

## Prerequisites
- Docker, kubectl, Helm, Minikube
- Minikube Ingress addon: `minikube addons enable ingress`

## Setup
1. Start Minikube:
   ```bash
   minikube start
   ```
2. Mount configs using `startup/mountFiles.sh`:

3. Build docker images to add to minikube vm using `startup/buildImages.sh`:

4. Add ingress services to hosts:
   ```bash
   # Use localhost with minikube tunnel
   sudo sh -c 'echo "127.0.0.1 taskmanager.local" >> /etc/hosts'
   sudo sh -c 'echo "127.0.0.1 pgadmin.taskmanager.local" >> /etc/hosts'
   sudo sh -c 'echo "127.0.0.1 portainer.taskmanager.local" >> /etc/hosts'
   sudo sh -c 'echo "127.0.0.1 grafana.taskmanager.local" >> /etc/hosts'
   ```
5. Start helm deployment using `startup/startup.sh`

6. Start tunnel with `sudo minikube tunnel`

## Access - All requests through envoy
- Task Manager Serivce: http://taskmanager.local:80
- pgAdmin: http://pgadmin.taskmanager.local:8081 (pgadmin: darius@pgadmin.com/dariuspassword - postgrespassword)
- Portainer: http://portainer.taskmanager.local:8082
- Grafana: http://grafana.taskmanager.local:8083 (admin/admin)