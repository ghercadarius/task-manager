#!/bin/bash
set -e

echo "Updating helm repositories..."
cd ../helm || exit 1
helm repo update

echo "Installing/upgrading Helm charts..."
helm upgrade --install task-manager . -n default

echo "Helm charts installed/upgraded successfully."