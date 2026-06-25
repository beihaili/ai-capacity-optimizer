#!/usr/bin/env bash
set -euo pipefail

curl --noproxy '*' http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Summarize my AI capacity risk through one API."
      }
    ],
    "policy": "balanced"
  }'

