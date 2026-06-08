"""Config-driven web scraper for sources without RSS feeds."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from scrapy import Selector
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.source import Source
from app.schemas.article import RawArticle


class WebScraper:
    """Scrape list and article pages according to per-source CSS selectors."""

    USER_AGENTS = [
        "TruthPuzzle/0.1 (+https://truthpuzzle.local)",
        "Mozilla/5.0 (compatible; TruthPuzzleBot/0.1; +https://truthpuzzle.local)",
    ]

    async def scrape_source(self, source: Source) -> list[RawArticle]:
        config = source.scraper_config or {}
        list_url = config.get("list_url")
        if not list_url:
            return []
        list_urls = await self._list_pages(list_url, config)
        links: list[str] = []
        for page_url in list_urls:
            requires_js = bool(config.get("requires_js"))
            html = await self._fetch_page(page_url, requires_js=requires_js)
            if requires_js:
                soup = BeautifulSoup(html, "html.parser")
                links.extend(
                    urljoin(page_url, node.get("href", ""))
                    for node in soup.select(config.get("article_selector", "a"))
                    if node.get("href")
                )
            else:
                selector = Selector(text=html)
                links.extend(
                    urljoin(page_url, href)
                    for href in selector.css(config.get("article_selector", "a")).xpath("@href").getall()
                    if href
                )
        deduped_links = list(dict.fromkeys(links))

        articles = []
        for link in deduped_links[: config.get("limit", 20)]:
            if not await self._allowed(link):
                continue
            await asyncio.sleep(float(config.get("request_delay_seconds", 1)))
            requires_js = bool(config.get("requires_js"))
            article_html = await self._fetch_page(link, requires_js=requires_js)
            if requires_js:
                article_soup = BeautifulSoup(article_html, "html.parser")
                title = self._text(article_soup, config.get("title_selector", "h1")) or "Untitled"
                content = self._text(article_soup, config.get("content_selector", "article, main"))
                published_text = (
                    self._text(article_soup, config.get("date_selector", "")) if config.get("date_selector") else ""
                )
                author = self._text(article_soup, config.get("author_selector", "")) if config.get("author_selector") else None
                image_url = self._image_url(article_soup, config.get("image_selector", "meta[property='og:image']"), link)
            else:
                article_selector = Selector(text=article_html)
                title = self._css_text(article_selector, config.get("title_selector", "h1")) or "Untitled"
                content = self._css_text(article_selector, config.get("content_selector", "article, main"))
                published_text = (
                    self._css_text(article_selector, config.get("date_selector", "")) if config.get("date_selector") else ""
                )
                author = self._css_text(article_selector, config.get("author_selector", "")) if config.get("author_selector") else None
                image_url = self._css_image_url(article_selector, config.get("image_selector", "meta[property='og:image']"), link)
            published_at = self._parse_date(
                published_text,
                config.get("date_format"),
            )
            if content:
                articles.append(
                    RawArticle(
                        source_id=source.id,
                        external_url=link,
                        title_original=title,
                        content_original=content,
                        language=source.language,
                        published_at=published_at,
                        author=author,
                        image_url=image_url,
                        metadata={
                            "scraper": True,
                            "requires_js": bool(config.get("requires_js")),
                            "engine": "playwright" if config.get("requires_js") else "scrapy",
                        },
                    )
                )
        return articles

    async def _list_pages(self, list_url: str, config: dict) -> list[str]:
        """Follow configured next-button pagination for a bounded number of pages."""
        pagination = config.get("pagination") or {}
        pages = [list_url]
        if pagination.get("type") != "next_button" or not pagination.get("selector"):
            return pages
        max_pages = int(pagination.get("max_pages", 3))
        current = list_url
        for _ in range(max_pages - 1):
            html = await self._fetch_page(current, requires_js=bool(config.get("requires_js")))
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one(pagination["selector"])
            href = next_link.get("href") if next_link else None
            if not href:
                break
            current = urljoin(current, href)
            if current in pages:
                break
            pages.append(current)
        return pages

    async def _fetch_page(self, url: str, *, requires_js: bool = False) -> str:
        if requires_js:
            return await self._render_with_playwright(url)
        return await self._fetch(url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=5))
    async def _fetch(self, url: str) -> str:
        if not await self._allowed(url):
            raise PermissionError(f"robots.txt disallows scraping {url}")
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": random.choice(self.USER_AGENTS)})
            response.raise_for_status()
            return response.text

    async def _render_with_playwright(self, url: str) -> str:
        """Render JS-heavy pages when Playwright is installed in the runtime."""
        if not await self._allowed(url):
            raise PermissionError(f"robots.txt disallows scraping {url}")
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for scraper_config.requires_js=true") from exc

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=random.choice(self.USER_AGENTS))
            try:
                await page.goto(url, wait_until="networkidle", timeout=settings.request_timeout_seconds * 1000)
                return await page.content()
            finally:
                await browser.close()

    async def _allowed(self, url: str) -> bool:
        """Respect robots.txt before fetching pages."""
        parsed = httpx.URL(url)
        robots_url = f"{parsed.scheme}://{parsed.host}/robots.txt"
        parser = robotparser.RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                response = await client.get(robots_url, headers={"User-Agent": self.USER_AGENTS[0]})
                if response.status_code >= 400:
                    return True
                parser.parse(response.text.splitlines())
            return parser.can_fetch(self.USER_AGENTS[0], url)
        except Exception:
            return True

    @staticmethod
    def _text(soup: BeautifulSoup, selector: str) -> str:
        if not selector:
            return ""
        nodes = soup.select(selector)
        return "\n".join(node.get_text(" ", strip=True) for node in nodes)

    @staticmethod
    def _css_text(selector: Selector, css_selector: str) -> str:
        if not css_selector:
            return ""
        values = [
            " ".join(value.split())
            for node in selector.css(css_selector)
            if (value := node.xpath("string()").get(default="").strip())
        ]
        return "\n".join(values)

    @staticmethod
    def _css_image_url(selector: Selector, css_selector: str, base_url: str) -> str | None:
        node = selector.css(css_selector)
        value = node.attrib.get("content") or node.attrib.get("src") if node else None
        return urljoin(base_url, value) if value else None

    @staticmethod
    def _parse_date(value: str, date_format: str | None = None) -> datetime | None:
        value = value.strip()
        if not value:
            return None
        try:
            if date_format:
                parsed = datetime.strptime(value, date_format)
            else:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @staticmethod
    def _image_url(soup: BeautifulSoup, selector: str, base_url: str) -> str | None:
        node = soup.select_one(selector)
        if not node:
            return None
        value = node.get("content") or node.get("src")
        return urljoin(base_url, value) if value else None
