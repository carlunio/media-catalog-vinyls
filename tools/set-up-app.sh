#!/bin/bash
cd "$(dirname "$0")/.."

echo "Setting up the application..."
make setup

echo "Setup completed"
read -p "Press Enter to close..."
