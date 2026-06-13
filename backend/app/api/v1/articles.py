"""Article detail and one-click translation routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import ApiError, envelope
from app.db import get_db
from app.models.article import Article
from app.schemas.article import ArticleRead, TranslateRequest, TranslateResponse
from app.services.processor.translator import TranslationError, TranslationService
from app.tasks.collect_task import backfill_article_fulltext

router = APIRouter()


def _translation_fallback_response(target_lang: str, error: TranslationError) -> TranslateResponse:
    """Return an honest Chinese fallback instead of leaving the article panel blank."""
    if target_lang.lower().startswith("zh"):
        return TranslateResponse(
            title="自动翻译暂不可用，请查看原文标题",
            content=(
                "自动翻译服务没有返回可用的中文译文。"
                "这通常表示还没有配置真实翻译模型，或模型返回了原文。"
                "请点击“显示原文”查看原始报道；原文语言已在文章信息中标注。"
            ),
            cached=False,
            fallback=True,
            message=f"翻译暂不可用：{error}",
        )
    return TranslateResponse(
        title="Translation unavailable; view the original title",
        content="The translation service did not return usable translated text. Use the original view for the source article.",
        cached=False,
        fallback=True,
        message=f"Translation unavailable: {error}",
    )


@router.get("/{article_id}")
async def get_article(article_id: UUID, db: AsyncSession = Depends(get_db)):
    article = (
        await db.execute(select(Article).options(selectinload(Article.source)).where(Article.id == article_id))
    ).scalar_one_or_none()
    if not article:
        raise ApiError("article_not_found", "Article not found", 404)
    return envelope(ArticleRead.model_validate(article).model_dump(mode="json"))


@router.post("/{article_id}/backfill-fulltext")
async def backfill_article(article_id: UUID, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise ApiError("article_not_found", "Article not found", 404)
    result = backfill_article_fulltext.delay(str(article_id))
    return envelope({"task_id": result.id, "status": "queued", "task": "backfill_article_fulltext"})


@router.post("/{article_id}/translate")
async def translate_article(article_id: UUID, payload: TranslateRequest, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise ApiError("article_not_found", "Article not found", 404)
    service = TranslationService()
    try:
        title, title_cached = await service.translate_on_demand(
            article.title_original,
            article.language,
            payload.target_lang,
            article_id=str(article_id),
            field="title",
        )
        content, content_cached = await service.translate_on_demand(
            article.content_original,
            article.language,
            payload.target_lang,
            article_id=str(article_id),
            field="content",
        )
    except TranslationError as exc:
        response = _translation_fallback_response(payload.target_lang, exc)
        return envelope(response.model_dump())
    if payload.target_lang == "en":
        article.title_translated = title
        article.content_translated = content
        await db.commit()
    response = TranslateResponse(title=title, content=content, cached=title_cached and content_cached)
    return envelope(response.model_dump())
