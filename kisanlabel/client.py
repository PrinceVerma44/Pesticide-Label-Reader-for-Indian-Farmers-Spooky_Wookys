import os

# Gemma 4 models served through the Gemini API. Override with the GEMMA_MODEL env var.
# Options listed in Google's docs: gemma-4-26b-a4b-it (lighter), gemma-4-31b-it (bigger).
MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")


def get_client():
    """Create a Gemini API client. The SDK is imported lazily so tests run without it."""
    from google import genai

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "(free from Google AI Studio)."
        )
    return genai.Client(api_key=key)
