"""Minimal, instrumented Ollama client (standard library only).

Every call records latency, token counts and the raw model text. Nothing here ever fabricates an
answer: a failed or invalid call is returned as such and the caller decides the (labelled) fallback.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class LLMCall:
    purpose: str
    agent: str
    ok: bool
    data: dict[str, Any] | None
    raw: str
    error: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cached: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OllamaClient:
    model: str = "qwen2.5:3b"
    endpoint: str = "http://localhost:11434"
    timeout: float = 90.0
    temperature: float = 0.0
    seed: int = 7
    constrained: bool = True   # JSON-schema constrained decoding (option IDs as an enum)
    cache_path: str | None = None
    think: bool | None = None  # for reasoning models (e.g. qwen3); None = do not send the flag
    _cache: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.cache_path and Path(self.cache_path).exists():
            for line in Path(self.cache_path).read_text().splitlines():
                rec = json.loads(line)
                self._cache[rec["key"]] = rec

    def config(self) -> dict[str, Any]:
        return {"model": self.model, "temperature": self.temperature, "seed": self.seed,
                "constrained_decoding": self.constrained, "think": self.think}

    def available(self) -> tuple[bool, str]:
        try:
            with urlopen(self.endpoint + "/api/tags", timeout=3) as r:
                names = [m["name"] for m in json.loads(r.read())["models"]]
            return (self.model in names, "ok" if self.model in names else f"model {self.model} not pulled")
        except (URLError, OSError) as exc:
            return False, f"Ollama unreachable: {exc}"

    def chat(self, purpose: str, agent: str, system: str, user: str, schema: dict[str, Any]) -> LLMCall:
        fmt: Any = schema if self.constrained else "json"
        body = {"model": self.model, "stream": False, "format": fmt,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": 4096,
                            "num_predict": 200}}
        if self.think is not None:
            body["think"] = self.think
        key = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        with self._lock:
            hit = self._cache.get(key)
        if hit:
            call = LLMCall(**{k: v for k, v in hit["call"].items() if k != "cached"}, cached=True)
            call.purpose, call.agent = purpose, agent
            return call
        t0 = time.perf_counter()
        raw, ptok, ctok = "", 0, 0
        try:
            req = Request(self.endpoint + "/api/chat", data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=self.timeout) as resp:
                out = json.loads(resp.read().decode())
            raw = out["message"]["content"]
            ptok, ctok = out.get("prompt_eval_count", 0), out.get("eval_count", 0)
            data = json.loads(raw)
            _check(data, schema)
            call = LLMCall(purpose, agent, True, data, raw, "", (time.perf_counter() - t0) * 1000, ptok, ctok)
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            return LLMCall(purpose, agent, False, None, raw, f"transport: {exc}",
                           (time.perf_counter() - t0) * 1000, ptok, ctok)
        except (ValueError, KeyError, TypeError) as exc:
            call = LLMCall(purpose, agent, False, None, raw, f"invalid output: {exc}",
                           (time.perf_counter() - t0) * 1000, ptok, ctok)
        if self.cache_path:  # transport errors are never cached
            with self._lock:
                self._cache[key] = {"key": key, "call": call.as_dict()}
                with open(self.cache_path, "a") as f:
                    f.write(json.dumps(self._cache[key]) + "\n")
        return call


def _check(data: Any, schema: dict[str, Any]) -> None:
    """Tiny validator for the flat object schemas used here."""
    if not isinstance(data, dict):
        raise TypeError("output is not a JSON object")
    for k in schema.get("required", []):
        if k not in data:
            raise KeyError(f"missing field '{k}'")
    for k, spec in schema.get("properties", {}).items():
        if k in data and "enum" in spec and data[k] not in spec["enum"]:
            raise ValueError(f"{k}={data[k]!r} not in {spec['enum']}")


def choice_schema(field_name: str, allowed: list[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {"reason": {"type": "string"}}
    props.update(extra or {})
    props[field_name] = {"type": "string", "enum": allowed}
    return {"type": "object", "properties": props, "required": list(props)}
