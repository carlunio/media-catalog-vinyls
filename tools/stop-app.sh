#!/bin/bash
cd "$(dirname "$0")/.."

echo "Stopping the application..."
make stop

echo "Application stopped"
read -p "Press Enter to close..."
