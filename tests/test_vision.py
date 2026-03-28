"""Тесты для модуля vision.py (распознавание еды через Ollama LLaVA)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from calorie_tracker.models import TrackerError
from calorie_tracker.vision import recognize_food


def _make_image(tmp_dir: str) -> Path:
    """Создаёт минимальный PNG-файл для тестов."""
    # 1x1 белый PNG (минимальный валидный файл)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    p = Path(tmp_dir) / "test.png"
    p.write_bytes(png_bytes)
    return p


def _mock_ollama_response(items: list[dict]) -> MagicMock:
    """Создаёт mock HTTP-ответа от Ollama."""
    response_body = json.dumps({"response": json.dumps(items)}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ── Unit-тесты ────────────────────────────────────────────────────────────────

def test_recognize_food_file_not_found():
    """recognize_food бросает TrackerError если файл не существует."""
    with pytest.raises(TrackerError, match="Файл не найден"):
        recognize_food("/nonexistent/path/image.jpg")


def test_recognize_food_returns_items():
    """recognize_food возвращает список блюд при успешном ответе Ollama."""
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        items = [{"name": "Овсянка", "calories": 350}, {"name": "Кофе", "calories": 80}]
        mock_resp = _mock_ollama_response(items)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = recognize_food(img)
    assert len(result) == 2
    assert result[0]["name"] == "Овсянка"
    assert result[0]["calories"] == 350
    assert result[1]["name"] == "Кофе"
    assert result[1]["calories"] == 80


def test_recognize_food_empty_response():
    """recognize_food возвращает [] если модель вернула пустой массив."""
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        mock_resp = _mock_ollama_response([])
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = recognize_food(img)
    assert result == []


def test_recognize_food_no_json_in_response():
    """recognize_food возвращает [] если ответ не содержит JSON-массива."""
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        response_body = json.dumps({"response": "Я не вижу еды на фото."}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = recognize_food(img)
    assert result == []


def test_recognize_food_ollama_unavailable():
    """recognize_food бросает TrackerError если Ollama недоступна."""
    import urllib.error
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with pytest.raises(TrackerError, match="Ollama"):
                recognize_food(img)


def test_recognize_food_filters_invalid_items():
    """recognize_food пропускает элементы без name или calories."""
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        items = [
            {"name": "Суп", "calories": 200},
            {"name": "Без калорий"},          # нет calories — пропускается
            {"calories": 100},                 # нет name — пропускается
            {"name": "Салат", "calories": 150},
        ]
        mock_resp = _mock_ollama_response(items)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = recognize_food(img)
    assert len(result) == 2
    assert result[0]["name"] == "Суп"
    assert result[1]["name"] == "Салат"


def test_recognize_food_calories_are_int():
    """recognize_food приводит calories к int."""
    with tempfile.TemporaryDirectory() as tmp:
        img = _make_image(tmp)
        # Модель может вернуть строку вместо числа
        response_body = json.dumps({"response": '[{"name": "Хлеб", "calories": "120"}]'}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = recognize_food(img)
    assert result[0]["calories"] == 120
    assert isinstance(result[0]["calories"], int)
