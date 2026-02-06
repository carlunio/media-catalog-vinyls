#!/bin/bash
cd "$(dirname "$0")/.."

echo "Launching the application..."
make dev

echo "Application started"
read -p "Press Enter to close..."
