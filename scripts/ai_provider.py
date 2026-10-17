#!/usr/bin/env python3
"""
Multi-Provider Resilient AI Orchestrator for Spryzen & GossipMesh.
Provides seamless fallback across:
1. Google Gemini (Active 2026 models: gemini-flash-lite-latest, gemini-3.5-flash-lite, gemini-3.1-flash-lite)
2. OpenRouter (DeepSeek-V3, LLaMA-3.3 70B, Qwen-2.5 Coder)
3. NVIDIA NIM (DeepSeek-Coder 6.7B, IBM Granite 34B Code, Mistral NeMo 12B)
"""

import os
import sys
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Union

ACTIVE_GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]

DEFAULT_GEMINI_KEYS: list[str] = []

OPENROUTER_MODELS = [
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-coder-32b-instruct",
]

NVIDIA_NIM_MODELS = [
    "deepseek-ai/deepseek-v4.1-flash",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "google/codegemma-7b",
    "ibm/granite-34b-code-instruct",
]

def load_llm_keys() -> dict[str, str]:
    """Dynamically loads multi-provider API keys from .llm_keys files and env vars."""
    keys: dict[str, str] = {}

    search_dirs = [
        Path.home(),
        Path("."),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent.parent,
    ]

    for d in search_dirs:
        key_file = d / ".llm_keys"
        if key_file.exists():
            try:
                for line in key_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v and k not in keys:
                            keys[k] = v
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

    for var in ("OPENROUTER_API_KEY", "NVIDIA_API_KEY", "NVIDIA_API_KEY_2", "COHERE_API_KEY", "HUGGINGFACE_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val and var not in keys:
            keys[var] = val

    return keys

# Pre-load on import
_LOADED_KEYS = load_llm_keys()

def clean_json_response(raw_text: str) -> dict:
    """Robust JSON extraction from LLM response (strips markdown fences and finds json block)."""
    text = raw_text.strip()

    # Direct parse
    try:
        return json.loads(text, strict=False)
    except Exception:
        pass

    # Markdown fence extraction
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            try:
                return json.loads(candidate, strict=False)
            except Exception:
                pass

    # Regex search for outer JSON object
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            pass

    # If it's a list instead of dict
    match = re.search(r"(\[[\s\S]*\])", text)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            pass

    raise json.JSONDecodeError(f"Could not extract valid JSON from response: {raw_text[:200]}...", raw_text, 0)

def call_openrouter(prompt: str, system_prompt: Optional[str] = None, models: list[str] = None, max_tokens: int = 2048) -> dict:
    """Calls OpenRouter chat completions API with high-grade coding models and budget-safe token limits."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or _LOADED_KEYS.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("No OPENROUTER_API_KEY available.")

    models_to_try = models or OPENROUTER_MODELS
    last_err = None

    for model_name in models_to_try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }

        print(f"[*] [OpenRouter] Querying model '{model_name}' (max_tokens: {max_tokens})...", flush=True)
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/Aditya-9-6/spryzen",
                "X-Title": "Spryzen Autonomous Engine",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return clean_json_response(content)
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            print(f"[!] [OpenRouter] HTTP {e.code} for {model_name}: {err_msg[:160]}", file=sys.stderr, flush=True)
            last_err = err_msg
            continue
        except Exception as e:
            print(f"[!] [OpenRouter] Error for {model_name}: {e}", file=sys.stderr, flush=True)
            last_err = str(e)
            continue

    raise RuntimeError(f"All OpenRouter models failed. Last error: {last_err}")

def call_nvidia_nim(prompt: str, system_prompt: Optional[str] = None, models: list[str] = None, max_tokens: int = 2048) -> dict:
    """Calls NVIDIA NIM hosted inference endpoints with enterprise code models."""
    keys = [
        os.environ.get("NVIDIA_API_KEY", ""),
        os.environ.get("NVIDIA_API_KEY_2", ""),
        _LOADED_KEYS.get("NVIDIA_API_KEY", ""),
        _LOADED_KEYS.get("NVIDIA_API_KEY_2", "")
    ]
    keys = [k for k in keys if k]
    if not keys:
        raise ValueError("No NVIDIA_API_KEY available.")

    models_to_try = models or NVIDIA_NIM_MODELS
    last_err = None

    for active_key in keys:
        for model_name in models_to_try:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": max_tokens,
            }

            print(f"[*] [NVIDIA NIM] Querying model '{model_name}'...", flush=True)
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {active_key}",
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    return clean_json_response(content)
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="replace")
                print(f"[!] [NVIDIA NIM] HTTP {e.code} for {model_name}: {err_msg[:160]}", file=sys.stderr, flush=True)
                last_err = err_msg
                continue
            except Exception as e:
                print(f"[!] [NVIDIA NIM] Error for {model_name}: {e}", file=sys.stderr, flush=True)
                last_err = str(e)
                continue

    raise RuntimeError(f"All NVIDIA NIM models failed. Last error: {last_err}")

def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    api_keys: Union[str, list[str]] = None,
    models: list[str] = None
) -> dict:
    """Calls Gemini REST API with active 2026 models and rapid failover on 404/429."""
    if isinstance(api_keys, str):
        keys_pool = [api_keys] if api_keys else []
    elif isinstance(api_keys, list):
        keys_pool = [k for k in api_keys if k]
    else:
        keys_pool = []

    # Check environment pools
    pool_env = os.environ.get("GEMINI_KEY_POOL", "")
    for k in pool_env.split(","):
        k = k.strip()
        if k and k not in keys_pool:
            keys_pool.append(k)

    for var in ("GEMINI_API_KEY", "GEMINI_SOLVER_KEY", "GEMINI_REVIEWER_KEY", "GEMINI_ISSUE_KEY"):
        val = os.environ.get(var, "").strip()
        if val and val not in keys_pool:
            keys_pool.append(val)

    # Fallback to default verified key pool
    if not keys_pool:
        keys_pool = list(DEFAULT_GEMINI_KEYS)

    models_to_try = models or ACTIVE_GEMINI_MODELS
    last_err = None

    for active_key in keys_pool:
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={active_key}"
            parts = []
            if system_prompt:
                parts.append({"text": system_prompt})
            parts.append({"text": prompt})

            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }

            print(f"[*] [Gemini] Querying model '{current_model}' (key: ...{active_key[-6:] if len(active_key) > 6 else 'key'})...", flush=True)
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return clean_json_response(text_response)
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="replace")
                print(f"[!] [Gemini] HTTP {e.code} for {current_model}: {err_msg[:160]}", file=sys.stderr, flush=True)
                last_err = err_msg
                # If 404 or 429, don't sleep - immediately try next model/key
                continue
            except Exception as e:
                print(f"[!] [Gemini] Error for {current_model}: {e}", file=sys.stderr, flush=True)
                last_err = str(e)
                continue

    raise RuntimeError(f"All Gemini models/keys failed. Last error: {last_err}")

def call_ai_model(
    prompt: str,
    system_prompt: Optional[str] = None,
    gemini_keys: Union[str, list[str]] = None,
    gemini_models: list[str] = None,
    max_tokens: int = 2048
) -> dict:
    """
    Unified multi-provider fallback orchestrator.
    Attempts in order:
    1. Gemini Active Lite models (fastest, highest throughput)
    2. OpenRouter (DeepSeek / LLaMA, budget safe with max_tokens limit)
    3. NVIDIA NIM (DeepSeek Coder / Granite)
    """
    errors = []

    # 1. Try Gemini
    try:
        return call_gemini(
            prompt=prompt,
            system_prompt=system_prompt,
            api_keys=gemini_keys,
            models=gemini_models
        )
    except Exception as e:
        print(f"[Fallback] Gemini unavailable ({e}). Escalating to OpenRouter...", flush=True)
        errors.append(f"Gemini: {e}")

    # 2. Try OpenRouter
    try:
        return call_openrouter(prompt=prompt, system_prompt=system_prompt, max_tokens=max_tokens)
    except Exception as e:
        print(f"[Fallback] OpenRouter unavailable ({e}). Escalating to NVIDIA NIM...", flush=True)
        errors.append(f"OpenRouter: {e}")

    # 3. Try NVIDIA NIM
    try:
        return call_nvidia_nim(prompt=prompt, system_prompt=system_prompt, max_tokens=max_tokens)
    except Exception as e:
        print(f"[!] NVIDIA NIM also failed ({e}).", flush=True)
        errors.append(f"NVIDIA NIM: {e}")

    raise RuntimeError(f"All AI providers exhausted! Errors:\n" + "\n".join(errors))
