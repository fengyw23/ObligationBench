#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


method, route, token_file, expected, body_file = sys.argv[1:6]
token = Path(token_file).read_text().strip()
data = None if body_file == '-' else Path(body_file).read_bytes()
request = urllib.request.Request(
    'http://127.0.0.1:18116' + route,
    data=data,
    method=method,
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
)
try:
    response = urllib.request.urlopen(request, timeout=5)
    status = response.status
    content = response.read()
except urllib.error.HTTPError as error:
    status = error.code
    content = error.read()

if status != int(expected):
    raise SystemExit(f'unexpected HTTP status {status}, wanted {expected}: {content.decode()}')

print(f'token_api method={method} route={route} status={status}')
if content:
    payload = json.loads(content)
    for key in sorted(payload):
        print(f'{key}={payload[key]}')
