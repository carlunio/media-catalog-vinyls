#!/bin/bash
cd "$(dirname "$0")/.."

echo "Updating the application..."
git pull

echo "Application updated"
read -p "Press Enter to close..."
