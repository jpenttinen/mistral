import time
from email.utils import format_datetime
from datetime import datetime, timezone

import pytest

import mistralai.workflows as workflows
from mistralai.workflows import testing
from worker.workflows.morning_report import (
    MorningReportInput,
    MorningReportWorkflow,
    build_report_prompt,
    parse_feed,
    parse_weather_payload,
    weather_code_to_fi,
)
from conftest import TEST_TASK_QUEUE


def test_weather_code_known_and_unknown():
    assert weather_code_to_fi(0) == "selkeää"
    assert weather_code_to_fi(95) == "ukkosta"
    assert "koodi 999" in weather_code_to_fi(999)
    assert "koodi" in weather_code_to_fi(None)


def test_parse_weather_payload():
    payload = {
        "current": {
            "time": "2026-11-14T05:00",
            "temperature_2m": -3.5,
            "relative_humidity_2m": 87,
            "apparent_temperature": -7.1,
            "precipitation": 0.0,
            "weather_code": 71,
            "wind_speed_10m": 12.5,
            "wind_direction_10m": 180,
            "pressure_msl": 1002.4,
        },
        "hourly": {
            "time": ["2026-11-14T04:00", "2026-11-14T05:00", "2026-11-14T06:00"],
            "temperature_2m": [-4.0, -3.5, -3.0],
            "precipitation_probability": [10, 20, 30],
            "weather_code": [71, 71, 3],
            "wind_speed_10m": [11.0, 12.5, 13.0],
        },
    }
    result = parse_weather_payload(payload)
    assert result["location"] == "Kuopio, Suomi"
    assert result["current"]["temperature_c"] == -3.5
    assert result["current"]["weather"] == "kevyttä lumisadetta"
    assert len(result["next_12h"]) == 2
    assert result["next_12h"][0]["time"] == "2026-11-14T05:00"
    assert result["next_12h"][1]["weather"] == "pilvistä"


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test feed</title>
    <item>
      <title>Tuore uutinen &amp; lisää</title>
      <link>https://example.com/new</link>
      <pubDate>{new_date}</pubDate>
      <description>&lt;p&gt;Tuore juttu.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Vanha uutinen</title>
      <link>https://example.com/old</link>
      <pubDate>{old_date}</pubDate>
      <description>Vanha juttu.</description>
    </item>
  </channel>
</rss>
"""


def _rss(content_date_new: datetime, content_date_old: datetime) -> bytes:
    return SAMPLE_RSS.format(
        new_date=format_datetime(content_date_new), old_date=format_datetime(content_date_old)
    ).encode()


def test_parse_feed_filters_by_cutoff_and_cleans_html():
    now = datetime.now(timezone.utc)
    old = datetime.fromtimestamp(now.timestamp() - 48 * 3600, tz=timezone.utc)
    content = _rss(now, old)
    cutoff = time.time() - 12 * 3600
    items = parse_feed(content, "Test Source", cutoff)
    assert len(items) == 1
    item = items[0]
    assert item["source"] == "Test Source"
    assert item["title"] == "Tuore uutinen & lisää"
    assert item["link"] == "https://example.com/new"
    assert item["summary"] == "Tuore juttu."
    assert item["published_ts"] > cutoff


def test_parse_feed_skips_items_without_timestamp():
    rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
    <item><title>Ei päivää</title><link>https://example.com/x</link></item>
    </channel></rss>""".encode()
    assert parse_feed(rss, "S", time.time() - 3600) == []


def test_build_report_prompt_contains_sections():
    weather = {"location": "Kuopio, Suomi", "current": {}, "next_12h": []}
    news = [{"source": "AP", "title": "Juttu", "link": "https://x", "published": "p", "summary": "s"}]
    prompt = build_report_prompt(weather, news, 12, "14.11.2026 05:00")
    assert "Kuopion sää" in prompt
    assert "USA:n uutiset" in prompt
    assert "AP: Juttu" in prompt


def test_workflow_is_discoverable():
    classes = workflows.discover_all_workflows_in_package("worker.workflows")
    names = {getattr(c, "__workflows_workflow_def").name for c in classes}
    assert "morning-report" in names


@workflows.activity(name="fetch_kuopio_weather")
async def stub_weather() -> dict:
    return {"location": "Kuopio, Suomi", "current": {"temperature_c": 1.0}, "next_12h": []}


@workflows.activity(name="fetch_recent_us_news")
async def stub_news(hours: int, max_items: int) -> list[dict]:
    assert hours == 12
    return [
        {"source": "Test", "title": "Uutinen", "link": "https://example.com", "published": "p", "summary": "s"}
    ]


@workflows.activity(name="compose_report")
async def stub_compose(weather: dict, news: list[dict], hours: int) -> str:
    return f"RAPORTTI: {weather['location']}, uutisia={len(news)}, tuntia={hours}"


@pytest.mark.asyncio
async def test_workflow_end_to_end_with_stubbed_activities(temporal_env):
    async with testing.create_test_worker(
        temporal_env,
        [MorningReportWorkflow],
        activities=[stub_weather, stub_news, stub_compose],
        task_queue=TEST_TASK_QUEUE,
    ):
        handle = await temporal_env.client.start_workflow(
            "morning-report",
            MorningReportInput(hours=12, max_news_items=5),
            id="test-morning-report",
            task_queue=TEST_TASK_QUEUE,
        )
        result = await handle.result()
    assert result["result"] == "RAPORTTI: Kuopio, Suomi, uutisia=1, tuntia=12"
