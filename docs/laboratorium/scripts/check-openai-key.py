#!/usr/bin/env python3
"""Check OpenAI API-key authentication without printing the key."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


env = dotenv_values("/opt/lab/litellm/.env")
key = env.get("OPENAI_API_KEY")
if not key:
    print("OPENAI_API_KEY: missing")
    raise SystemExit(2)
if key.startswith("REPLACE_"):
    print("OPENAI_API_KEY: placeholder value")
    raise SystemExit(2)

request = Request(
    "https://api.openai.com/v1/models",
    headers={"Authorization": f"Bearer {key}"},
)

try:
    with urlopen(request, timeout=20) as response:
        print(f"OpenAI API-key authentication: HTTP {response.status}")
except HTTPError as error:
    print(f"OpenAI API-key authentication: HTTP {error.code}")
    try:
        details = json.loads(error.read().decode("utf-8"))
        provider_error = details.get("error", {})
        if provider_error.get("code"):
            print(f"Provider error code: {provider_error['code']}")
        if provider_error.get("type"):
            print(f"Provider error type: {provider_error['type']}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    raise SystemExit(1)
except (TimeoutError, URLError) as error:
    print(f"OpenAI API-key check could not reach provider: {type(error).__name__}")
    raise SystemExit(3)
