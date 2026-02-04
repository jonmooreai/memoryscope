#!/bin/bash

# Set Firebase Service Account JSON from file
FIREBASE_JSON_FILE="/Users/jonmoore/Downloads/scoped-memory-7c9f9-firebase-adminsdk-fbsvc-03bbb965be.json"

if [ ! -f "$FIREBASE_JSON_FILE" ]; then
    echo "❌ Firebase JSON file not found at: $FIREBASE_JSON_FILE"
    exit 1
fi

# Use Python to properly escape the JSON
export FIREBASE_SERVICE_ACCOUNT_JSON=$(python3 -c "
import json
import sys
with open('$FIREBASE_JSON_FILE', 'r') as f:
    data = json.load(f)
    print(json.dumps(data))
")

echo "✅ FIREBASE_SERVICE_ACCOUNT_JSON set from file"
echo "   Project ID: scoped-memory-7c9f9"
echo "   Client Email: firebase-adminsdk-fbsvc@scoped-memory-7c9f9.iam.gserviceaccount.com"

