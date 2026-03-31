"""Competitive Scout Agent - Daily keyword gap and cluster expansion analysis.

Scans the competitive landscape via Ahrefs to find low-hanging fruit keywords
that competitors rank for but DWC doesn't, groups them into topical clusters,
and surfaces the best opportunities for new content.
"""

from __future__ import annotations

import json
from datetime import date
from anthropic import Anthropic
from config.settings import (
    ANTHROPIC_API_KEY,
    DWC_DOMAIN,
    DWC_EXISTING_CONTENT,
    DWC_COMPETITORS,
    DWC_PRODUCT_CATEGORIES,
    TARGET_AUDIENCE,
    MODEL_RESEARCH,
    MAX_TOKENS,
    MAX_KEYWORD_DIFFICULTY,
    MIN_KEYWORD_VOLUME,
    SCOUT_COMPETITOR_LIMIT,
    SUGGESTIONS_PER_EMAIL,
)
from integrations.ahrefs import AHREFS_TOOLS, execute_tool

client = Anthropic(api_key=ANTHROPIC_API_KEY)

MAX_TOOL_ROUNDS = 15

SYSTEM_PROMPT = f"""You are a competitive intelligence scout for Distributor Wire & Cable ({DWC_DOMAIN}), a master distributor of electrical wire and cable. You run daily scans of the competitive landscape to find content opportunities.

## Your Mission
Find low-hanging fruit keywords that DWC's competitors rank for but DWC doesn't. Group them into topical clusters and recommend the single best article to write next for each cluster.

## Target Audience
{TARGET_AUDIENCE}

## DWC Product Categories
{json.dumps(DWC_PRODUCT_CATEGORIES, indent=2)}

## Existing DWC Content (do NOT suggest topics already covered)
{json.dumps(DWC_EXISTING_CONTENT, indent=2)}

## Top Competitors to Monitor
{json.dumps(DWC_COMPETITORS[:SCOUT_COMPETITOR_LIMIT], indent=2)}

## Your Research Process
Use the Ahrefs tools to:

### Step 1: Refresh DWC's current keyword landscape
- Call `ahrefs_organic_keywords` on distributorwire.com to get current rankings
- Call `ahrefs_domain_metrics` on distributorwire.com for baseline

### Step 2: Scan competitors for gaps
- Call `ahrefs_top_pages` on the top 2-3 competitors to see their best content
- Call `ahrefs_organic_keywords` on 1-2 competitors, looking for keywords DWC doesn't rank for

### Step 3: Evaluate the gaps
- Call `ahrefs_keywords_overview` on the most promising gap keywords to get difficulty, volume, SERP features
- Focus on keywords with difficulty <= {MAX_KEYWORD_DIFFICULTY} and volume >= {MIN_KEYWORD_VOLUME}

### Step 4: Cluster and prioritize
Group the opportunities into topical clusters (e.g., "building wire specs", "cable testing standards", "underground installation") and pick the single best article topic for each cluster.

## Scoring Criteria
Rank opportunities by:
1. **Keyword Difficulty** (lower = better, max {MAX_KEYWORD_DIFFICULTY})
2. **Search Volume** (higher = better, min {MIN_KEYWORD_VOLUME})
3. **Traffic Potential** (how much traffic the #1 page gets from all its keywords)
4. **Cluster Fit** (does it expand an existing cluster or start a strategically important new one?)
5. **DWC Product Alignment** (can DWC naturally reference its products?)
6. **Competitor Weakness** (are the ranking pages from low-DR sites or thin content?)

## Final Output
Return your analysis as a JSON object with:
- scan_date (string): today's date
- dwc_current_metrics (object): organic_keywords, organic_traffic, traffic_value
- clusters (array of objects, each with):
  - cluster_name (string): descriptive name for the topical cluster
  - cluster_theme (string): 1-2 sentence description of the cluster
  - existing_dwc_content (array of strings): URLs of existing DWC content in this cluster
  - recommended_topic (object with):
    - title (string): suggested article title
    - primary_keyword (string)
    - volume (integer)
    - difficulty (integer)
    - traffic_potential (integer)
    - competitor_urls (array of strings): who currently ranks for this
    - rationale (string): why this is the right next piece for this cluster
  - additional_keywords (array of strings): other keywords this article could capture
- top_pick (object): the single best opportunity across all clusters, same structure as recommended_topic plus a cluster_name field

Wrap your final JSON in <scout_report> tags."""


class CompetitiveScoutAgent:
    """Daily competitive intelligence scanner."""

    name = "Competitive Scout"
    model = MODEL_RESEARCH
    max_tokens = MAX_TOKENS

    def scan(self) -> dict:
        """Run a full competitive scan and return clustered opportunities."""
        user_message = f"""Run your daily competitive scan for {date.today().isoformat()}.

Scan DWC's competitive landscape to find the best content opportunities. Focus on:
1. Keywords where competitors rank but DWC doesn't (content gaps)
2. Low difficulty keywords (KD <= {MAX_KEYWORD_DIFFICULTY}) with meaningful volume (>= {MIN_KEYWORD_VOLUME})
3. Topics that expand existing topical clusters or start strategically important new ones
4. Opportunities where DWC can naturally reference its products

Start by checking DWC's current state, then scan the top competitors for gaps."""

        messages = [{"role": "user", "content": user_message}]

        final_text = ""
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=AHREFS_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
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
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
            else:
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                return self._extract_report(final_text)

        return self._extract_report(final_text)

    def _extract_report(self, text: str) -> dict:
        """Extract the scout report JSON from the agent's response."""
        import re
        tag_match = re.search(r"<scout_report>\s*(\{.*?\})\s*</scout_report>", text, re.DOTALL)
        if tag_match:
            try:
                return json.loads(tag_match.group(1))
            except json.JSONDecodeError:
                pass

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
                            if "clusters" in parsed or "top_pick" in parsed:
                                best_json = parsed
                                best_len = len(candidate)
                        except json.JSONDecodeError:
                            pass
                    start = None

        if best_json:
            return best_json

        return {"error": "Failed to extract scout report", "raw": text[:3000]}
