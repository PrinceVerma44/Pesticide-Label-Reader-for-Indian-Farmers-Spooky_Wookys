import base64
import json
import os
import urllib.error
import urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _post(path, payload, timeout=600):
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

    def chat(self, prompt, images=None, **kwargs):
        return chat(prompt, images=images, **kwargs)


def get_client():
    return LocalClient()
