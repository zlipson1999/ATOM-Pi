"""
ATOM-Pi Visual Reasoning (EYES, comprehension side)
====================================================
"What do you see?" -> capture a frame -> Moondream (via Ollama)
answers in sentences. Hailo keeps doing real-time detection
separately; this module is scene UNDERSTANDING, not detection.

VERIFIED AGAINST REAL CODE (pocket-ai camera_stream.py):
  * POST /camera/capture returns {"status":"success","filename":...}
  * captured files are served at /captures/<filename>
  * POST /camera/start is safe to call if already running

Registered as a tool by patches/apply_patches.py, which appends a
run_describe_scene() runner to tool_ai.py's TOOL_RUNNERS registry.

Standalone test (backend running, camera connected):
    python vision_describe.py "What do you see?"
"""

import base64
import os
import sys

import requests

BACKEND = os.environ.get("ATOM_BACKEND", "http://localhost:8000")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_QUESTION = "Describe what you see in one or two sentences."
MAX_QUESTION_CHARS = 1000


def _capture_b64() -> str:
    try:
        requests.post(f"{BACKEND}/camera/start", timeout=5)
    except requests.RequestException:
        pass
    r = requests.post(f"{BACKEND}/camera/capture", timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "capture failed"))
    img = requests.get(f"{BACKEND}/captures/{data['filename']}", timeout=10)
    img.raise_for_status()
    return base64.b64encode(img.content).decode()


def describe_scene(question: str = "") -> str:
    question = ((question or "").strip() or DEFAULT_QUESTION)[:MAX_QUESTION_CHARS]
    try:
        image_b64 = _capture_b64()
    except Exception:
        return "I couldn't get a picture from my camera."
    try:
        resp = requests.post(
            OLLAMA,
            json={
                "model": "moondream",
                "prompt": question,
                "images": [image_b64],
                "stream": False,
            },
            timeout=120,
        )  # first call loads the model
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()
        return answer or "I looked, but I couldn't put it into words."
    except requests.ConnectionError:
        return "My vision model isn't running. Start it with: sudo systemctl start ollama"
    except requests.Timeout:
        return "My vision model took too long — try asking again."
    except Exception:
        # Anything else — an HTTP error, malformed JSON — must still come back
        # as a sentence. This runs inside a tool runner; an exception escaping
        # here surfaces as a broken tool call rather than an answer.
        return "My vision model returned an unreadable response."


if __name__ == "__main__":
    print(describe_scene(" ".join(sys.argv[1:])))
