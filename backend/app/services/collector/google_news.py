"""Google News RSS collector for multilingual event discovery."""

from __future__ import annotations

from urllib.parse import quote_plus, urlparse

import feedparser
import httpx

from app.config import settings
from app.schemas.article import RawArticle
from app.services.collector.rss_collector import RSSCollector


class GoogleNewsCollector:
    """Collect and search Google News RSS editions across languages."""

    REGION_FEEDS = {
        "en-US": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "en-GB": "https://news.google.com/rss?hl=en-GB&gl=GB&ceid=GB:en",
        "en-CA": "https://news.google.com/rss?hl=en-CA&gl=CA&ceid=CA:en",
        "en-AU": "https://news.google.com/rss?hl=en-AU&gl=AU&ceid=AU:en",
        "en-IN": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "en-NG": "https://news.google.com/rss?hl=en-NG&gl=NG&ceid=NG:en",
        "en-ZA": "https://news.google.com/rss?hl=en-ZA&gl=ZA&ceid=ZA:en",
        "en-KE": "https://news.google.com/rss?hl=en-KE&gl=KE&ceid=KE:en",
        "en-SG": "https://news.google.com/rss?hl=en-SG&gl=SG&ceid=SG:en",
        "ar": "https://news.google.com/rss?hl=ar&gl=EG&ceid=EG:ar",
        "ar-SA": "https://news.google.com/rss?hl=ar&gl=SA&ceid=SA:ar",
        "ar-AE": "https://news.google.com/rss?hl=ar&gl=AE&ceid=AE:ar",
        "ar-MA": "https://news.google.com/rss?hl=ar&gl=MA&ceid=MA:ar",
        "ar-LB": "https://news.google.com/rss?hl=ar&gl=LB&ceid=LB:ar",
        "ar-JO": "https://news.google.com/rss?hl=ar&gl=JO&ceid=JO:ar",
        "zh-CN": "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "zh-TW": "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "zh-HK": "https://news.google.com/rss?hl=zh-HK&gl=HK&ceid=HK:zh-Hant",
        "ja": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja",
        "hi": "https://news.google.com/rss?hl=hi&gl=IN&ceid=IN:hi",
        "bn-BD": "https://news.google.com/rss?hl=bn&gl=BD&ceid=BD:bn",
        "ta-IN": "https://news.google.com/rss?hl=ta&gl=IN&ceid=IN:ta",
        "te-IN": "https://news.google.com/rss?hl=te&gl=IN&ceid=IN:te",
        "ur-PK": "https://news.google.com/rss?hl=ur&gl=PK&ceid=PK:ur",
        "pt-BR": "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "pt-PT": "https://news.google.com/rss?hl=pt-PT&gl=PT&ceid=PT:pt-150",
        "tr": "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr",
        "fr": "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr",
        "fr-CA": "https://news.google.com/rss?hl=fr-CA&gl=CA&ceid=CA:fr",
        "fr-BE": "https://news.google.com/rss?hl=fr&gl=BE&ceid=BE:fr",
        "fr-SN": "https://news.google.com/rss?hl=fr&gl=SN&ceid=SN:fr",
        "de": "https://news.google.com/rss?hl=de&gl=DE&ceid=DE:de",
        "de-AT": "https://news.google.com/rss?hl=de&gl=AT&ceid=AT:de",
        "de-CH": "https://news.google.com/rss?hl=de&gl=CH&ceid=CH:de",
        "es": "https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es",
        "es-MX": "https://news.google.com/rss?hl=es-419&gl=MX&ceid=MX:es-419",
        "es-AR": "https://news.google.com/rss?hl=es-419&gl=AR&ceid=AR:es-419",
        "es-CL": "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419",
        "es-CO": "https://news.google.com/rss?hl=es-419&gl=CO&ceid=CO:es-419",
        "es-PE": "https://news.google.com/rss?hl=es-419&gl=PE&ceid=PE:es-419",
        "es-VE": "https://news.google.com/rss?hl=es-419&gl=VE&ceid=VE:es-419",
        "ru": "https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru",
        "ru-KZ": "https://news.google.com/rss?hl=ru&gl=KZ&ceid=KZ:ru",
        "uk-UA": "https://news.google.com/rss?hl=uk&gl=UA&ceid=UA:uk",
        "ko": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
        "sw": "https://news.google.com/rss?hl=sw&gl=KE&ceid=KE:sw",
        "it-IT": "https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it",
        "nl-NL": "https://news.google.com/rss?hl=nl&gl=NL&ceid=NL:nl",
        "nl-BE": "https://news.google.com/rss?hl=nl&gl=BE&ceid=BE:nl",
        "pl-PL": "https://news.google.com/rss?hl=pl&gl=PL&ceid=PL:pl",
        "cs-CZ": "https://news.google.com/rss?hl=cs&gl=CZ&ceid=CZ:cs",
        "sk-SK": "https://news.google.com/rss?hl=sk&gl=SK&ceid=SK:sk",
        "hu-HU": "https://news.google.com/rss?hl=hu&gl=HU&ceid=HU:hu",
        "ro-RO": "https://news.google.com/rss?hl=ro&gl=RO&ceid=RO:ro",
        "el-GR": "https://news.google.com/rss?hl=el&gl=GR&ceid=GR:el",
        "bg-BG": "https://news.google.com/rss?hl=bg&gl=BG&ceid=BG:bg",
        "sv-SE": "https://news.google.com/rss?hl=sv&gl=SE&ceid=SE:sv",
        "no-NO": "https://news.google.com/rss?hl=no&gl=NO&ceid=NO:no",
        "da-DK": "https://news.google.com/rss?hl=da&gl=DK&ceid=DK:da",
        "fi-FI": "https://news.google.com/rss?hl=fi&gl=FI&ceid=FI:fi",
        "he-IL": "https://news.google.com/rss?hl=he&gl=IL&ceid=IL:he",
        "fa-IR": "https://news.google.com/rss?hl=fa&gl=IR&ceid=IR:fa",
        "id-ID": "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id",
        "ms-MY": "https://news.google.com/rss?hl=ms&gl=MY&ceid=MY:ms",
        "th-TH": "https://news.google.com/rss?hl=th&gl=TH&ceid=TH:th",
        "vi-VN": "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi",
        "fil-PH": "https://news.google.com/rss?hl=fil&gl=PH&ceid=PH:fil",
    }

    async def search_event(self, query: str, language: str) -> list[RawArticle]:
        """Search Google News RSS by query and language."""
        feed = self.feed_for_language(language)
        url = feed.replace("/rss?", f"/rss/search?q={quote_plus(query)}&")
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthPuzzle/0.1"})
            response.raise_for_status()
        parsed = feedparser.parse(response.content)
        parser = RSSCollector()
        articles = []
        for entry in parsed.entries:
            link = await self.resolve_google_link(getattr(entry, "link", ""))
            articles.append(
                RawArticle(
                    external_url=link,
                    title_original=getattr(entry, "title", "Untitled"),
                    content_original=getattr(entry, "summary", ""),
                    language=language,
                    published_at=parser._parse_date(getattr(entry, "published", None)),
                    metadata={"google_news": True},
                )
            )
        return articles

    @classmethod
    def feed_for_language(cls, language: str) -> str:
        """Return an exact or base-language Google News edition, defaulting to en-US."""
        if language in cls.REGION_FEEDS:
            return cls.REGION_FEEDS[language]
        prefix = f"{language.split('-')[0]}-"
        for key, feed in cls.REGION_FEEDS.items():
            if key.startswith(prefix):
                return feed
        return cls.REGION_FEEDS["en-US"]

    async def discover_sources(self, articles: list[RawArticle]) -> list[dict]:
        """Return unique domains for human review as candidate sources."""
        seen: set[str] = set()
        candidates: list[dict] = []
        for article in articles:
            domain = urlparse(article.external_url).netloc.replace("www.", "")
            if domain and domain not in seen:
                seen.add(domain)
                candidates.append({"domain": domain, "language": article.language, "status": "pending_review"})
        return candidates

    async def resolve_google_link(self, url: str) -> str:
        """Resolve Google News redirect URLs to their final target when possible."""
        if "news.google.com" not in url:
            return url
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthPuzzle/0.1"})
            return str(response.url)
