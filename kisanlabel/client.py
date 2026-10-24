"""Local Gemma client for KisanLabel — NO Gemini API, NO API key.

Runs the open-weights Gemma model locally via Ollama on the same machine
that runs Streamlit. This is the file the judges asked for: the model
weights live on the laptop, inference happens on the laptop, and the app
works offline once the model has been pulled once.

Setup (once, on the demo laptop, in Terminal):
    ollama pull gemma3:4b

    # gemma3:4b is the multimodal Gemma 3 model: it can SEE the label
    # photo. A text-only model cannot do the extract step.
    # On an Apple Silicon Mac with ~12 GB GPU memory, 4b is the safe
    # demo choice. 12b is slower and risks running out of memory
    # mid-demo; do not switch to it on demo night.

Override with env vars if needed:
    OLLAMA_MODEL=gemma3:4b
    OLLAMA_HOST=http://localhost:11434
"""

import base64
import json
import os
import urllib.error
import urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _post(path, payload, timeout=600):
    """POST one JSON request to Ollama and return the parsed JSON reply."""
    url = f"{OLLAMA_HOST}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        if e.code == 404 and "model" in body.lower():
            raise RuntimeError(
                f"Local model '{MODEL}' is not pulled yet. "
                f"Run this in Terminal, then restart Streamlit:\n"
                f"    ollama pull {MODEL}"
            ) from e
        raise RuntimeError(f"Ollama returned HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach Ollama at "
            f"{OLLAMA_HOST}. Open the Ollama app (or run `ollama serve` "
            "in Terminal) and check http://localhost:11434 in a browser — "
            'it should say "Ollama is running".'
        ) from e


def chat(prompt, images=None, temperature=0.0, num_predict=1024):
    """One non-streaming Ollama chat call. images = list of raw bytes."""
    message = {"role": "user", "content": prompt}
    if images:
        message["images"] = [base64.b64encode(b).decode("ascii") for b in images]
    reply = _post(
        "/api/chat",
        {
            "model": MODEL,
            "messages": [message],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        },
    )
    text = (reply.get("message") or {}).get("content", "")
    if not text.strip():
        raise RuntimeError(f"Local Gemma model '{MODEL}' returned an empty reply.")
    return text


class LocalClient:
    """Tiny compatibility shim.

    The old code called get_client().models.generate_content(...).
    The new extract/explain code calls chat() directly, but ui.py still
    calls get_client() and holds the result in session state, so this
    keeps that call working — with no API key and no network call.
    """

    def chat(self, prompt, images=None, **kwargs):
        return chat(prompt, images=images, **kwargs)


def get_client():
    return LocalClient()
