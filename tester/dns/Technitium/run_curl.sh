#!/bin/bash

# Check if token is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <token>"
    exit 1
fi

TOKEN="$1"

curl -X POST -d "token=${TOKEN}&domain=test.&listZone=true" http://localhost:9001/api/zones/records/get
