"""Data models for the content pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PipelineStage(Enum):
    DOMAIN_RESEARCH = "domain_research"
    SEO_RESEARCH = "seo_research"
    OUTLINE = "outline"
    WRITING = "writing"
    FACT_CHECK = "fact_check"
    EDITING = "editing"
    PUBLISHING = "publishing"
    COMPLETE = "complete"


@dataclass
class KeywordData:
    keyword: str
    volume: int
    difficulty: int
    traffic_potential: int
    cpc_cents: int
    parent_topic: Optional[str] = None
    current_position: Optional[int] = None


@dataclass
class CompetitorInsight:
    domain: str
    keywords_common: int
    keywords_they_have: int
    traffic: int
    domain_rating: float


@dataclass
class SEOResearchBrief:
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    keyword_data: list[KeywordData]
    search_intent: str
    serp_features: list[str]
    competitor_urls: list[str]
    content_gap_opportunities: list[str]
    recommended_word_count: int
    geo_optimization_notes: str


@dataclass
class DomainResearchBrief:
    topic: str
    target_audience_needs: str
    key_concepts: list[str]
    technical_details: str
    distributor_pain_points: list[str]
    sales_enablement_angles: list[str]
    dwc_product_relevance: list[str]
    industry_context: str


@dataclass
class ContentBrief:
    domain_research: DomainResearchBrief
    seo_research: SEOResearchBrief
    combined_recommendations: str


@dataclass
class ContentOutline:
    title: str
    meta_description: str
    h1: str
    sections: list[dict]
    internal_link_opportunities: list[str]
    schema_markup_type: str
    target_word_count: int
    brief: ContentBrief


@dataclass
class Article:
    title: str
    meta_description: str
    slug: str
    body_html: str
    body_markdown: str
    word_count: int
    outline: ContentOutline


@dataclass
class PipelineState:
    topic_seed: str
    stage: PipelineStage = PipelineStage.DOMAIN_RESEARCH
    domain_brief: Optional[DomainResearchBrief] = None
    seo_brief: Optional[SEOResearchBrief] = None
    content_brief: Optional[ContentBrief] = None
    outline: Optional[ContentOutline] = None
    draft_article: Optional[Article] = None
    fact_checked_article: Optional[Article] = None
    edited_article: Optional[Article] = None
    published_url: Optional[str] = None
    contentful_entry_id: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    errors: list[str] = field(default_factory=list)
