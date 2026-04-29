# Marcus - Project Brief

This document is for AI assistants (Claude Code, etc.) picking up development
on this project. It contains everything you need to understand what Marcus is,
how it's built, what decisions were made and why, and what's next.

## What is Marcus?

Marcus is an AI-powered content strategy system for Distributor Wire & Cable
(DWC), a master distributor of electrical wire and cable that sells exclusively
to electrical distributors (never to contractors). Marcus is named after Marcus
Sheridan, whose "They Ask, You Answer" philosophy drives DWC's content strategy.

Marcus is a swarm of 10 AI agents that:
1. Scans the competitive landscape daily via Ahrefs
2. Identifies content gaps and keyword opportunities
3. Scores every opportunity through the eyes of an electrical distributor
4. Emails the human operator ranked suggestions
5. When the operator replies with a number, runs a full content pipeline
6. Publishes the finished article as a draft to Contentful
7. Emails the operator when it's done

## Architecture

### Agent SDK
Marcus is built on the Claude Agent SDK (`claude-agent-sdk` Python package).
The orchestrator uses `query()` with subagent delegation. Each agent is defined
as an `AgentDefinition` dict in `agents/definitions.py` with a system prompt,
model assignment, and tool access list. The SDK handles tool-use loops
automatically (no manual loop code needed).

### The 10 Agents

| Agent | Model | File/Location | Role |
|---|---|---|---|
| Orchestrator | Opus 4.6 | `pipeline.py` | Manages pipeline, enforces quality gates, sends work back for revision |
| Domain Researcher | Sonnet 4.6 | `agents/definitions.py` | Wire & cable industry expertise, distributor pain points, NEC/UL knowledge |
| SEO/GEO Researcher | Sonnet 4.6 | `agents/definitions.py` | Live Ahrefs queries, keyword strategy, SERP analysis, AI discoverability |
| Value Analyst | Opus 4.6 | `agents/definitions.py` | Scores topics on 4 dimensions from the distributor's perspective |
| Outline Architect | Sonnet 4.6 | `agents/definitions.py` | Structures articles for comprehensive coverage and GEO optimization |
| Writer | Opus 4.6 | `agents/definitions.py` | Writes articles in DWC's BrandScript voice with TAYA transparency |
| Fact Checker | Sonnet 4.6 | `agents/definitions.py` | Verifies technical accuracy, DWC product alignment, audience targeting |
| Editor in Chief | Opus 4.6 | `agents/definitions.py` | Final polish, kills AI patterns and emdashes |
| Canary | Haiku 4.5 | `agents/definitions.py` | Publishes to Contentful, records in memory, author: "Marcus" |
| Competitive Scout | Sonnet 4.6 | `agents/definitions.py` | Daily Ahrefs scan, coverage gaps, keyword opportunities, cluster expansion |

### Model Strategy
- **Opus 4.6**: Orchestrator, Writer, Value Analyst, Editor. Used where judgment,
  prose quality, empathy, or editorial taste matter.
- **Sonnet 4.6**: Domain Researcher, SEO Researcher, Outline Architect, Fact
  Checker, Competitive Scout. Used for research, tool-use, and structured output.
- **Haiku 4.5**: Canary only. Just makes API calls, no reasoning needed.

### Three MCP Tool Servers

All defined in `tools/` using `@tool` decorators and `create_sdk_mcp_server()`.

1. **ahrefs** (`tools/ahrefs_tools.py`) - 8 tools wrapping Ahrefs API v3:
   keywords_overview, related_keywords, search_suggestions, serp_overview,
   organic_keywords, domain_metrics, top_pages, organic_competitors

2. **contentful** (`tools/contentful_tools.py`) - 4 tools:
   publish_draft (sets author to "Marcus"), list_all_content (paginated),
   get_entry_content (full body by ID), search_content_by_slug

3. **memory** (`tools/memory_tools.py`) - 10 tools wrapping SQLite:
   get/record published_content, keyword_positions, cluster_map,
   scout_scans, competitor_snapshots

### Persistent Memory

SQLite database at `output/memory.db` with 6 tables:
- `published_content` - articles DWC has published
- `keyword_positions` - keyword rank tracking over time
- `clusters` + `cluster_keywords` - topical cluster map
- `scout_scans` - competitive scan history
- `competitor_snapshots` - competitor metric trends

Contentful is the **source of truth** for what content exists. Memory tracks
supplementary data (keyword positions, clusters, competitor trends) that
Contentful doesn't store.

### Quality Gates

The orchestrator (`pipeline.py`) reviews every agent's output:
- Domain Researcher: ≥5 key concepts, ≥3 pain points, specific product relevance
- SEO Researcher: real volume data, ≥3 secondary keywords, KD feasibility
- Value Analyst: tiered gate (≥70 proceed, 50-69 consider pivot, 30-49 force
  new angle, <30 kill pipeline)
- Outline: ≥6 sections, ≥1500 word target, ≥2 internal links
- Writer: within 20% of target word count, must have table + FAQ
- Fact Checker: all scores ≥80 or revision loop (max 2 rounds back to writer)
- Editor: >15 edits flagged as quality concern in report
- Max 2 revision rounds per agent before proceeding with best available

### Daily Scheduler

`scheduler.py` runs two threads:
1. **Scout loop**: fires at configured hour (default 7 AM), runs competitive
   scout + value analyst, emails scored suggestions
2. **Reply loop**: polls IMAP every 5 minutes for email replies, triggers
   full pipeline when a reply is found

### Email

`integrations/email_service.py` supports SendGrid (preferred) or Gmail SMTP
fallback. IMAP polling for reply detection. All emails branded as "Marcus by DWC".
Reply matching searches for `"Re: Marcus"` in subject line.

## Key Design Decisions

### Why Contentful as source of truth (not SQLite)?
Contentful is the live CMS. If someone publishes an article through the
Contentful UI directly, the agents see it on next run. SQLite can't know
about manual publishes. The `list_all_content` tool paginates through all
entries and returns title, slug, status, dates.

### Why the Big 5 is "a lens, not a constraint"
Early versions had agents rigidly mapping every topic to one of 5 content
types (cost, problems, comparisons, best-of, what-is). This made topic
recommendations formulaic. The Big 5 are now just one input for spotting
gaps. Agents think broader: technical deep-dives, application guides, code
walkthroughs, spec references, industry analysis.

### Why duplicate topics get replaced, not blocked
If the scout or domain researcher finds a topic that already exists in
Contentful, it doesn't stop. It reads the existing article via
`get_entry_content` and finds a complementary angle the existing piece
doesn't cover. The pipeline never produces duplicate content, but it also
never wastes an opportunity by refusing to think about a topic area.

### Why the value analyst uses Opus
The scoring requires genuine empathy and calibrated judgment. Sonnet produces
flat, predictable scores. Opus reasons about whether a counter sales rep
would actually use this knowledge when a contractor calls. The
`distributor_perspective` field is written AS a distributor.

### DWC BrandScript (embedded in `_DWC_CONTEXT`)
- Hero = electrical distributor
- Guide = DWC
- Problem = specialty cable sourcing eats time, the "simplest" part of the
  BOM causes the most stress
- Plan = Send BOM → fastQuote in 6 min → Win the Bid
- Result = zero inventory risk, hero status with contractors
- Failure = losing bids to faster competitors

### Content philosophy (embedded in `_DWC_CONTENT_PHILOSOPHY`)
- Radical transparency (answer everything, no gatekeeping)
- Assignment selling (every article good enough for a rep to send pre-call)
- Endless customers (content builds trust at scale, trust compounds)
- Ownership (if DWC doesn't answer it, a competitor will)
- Comprehensive coverage mandate (if DWC sells it, DWC writes about it)
- AI discoverability (rank #1 on Google + surface in ChatGPT, Perplexity,
  Claude, Grok, Meta AI, AI Overviews, fan-out queries)

## What's Working

- Full codebase is on GitHub at `crgklr/local-isp`, branch
  `claude/wire-distribution-research-agent-6eVrW`
- All agent definitions, tool servers, memory layer, email service,
  scheduler, and orchestrator are implemented
- README has complete setup guide with step-by-step API key instructions
- Memory seed file has 11 existing DWC articles and 10 topical clusters
- Flowchart PDF is in the repo root (`marcus-flowchart.pdf`)

## What Hasn't Been Tested Yet

This system was designed and built in a single session. It has NOT been:
- Run end-to-end against live APIs
- Tested with real Anthropic API calls (Agent SDK integration is untested)
- Tested with real Contentful space
- Tested with real email sending/receiving
- Deployed to any hosting platform

Expect integration bugs on first run. The Agent SDK's exact API surface
(AgentDefinition constructor, query() parameters, ResultMessage shape) should
be verified against the latest `claude-agent-sdk` package docs.

## What's Left to Build

### Immediate (before first real run)
- Verify `claude-agent-sdk` package API matches our usage (AgentDefinition
  accepts `model`, `description`, `prompt`, `tools` kwargs)
- Test each MCP tool server independently (Ahrefs auth, Contentful CRUD,
  SQLite memory)
- Test email sending via SendGrid or Gmail
- Set up Contentful space with the required content type schema
- Run `--seed` and verify memory database
- Run a single `--scout` and verify Ahrefs data flows through

### Short-term improvements
- Add extended thinking (planning mode) for agents that benefit from it:
  Orchestrator, Domain Researcher, Value Analyst, Outline Architect, Writer,
  Editor. The Agent SDK's mechanism for this needs to be researched.
- Add retry logic for transient API failures (Ahrefs rate limits, Contentful
  timeouts)
- Add cost tracking and reporting (the orchestrator prompt asks for it but
  the code doesn't aggregate across agents yet)
- Add a `--status` command showing memory stats, last scan date, pending
  suggestions
- Consider adding Google Search Console MCP tools (Ahrefs has GSC endpoints)

### Medium-term
- Dashboard or web UI for reviewing suggestions instead of email
- Webhook-based reply handling instead of IMAP polling (more reliable)
- Article revision workflow (re-run pipeline on existing articles to update)
- Performance tracking: after publish, monitor keyword positions over time
  and report on which articles are ranking
- A/B test different writer prompts and measure which produce better
  engagement/ranking outcomes

### Long-term
- Multi-language support (DWC may expand)
- Social media distribution agent (share articles on LinkedIn, etc.)
- Internal linking optimization agent (retroactively adds links when new
  content is published)
- Content refresh agent (identifies aging articles that need updating)

## File Map

```
marcus/
├── main.py                      # CLI: --seed, --suggest, --scout, --daemon, "topic"
├── pipeline.py                  # Orchestrator (Opus) with quality gates
├── scheduler.py                 # Daily scout + email reply handler
├── marcus-flowchart.pdf         # Visual architecture diagram
│
├── agents/
│   ├── definitions.py           # All 10 agent prompts, models, tool access
│   ├── base.py                  # Legacy base class (pre-SDK, may be unused)
│   ├── domain_researcher.py     # Legacy (pre-SDK, replaced by definitions.py)
│   ├── seo_researcher.py        # Legacy (pre-SDK, replaced by definitions.py)
│   ├── outline_agent.py         # Legacy
│   ├── writer.py                # Legacy
│   ├── fact_checker.py          # Legacy
│   ├── editor.py                # Legacy
│   ├── canary.py                # Legacy
│   └── competitive_scout.py     # Legacy
│
├── tools/
│   ├── ahrefs_tools.py          # 8 Ahrefs API v3 tools (@tool decorators)
│   ├── contentful_tools.py      # 4 Contentful CMS tools
│   └── memory_tools.py          # 10 SQLite memory tools
│
├── memory/
│   ├── store.py                 # SQLite persistence layer (6 tables)
│   └── seed.py                  # Initial content + cluster seeding
│
├── integrations/
│   ├── ahrefs.py                # Legacy Ahrefs integration (pre-SDK)
│   ├── contentful.py            # Legacy Contentful integration (pre-SDK)
│   └── email_service.py         # SendGrid/SMTP send + IMAP reply polling
│
├── config/
│   └── settings.py              # All config, DWC domain knowledge, model assignments
│
├── models/
│   └── content.py               # Legacy data models (pre-SDK)
│
├── .env.example                 # API key template with setup instructions
├── .gitignore
├── requirements.txt             # claude-agent-sdk, anthropic, httpx, python-dotenv, rich
└── README.md                    # Full setup guide
```

Note: Files marked "Legacy" are from the pre-Agent-SDK version of the codebase.
They're still in the repo but are NOT used by the current architecture. The
current system uses `agents/definitions.py` for all agent definitions and
`tools/*.py` for all tool servers. The legacy files can be cleaned up.

## Environment Variables

See `.env.example` for the complete list. Critical ones:
- `ANTHROPIC_API_KEY` - powers all agents
- `AHREFS_API_KEY` - live SEO data
- `CONTENTFUL_SPACE_ID` + `CONTENTFUL_MANAGEMENT_TOKEN` - CMS publishing
- `SENDGRID_API_KEY` or `IMAP_*` credentials - email
- `EMAIL_FROM` (default: marcus@distributorwire.com)
- `EMAIL_TO` - where suggestions go

## How to Continue Development

1. Clone: `git clone https://github.com/crgklr/local-isp.git marcus`
2. Branch: `git checkout claude/wire-distribution-research-agent-6eVrW`
3. Read this file and `README.md`
4. The core logic is in 4 files: `pipeline.py`, `scheduler.py`,
   `agents/definitions.py`, and `config/settings.py`
5. Tool servers are in `tools/`. Memory layer is in `memory/store.py`.
6. Start by verifying the Agent SDK integration works with a simple test
   before running the full pipeline.
