import calendar
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pydantic

import mistralai.workflows as workflows
from mistralai.workflows import Depends
from mistralai.workflows.client import get_mistral_client

KUOPIO_LATITUDE = 62.8924
KUOPIO_LONGITUDE = 27.6770
HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={KUOPIO_LATITUDE}&longitude={KUOPIO_LONGITUDE}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
    "weather_code,wind_speed_10m,wind_direction_10m,pressure_msl"
    "&hourly=temperature_2m,precipitation_probability,weather_code,wind_speed_10m"
    "&forecast_days=2&timezone=Europe%2FHelsinki"
)

NEWS_FEEDS = [
    ("New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/US.xml"),
    ("Washington Post", "https://feeds.washingtonpost.com/rss/politics"),
    ("ABC News", "https://feeds.abcnews.com/abcnews/topstories"),
    ("CBS News", "https://www.cbsnews.com/latest/rss/main"),
    ("BBC US & Canada", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("The Guardian US", "https://www.theguardian.com/us-news/rss"),
    ("AP News", "https://apnews.com/apf-topnews/rss"),
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("CNN", "https://rss.cnn.com/rss/cnn_topstories.rss"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
]

WMO_WEATHER_CODES_FI = {
    0: "selkeää",
    1: "melko selkeää",
    2: "puolipilvistä",
    3: "pilvistä",
    45: "sumua",
    48: "jäätävää sumua",
    51: "kevyttä tihkusadetta",
    53: "tihkusadetta",
    55: "voimakasta tihkusadetta",
    56: "kevyttä jäätävää tihkua",
    57: "jäätävää tihkua",
    61: "kevyttä sadetta",
    63: "sadetta",
    65: "rankkasadetta",
    66: "kevyttä jäätävää sadetta",
    67: "jäätävää sadetta",
    71: "kevyttä lumisadetta",
    73: "lumisadetta",
    75: "voimakasta lumisadetta",
    77: "lumijyväsiä",
    80: "kevyitä sadekuuroja",
    81: "sadekuuroja",
    82: "rajuja sadekuuroja",
    85: "lumikuuroja",
    86: "voimakkaita lumikuuroja",
    95: "ukkosta",
    96: "ukkosta ja kevyitä rakeita",
    99: "ukkosta ja rakeita",
}

_TAG_RE = re.compile(r"<[^>]+>")


def weather_code_to_fi(code: Any) -> str:
    try:
        return WMO_WEATHER_CODES_FI.get(int(code), f"tuntematon säätyyppi (koodi {code})")
    except (TypeError, ValueError):
        return f"tuntematon säätyyppi (koodi {code})"


def parse_weather_payload(payload: dict) -> dict:
    current = payload["current"]
    hourly = payload["hourly"]
    times = hourly["time"]
    start = next((i for i, t in enumerate(times) if t >= current["time"]), 0)
    next_hours = []
    for i in range(start, min(start + 12, len(times))):
        next_hours.append(
            {
                "time": times[i],
                "temperature_c": hourly["temperature_2m"][i],
                "precipitation_probability": hourly["precipitation_probability"][i],
                "weather": weather_code_to_fi(hourly["weather_code"][i]),
                "wind_kmh": hourly["wind_speed_10m"][i],
            }
        )
    return {
        "location": "Kuopio, Suomi",
        "observed_at": current["time"],
        "current": {
            "temperature_c": current["temperature_2m"],
            "feels_like_c": current["apparent_temperature"],
            "humidity_pct": current["relative_humidity_2m"],
            "precipitation_mm": current["precipitation"],
            "weather": weather_code_to_fi(current["weather_code"]),
            "wind_kmh": current["wind_speed_10m"],
            "wind_direction_deg": current["wind_direction_10m"],
            "pressure_hpa": current["pressure_msl"],
        },
        "next_12h": next_hours,
    }


def _clean_text(text: Any) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", str(text)))).strip()


def entry_timestamp(entry: Any) -> float | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return calendar.timegm(value)
    return None


def parse_feed(content: bytes, source: str, cutoff_ts: float, max_summary_chars: int = 300) -> list[dict]:
    import feedparser

    feed = feedparser.parse(content)
    items = []
    for entry in feed.entries:
        ts = entry_timestamp(entry)
        if ts is None or ts < cutoff_ts:
            continue
        items.append(
            {
                "source": source,
                "title": _clean_text(entry.get("title", "")),
                "link": entry.get("link", ""),
                "published": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "published_ts": ts,
                "summary": _clean_text(entry.get("summary", ""))[:max_summary_chars],
            }
        )
    return items


SYSTEM_PROMPT = (
    "Olet ammattitaitoinen uutistoimittaja. Laadit joka aamu suomenkielisen aamuraportin. "
    "Kirjoita selkeästi ja ytimekkäästi Markdown-muodossa. Älä keksi sisältöä, käytä vain annettuja tietoja."
)


def build_report_prompt(weather: dict, news: list[dict], hours: int, now_local: str) -> str:
    lines = [f"Raportin ajankohta: {now_local} (Suomen aika).", ""]
    lines.append("## Kuopion sää (raakatiedot)")
    lines.append(json.dumps(weather, ensure_ascii=False, indent=2))
    lines.append("")
    lines.append(f"## USA:n uutiset viimeisten {hours} tunnin ajalta (tuorein ensin)")
    for item in news:
        lines.append(f"- {item['source']}: {item['title']} ({item['published']}) {item['link']}")
        if item["summary"]:
            lines.append(f"  {item['summary']}")
    lines.append("")
    lines.append(
        "Tee yllä olevista tiedoista aamuraportti suomeksi. Rakenne: "
        "1) otsikko päivämäärällä, 2) Kuopion sää lyhyesti (nykyhetki ja lähituntien näkymä), "
        f"3) USA:n tärkeimmät tapahtumat viimeisten {hours} tunnin ajalta, valitse olennaisimmat "
        "(enintään 8 kohtaa) ja anna kullekin lyhyt yhteenveto lähteineen, "
        "4) lopuksi lyhyt 'Mitä seurata tänään' -lista."
    )
    return "\n".join(lines)


@workflows.activity(
    start_to_close_timeout=timedelta(seconds=60),
    retry_policy_max_attempts=3,
    retry_policy_backoff_coefficient=2.0,
)
async def fetch_kuopio_weather() -> dict:
    import httpx

    async with httpx.AsyncClient(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": "morning-report-worker/0.1"}
    ) as client:
        response = await client.get(OPEN_METEO_URL)
        response.raise_for_status()
    return parse_weather_payload(response.json())


@workflows.activity(
    start_to_close_timeout=timedelta(seconds=120),
    retry_policy_max_attempts=3,
    retry_policy_backoff_coefficient=2.0,
)
async def fetch_recent_us_news(hours: int, max_items: int) -> list[dict]:
    import httpx

    cutoff_ts = time.time() - hours * 3600
    collected: list[dict] = []
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; morning-report-worker/0.1)"},
    ) as client:
        for source, url in NEWS_FEEDS:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            collected.extend(parse_feed(response.content, source, cutoff_ts))
    if not collected:
        raise RuntimeError(f"No US news items found from the last {hours} hours across {len(NEWS_FEEDS)} feeds")
    collected.sort(key=lambda item: item["published_ts"], reverse=True)
    return [{k: v for k, v in item.items() if k != "published_ts"} for item in collected[:max_items]]


@workflows.activity(
    start_to_close_timeout=timedelta(minutes=3),
    retry_policy_max_attempts=3,
    retry_policy_backoff_coefficient=2.0,
)
async def compose_report(weather: dict, news: list[dict], hours: int, client=Depends(get_mistral_client)) -> str:
    now_local = datetime.now(HELSINKI_TZ).strftime("%d.%m.%Y %H:%M")
    response = await client.chat.complete_async(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_report_prompt(weather, news, hours, now_local)},
        ],
    )
    return response.choices[0].message.content


class MorningReportInput(pydantic.BaseModel):
    hours: int = 12
    max_news_items: int = 25


@workflows.workflow.define(
    name="morning-report",
    workflow_display_name="Aamuraportti (Kuopio + USA)",
    workflow_description="Kuopion säätila ja USA:n tärkeimmät tapahtumat edellisten 12 tunnin ajalta suomeksi.",
)
class MorningReportWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: MorningReportInput) -> str:
        weather = await fetch_kuopio_weather()
        news = await fetch_recent_us_news(input.hours, input.max_news_items)
        return await compose_report(weather, news, input.hours)
