#!/usr/bin/env bash
set -euo pipefail

curl --noproxy '*' http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Show the routing decision for this request."
      }
    ],
    "policy": "balanced",
    "debug": true
  }'

