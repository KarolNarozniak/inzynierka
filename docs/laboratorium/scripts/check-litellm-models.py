#!/usr/bin/env python3
"""Check LiteLLM proxy authentication and list model aliases without secrets."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


env = dotenv_values("/opt/lab/litellm/.env")
key = env.get("LITELLM_MASTER_KEY")
if not key:
    print("LITELLM_MASTER_KEY: missing")
    raise SystemExit(2)

request = Request(
    "http://10.10.20.10:4000/v1/models",
    headers={"Authorization": f"Bearer {key}"},
)

try:
    with urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
        print(f"LiteLLM /v1/models: HTTP {response.status}")
        for model in result.get("data", []):
            print(f"model alias: {model.get('id', 'unknown')}")
except HTTPError as error:
    print(f"LiteLLM /v1/models: HTTP {error.code}")
    raise SystemExit(1)
except (TimeoutError, URLError) as error:
    print(f"LiteLLM proxy check failed: {type(error).__name__}")
    raise SystemExit(3)
