"""Распознавание еды на фото через локальную модель (Ollama или LM Studio)."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from calorie_tracker.models import TrackerError

# ── Настройки бэкенда ─────────────────────────────────────────────────────────
# Выберите один из вариантов:
#
# Ollama (по умолчанию):
#   BACKEND = "ollama"
#   API_URL  = "http://localhost:11434/api/generate"
#   MODEL    = "llava"
#
# LM Studio:
#   BACKEND = "lmstudio"
#   API_URL  = "http://localhost:1234/v1/chat/completions"
#   MODEL    = "llava"   # имя модели как в LM Studio (можно любое)

BACKEND = "lmstudio"        # "ollama" или "lmstudio"
API_URL  = "http://localhost:1234/v1/chat/completions"
MODEL    = "moondream-2b-2025-04-14-4bit"

_PROMPT = (
    "You are a nutrition assistant. Look at this food image carefully. "
    "List all food items you see with their estimated calories. "
    "Respond ONLY with a valid JSON array, no explanations:\n"
    '[{"name": "Apple", "calories": 80}, ...]\n'
    "If no food is visible, return empty array: []"
)


def _parse_items(raw_text: str) -> list[dict]:
    """Извлекает JSON-массив блюд из текста ответа модели."""
    # Убираем markdown блоки ```json ... ```
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    start = raw_text.find("[")
    end = raw_text.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        items = json.loads(raw_text[start:end])
        return [
            {
                "name": str(item.get("name", item.get("food", ""))),
                "calories": int(item.get("calories", item.get("kcal", 0)))
            }
            for item in items
            if ("name" in item or "food" in item) and ("calories" in item or "kcal" in item)
        ]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def _request_ollama(image_b64: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "prompt": _PROMPT,
        "images": [image_b64],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", "")


def _request_lmstudio(image_b64: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ],
        "max_tokens": 512,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def recognize_food(image_path: str | Path) -> list[dict]:
    """
    Отправляет фото в локальную модель и возвращает список блюд с калориями.
    Возвращает: [{"name": str, "calories": int}, ...]
    """
    path = Path(image_path)
    if not path.exists():
        raise TrackerError(f"Файл не найден: {path}")

    image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")

    try:
        if BACKEND == "lmstudio":
            raw_text = _request_lmstudio(image_b64)
        else:
            raw_text = _request_ollama(image_b64)
    except urllib.error.URLError as e:
        backend_name = "LM Studio" if BACKEND == "lmstudio" else "Ollama"
        raise TrackerError(
            f"Не удалось подключиться к {backend_name}. Убедитесь что сервер запущен: {e}"
        ) from e

    return _parse_items(raw_text)
