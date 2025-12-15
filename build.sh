#!/bin/bash
set -o errexit

echo "Installing Python dependencies..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt