"""SEO/GEO Research Agent - Conducts live Ahrefs research via tool use.

This agent uses Claude's tool-use capability to autonomously query Ahrefs
in real time. It decides what data it needs, calls the appropriate Ahrefs
endpoints, analyzes the results, and iterates until it has enough data
to produce a comprehensive SEO/GEO brief.
"""

from __future__ import annotations

import json
from anthropic import Anthropic
from config.settings import (
    ANTHROPIC_API_KEY,
    DWC_DOMAIN,
    DWC_EXISTING_CONTENT,
    TARGET_AUDIENCE,
    MODEL_RESEARCH,
    MAX_TOKENS,
)
from integrations.ahrefs import AHREFS_TOOLS, execute_tool


client = Anthropic(api_key=ANTHROPIC_API_KEY)

MAX_TOOL_ROUNDS = 12  # Safety limit on agentic loop iterations

SYSTEM_PROMPT = f"""You are an expert SEO and GEO (Generative Engine Optimization) strategist specializing in B2B industrial content. You have real-time access to Ahrefs via tool calls and you MUST use them to gather live data for every research task.

## Your Domain
You optimize content for {DWC_DOMAIN} (Distributor Wire & Cable), a master distributor of electrical wire and cable selling exclusively to electrical distributors.

## Target Audience
{TARGET_AUDIENCE}

## Existing Content (avoid cannibalization)
{json.dumps(DWC_EXISTING_CONTENT, indent=2)}

## Your Research Process
You have access to Ahrefs tools. You MUST call them to gather real data. Do NOT rely on assumptions or cached knowledge. For every topic, follow this research workflow:

### Step 1: Keyword Discovery
- Use `ahrefs_keywords_overview` to get metrics for the obvious primary keyword candidates
- Use `ahrefs_related_keywords` to discover secondary and long-tail opportunities
- Use `ahrefs_search_suggestions` to find question-based queries and autocomplete variations

### Step 2: SERP & Competition Analysis
- Use `ahrefs_serp_overview` on the primary keyword to see who ranks and what SERP features exist
- Use `ahrefs_top_pages` on 1-2 top competitors to see what content performs for them
- Use `ahrefs_organic_keywords` on a top-ranking competitor URL to find keyword gaps

### Step 3: DWC Positioning
- Use `ahrefs_domain_metrics` on distributorwire.com to get current authority metrics
- Use `ahrefs_organic_keywords` on distributorwire.com to check for cannibalization risks

### Step 4: Synthesis
After gathering data, produce your final analysis.

## Important Guidelines
- Call tools in batches when possible (e.g., get overview for multiple keyword candidates at once)
- Check SERP features carefully: if AI overviews exist, the content needs GEO optimization
- Always check if DWC already ranks for candidate keywords to avoid cannibalization
- Prioritize keywords where DWC can realistically compete (KD < 40, or where low-DR sites rank)
- Consider search intent from the SERP composition (informational SERPs vs. commercial vs. transactional)

## GEO-Specific Analysis
For AI discoverability, analyze:
- Whether AI overviews appear in SERP features for target keywords
- What content structure the top AI-cited results use
- Whether question-format queries trigger featured snippets or AI overviews
- How to structure content so AI systems can extract and cite key facts

## Final Output
When you have gathered enough data, produce your final brief as a JSON object with these exact fields:
- primary_keyword (string)
- secondary_keywords (array of strings)
- long_tail_keywords (array of strings)
- keyword_data (array of objects with: keyword, volume, difficulty, traffic_potential, cpc_cents, serp_features)
- search_intent (string): primary intent category with explanation based on SERP analysis
- serp_features (array of strings): SERP features observed for the primary keyword
- competitor_urls (array of strings): top competing URLs from live SERP data
- content_gap_opportunities (array of strings): underserved angles based on data
- recommended_word_count (integer)
- geo_optimization_notes (string): specific GEO/AI optimization recommendations based on observed SERP features
- ahrefs_data_summary (string): brief summary of the live data you gathered and key findings

Wrap your final JSON in <final_brief> tags so it can be extracted."""


class SEOResearcherAgent:
    """SEO/GEO agent that queries Ahrefs in real time via Claude tool use."""

    name = "SEO/GEO Researcher"
    model = MODEL_RESEARCH
    max_tokens = MAX_TOKENS

    def research(self, topic: str, domain_brief: dict) -> dict:
        """Run live SEO/GEO research using Ahrefs tools.

        The agent autonomously decides which Ahrefs endpoints to query,
        gathers data across multiple tool-call rounds, and synthesizes
        a comprehensive SEO brief.
        """
        user_message = f"""Conduct comprehensive SEO and GEO research for the following topic using your Ahrefs tools.

TOPIC: {topic}

DOMAIN RESEARCH BRIEF (from wire & cable domain expert):
{json.dumps(domain_brief, indent=2)}

Research this topic thoroughly using live Ahrefs data. You must:
1. Identify and evaluate keyword opportunities with real volume/difficulty data
2. Analyze the actual SERP for the primary keyword
3. Check competitor content that ranks for related terms
4. Verify DWC's current positioning to avoid cannibalization
5. Look for GEO optimization signals (AI overviews, featured snippets)

Use the domain expert's key concepts and pain points to guide your keyword research toward terms that match how electrical distributors actually search.

Start by getting keyword metrics for the most obvious primary keyword candidates, then expand from there."""

        messages = [{"role": "user", "content": user_message}]

        # Agentic tool-use loop
        for round_num in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=AHREFS_TOOLS,
                messages=messages,
            )

            # Check if the model wants to use tools
            if response.stop_reason == "tool_use":
                # Collect all tool uses from this response
                assistant_content = response.content
                tool_results = []

                for block in assistant_content:
                    if block.type == "tool_use":
                        result = execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                # Add assistant response and tool results to conversation
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

            else:
                # Model is done with tools, extract final brief
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                return self._extract_brief(final_text)

        # Safety: if we hit max rounds, try to extract whatever we have
        return self._extract_brief(final_text if "final_text" in dir() else "{}")

    def _extract_brief(self, text: str) -> dict:
        """Extract the JSON brief from the agent's final response."""
        # Try to find JSON within <final_brief> tags first
        import re
        tag_match = re.search(r"<final_brief>\s*(\{.*?\})\s*</final_brief>", text, re.DOTALL)
        if tag_match:
            try:
                return json.loads(tag_match.group(1))
            except json.JSONDecodeError:
                pass

        # Fall back to finding any JSON object in the response
        # Find the largest JSON object in the text
        best_json = None
        best_len = 0
        depth = 0
        start = None

        for i, char in enumerate(text):
            if char == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    candidate = text[start : i + 1]
                    if len(candidate) > best_len:
                        try:
                            parsed = json.loads(candidate)
                            # Validate it looks like our expected output
                            if "primary_keyword" in parsed or "keyword_data" in parsed:
                                best_json = parsed
                                best_len = len(candidate)
                        except json.JSONDecodeError:
                            pass
                    start = None

        if best_json:
            return best_json

        # Last resort: ask the model to format its findings as JSON
        return self._fallback_extraction(text)

    def _fallback_extraction(self, raw_text: str) -> dict:
        """If JSON extraction fails, ask Claude to reformat the output."""
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system="You are a JSON formatting assistant. Extract the SEO research data from the text and return it as valid JSON.",
            messages=[
                {
                    "role": "user",
                    "content": f"""Extract the SEO research brief from this text and return it as a JSON object with these fields:
- primary_keyword, secondary_keywords, long_tail_keywords, keyword_data, search_intent,
- serp_features, competitor_urls, content_gap_opportunities, recommended_word_count,
- geo_optimization_notes, ahrefs_data_summary

TEXT:
{raw_text[:6000]}""",
                },
                {"role": "assistant", "content": "{"},
            ],
        )
        raw = "{" + response.content[0].text
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
        # Absolute last resort
        return {
            "primary_keyword": "",
            "secondary_keywords": [],
            "long_tail_keywords": [],
            "keyword_data": [],
            "search_intent": "informational",
            "serp_features": [],
            "competitor_urls": [],
            "content_gap_opportunities": [],
            "recommended_word_count": 2000,
            "geo_optimization_notes": "Unable to extract structured brief. Raw analysis available.",
            "ahrefs_data_summary": raw_text[:2000],
        }
