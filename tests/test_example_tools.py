"""Tests for the example tools."""

from __future__ import annotations

import random
import urllib.error
from unittest.mock import MagicMock, patch

from agent_loop.tools.example_tools import (
    calculate,
    create_default_registry,
    get_current_time,
    get_weather,
    read_url,
    search_web,
)


class TestCalculate:
    def test_basic_arithmetic(self):
        r = calculate("2 + 2 * 3")
        assert r.status == "success"
        assert r.data == {"expression": "2 + 2 * 3", "result": 8}

    def test_allowed_builtins(self):
        r = calculate("abs(-7)")
        assert r.status == "success"
        assert r.data["result"] == 7

    def test_restricted_builtins(self):
        r = calculate("__import__('os').system('echo x')")
        assert r.status == "error"

    def test_syntax_error(self):
        r = calculate("2 +")
        assert r.status == "error"


class TestSearchWeb:
    def test_returns_three_results(self):
        r = search_web("fast cars")
        assert r.status == "success"
        assert len(r.data["results"]) == 3

    def test_url_safety(self):
        r = search_web('he said "hi" to me')
        for entry in r.data["results"]:
            assert " " not in entry["url"]
            assert '"' not in entry["url"]
            assert "'" not in entry["url"]

    def test_message_contains_all_urls(self):
        r = search_web("pune")
        for entry in r.data["results"]:
            assert entry["url"] in r.message


class TestGetWeather:
    def test_success_shape(self):
        random.seed(0)
        r = get_weather("Mumbai")
        assert r.status == "success"
        assert set(r.data.keys()) == {"location", "temperature", "humidity", "condition"}
        assert r.data["location"] == "Mumbai"

    def test_ranges(self):
        for _ in range(20):
            r = get_weather("X")
            assert 15 <= r.data["temperature"] <= 35
            assert 30 <= r.data["humidity"] <= 80


class TestGetCurrentTime:
    def test_default_timezone(self):
        r = get_current_time()
        assert r.status == "success"
        assert r.data["timezone"] == "UTC"
        assert "time" in r.data

    def test_custom_timezone(self):
        r = get_current_time("IST")
        assert r.data["timezone"] == "IST"


class TestReadUrl:
    def test_example_com_returns_mock(self):
        r = read_url("https://example.com/wiki/Hinjawadi")
        assert r.status == "success"
        assert "Hinjawadi" in r.data["content"]
        assert r.data["url"] == "https://example.com/wiki/Hinjawadi"

    def test_http_error(self):
        err = urllib.error.HTTPError(
            url="https://real.example.org/",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            r = read_url("https://real.example.org/")
        assert r.status == "error"
        assert "403" in r.message

    def test_url_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("nope"),
        ):
            r = read_url("https://real.example.org/")
        assert r.status == "error"
        assert "URL Error" in r.message

    def test_html_extraction_and_truncation(self):
        html = (
            "<html><head><style>x</style><script>y</script></head>"
            "<body><p>Hello</p><p>" + ("word " * 600) + "</p></body></html>"
        )
        fake_response = MagicMock()
        fake_response.read.return_value = html.encode("utf-8")
        fake_response.__enter__.return_value = fake_response
        fake_response.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=fake_response):
            r = read_url("https://real.example.org/page")

        assert r.status == "success"
        assert "Hello" in r.data["content"]
        assert "x" not in r.data["content"].split()  # style content skipped
        assert "y" not in r.data["content"].split()  # script content skipped
        assert r.data["content"].endswith("[truncated]")


class TestCreateDefaultRegistry:
    def test_registers_expected_tools(self):
        reg = create_default_registry()
        assert set(reg.list_tools()) == {
            "search_web",
            "read_url",
            "calculate",
            "get_weather",
            "get_current_time",
        }
