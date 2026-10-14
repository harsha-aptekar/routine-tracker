"""Minimal client for a local Ollama server (standard library only); prefers the largest installed model."""
import json
import urllib.error
import urllib.request

DEFAULT_HOST = "http://localhost:11434"


class OllamaError(Exception):
    """Raised with a message that is safe to show the user."""


class Ollama:
    def __init__(self, model: str = "", host: str = DEFAULT_HOST, timeout: int = 300):
        self._model, self._host, self._timeout = model, host, timeout

    def installed_models(self) -> list[str]:
        models = self._request("/api/tags", None, timeout=5)["models"]
        return [m["name"] for m in sorted(models, key=lambda m: m.get("size", 0), reverse=True)]

    def generate(self, prompt: str) -> str:
        model = self._model or next(iter(self.installed_models()), "")
        if not model:
            raise OllamaError("No Ollama model is installed yet. Run: ollama pull <model>")
        reply = self._request("/api/generate", {"model": model, "prompt": prompt, "stream": False}, timeout=self._timeout)
        return reply["response"].strip()

    def _request(self, path: str, payload: dict | None, timeout: int) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self._host + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.URLError as error:
            raise OllamaError(f"Could not reach Ollama at {self._host}. Is it running? ({error.reason})") from error
        except TimeoutError as error:
            raise OllamaError("Ollama took too long to answer. Try a smaller model.") from error
