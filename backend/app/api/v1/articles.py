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
from app.services.processor.translator import TranslationService

router = APIRouter()


@router.get("/{article_id}")
async def get_article(article_id: UUID, db: AsyncSession = Depends(get_db)):
    article = (
        await db.execute(select(Article).options(selectinload(Article.source)).where(Article.id == article_id))
    ).scalar_one_or_none()
    if not article:
        raise ApiError("article_not_found", "Article not found", 404)
    return envelope(ArticleRead.model_validate(article).model_dump(mode="json"))


@router.post("/{article_id}/translate")
async def translate_article(article_id: UUID, payload: TranslateRequest, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, article_id)
    if not article:
        raise ApiError("article_not_found", "Article not found", 404)
    service = TranslationService()
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
    if payload.target_lang == "en":
        article.title_translated = title
        article.content_translated = content
        await db.commit()
    response = TranslateResponse(title=title, content=content, cached=title_cached and content_cached)
    return envelope(response.model_dump())
