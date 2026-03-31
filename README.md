# Marcus

**DWC's AI content strategist.** Named after Marcus Sheridan, whose "They Ask, You Answer" philosophy drives DWC's content strategy.

Marcus is a swarm of 10 AI agents that researches, writes, fact-checks, edits, and publishes wire & cable content for electrical distributors. It scans the competitive landscape daily, identifies content gaps, and emails you scored topic suggestions. You reply with a number, and Marcus writes the article and publishes it as a draft to Contentful.

## What Marcus does

- **Daily competitive scanning** via Ahrefs: finds keywords competitors rank for that DWC doesn't
- **Product coverage gap analysis**: maps DWC's product catalog against existing content and flags holes
- **Topic scoring**: evaluates every suggestion through the eyes of an electrical distributor
- **Full article pipeline**: domain research, SEO/GEO keyword strategy, outline, writing, fact checking, editorial polish
- **Quality gates with feedback loops**: the orchestrator sends work back for revision when it doesn't meet standards
- **Contentful publishing**: drafts land in your CMS ready for review
- **Persistent memory**: tracks what's been published, keyword positions over time, competitor trends, and topical cluster health

## The agents

| # | Agent | Model | What it does |
|---|---|---|---|
| 1 | **Orchestrator** | Opus 4.6 | Manages the pipeline, enforces quality gates, sends work back for revision |
| 2 | **Domain Researcher** | Sonnet 4.6 | Researches wire & cable topics from a distributor's perspective |
| 3 | **SEO/GEO Researcher** | Sonnet 4.6 | Queries Ahrefs live for keywords, SERPs, competitor intel |
| 4 | **Value Analyst** | Opus 4.6 | Scores topics from behind the counter at a distribution branch |
| 5 | **Outline Architect** | Sonnet 4.6 | Structures comprehensive outlines for search and AI citation |
| 6 | **Writer** | Opus 4.6 | Writes authoritative articles in DWC's voice |
| 7 | **Fact Checker** | Sonnet 4.6 | Verifies NEC codes, specs, product alignment, catches hallucinations |
| 8 | **Editor in Chief** | Opus 4.6 | Final polish, kills AI patterns and emdashes |
| 9 | **Canary** | Haiku 4.5 | Publishes to Contentful as draft, records in memory |
| 10 | **Competitive Scout** | Sonnet 4.6 | Daily landscape scan via Ahrefs, finds opportunities |

## Setup guide

### Prerequisites

- **Python 3.11+** (check with `python3 --version`)
- **Git** (to clone the repo)

### Step 1: Clone and install

```bash
git clone https://github.com/crgklr/local-isp.git marcus
cd marcus
git checkout claude/wire-distribution-research-agent-6eVrW

python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Get your API keys

You need accounts with four services:

#### Anthropic (required) - powers all agents

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to **API Keys** in the left sidebar
4. Click **Create Key**, copy it (starts with `sk-ant-api03-`)

**Cost**: ~$1.50-2.50 per article, ~$0.50-1.00 per daily scout scan.

#### Ahrefs (required) - live SEO data

1. Log in to [ahrefs.com](https://ahrefs.com)
2. Click your profile icon > **API key**
3. Copy your API key

**Cost**: Included in your Ahrefs subscription.

#### Contentful (required) - where articles are published

1. Sign up at [contentful.com](https://www.contentful.com) (free tier works)
2. Create a new space (e.g., "DWC Blog")
3. Create a content type with ID `blogPost` and these fields:
   - `title` (Short text)
   - `slug` (Short text)
   - `body` (Long text)
   - `metaDescription` (Short text)
   - `author` (Short text)
4. Get your **Space ID**: Settings > General
5. Create a **management token**: Settings > CMA tokens > Generate personal token

**Cost**: Free (25,000 API calls/month).

#### Email service (required for daily mode) - pick one

**Option A: SendGrid (recommended)**

1. Sign up at [sendgrid.com](https://sendgrid.com) (free = 100 emails/day)
2. **Settings > API Keys > Create API Key** (Full Access), copy it (starts with `SG.`)
3. **Settings > Sender Authentication**, verify a sender email address

**Option B: Gmail SMTP (simplest, no new account)**

1. Enable **2-Step Verification** on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an app password for "Mail", copy the 16-character password

### Step 3: Configure

```bash
cp .env.example .env
```

Edit `.env` with your keys. At minimum:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
AHREFS_API_KEY=...
CONTENTFUL_SPACE_ID=...
CONTENTFUL_MANAGEMENT_TOKEN=CFPAT-...
SENDGRID_API_KEY=SG...
EMAIL_FROM=marcus@distributorwire.com
EMAIL_TO=you@example.com
```

### Step 4: Seed memory (one time)

```bash
python main.py --seed
```

This tells Marcus about DWC's 11 existing articles and 10 topical clusters.

### Step 5: Test

```bash
python main.py --suggest                    # See content gaps
python main.py --scout                      # Run a competitive scan
python main.py "Direct burial wire guide"   # Write an article
```

### Step 6: Start the daily scheduler

```bash
python main.py --daemon
```

Marcus will scan at 7 AM daily, email you suggestions, and write articles when you reply.

## How the pipeline works

```
You: "Write about tray cable"
     |
     v
Orchestrator (Opus) -----> reviews every output
     |                      sends back for revision if needed
     |                      max 2 rounds per agent
     |
     |---> Domain Researcher -----> QUALITY CHECK
     |---> SEO Researcher (Ahrefs) -> QUALITY CHECK
     |---> Value Analyst ----------> QUALITY GATE (can kill pipeline)
     |---> Outline Architect ------> QUALITY CHECK
     |---> Writer -----------------> QUALITY CHECK
     |---> Fact Checker -----------> QUALITY GATE (can loop back)
     |---> Editor in Chief --------> QUALITY CHECK
     |---> Canary -----------------> Contentful (draft) + Memory
     |
     v
Draft in Contentful + email notification
```

## Daily email workflow

1. **7:00 AM**: Marcus scans Ahrefs, scores opportunities, emails you suggestions with value badges
2. **You reply**: "3" (or "3 - focus on NEC compliance angle")
3. **Within 5 minutes**: Marcus picks up the reply, runs the full pipeline
4. **When done**: You get an email with the Contentful entry ID

## Deployment

Marcus needs long-running process support (not Vercel/Netlify).

| Host | Start command | Cost |
|---|---|---|
| [Railway](https://railway.app) | `python main.py --daemon` | ~$5-20/mo |
| [Render](https://render.com) | Background worker | ~$7-25/mo |
| [Fly.io](https://fly.io) | Dockerfile | ~$5-15/mo |

## Monthly cost

| Service | Cost |
|---|---|
| Anthropic API | $15-60 (depends on volume) |
| Ahrefs | Included in subscription |
| Contentful | Free |
| SendGrid | Free |
| Hosting | $5-20 |
| **Total** | **$20-80/month** |

## Commands

| Command | What it does |
|---|---|
| `python main.py "topic"` | Run the full pipeline |
| `python main.py "topic" -v` | Verbose mode |
| `python main.py --seed` | Seed memory (run once) |
| `python main.py --suggest` | Show clusters and opportunities |
| `python main.py --scout` | Run competitive scan now |
| `python main.py --daemon` | Start daily scheduler |

## Project structure

```
marcus/
├── main.py                    # CLI entry point
├── pipeline.py                # Orchestrator with quality gates
├── scheduler.py               # Daily scout + email reply handler
├── agents/
│   └── definitions.py         # All 10 agent prompts and model configs
├── tools/
│   ├── ahrefs_tools.py        # 8 Ahrefs API v3 tools
│   ├── contentful_tools.py    # 4 Contentful CMS tools
│   └── memory_tools.py        # 10 SQLite memory tools
├── memory/
│   ├── store.py               # SQLite persistence layer (6 tables)
│   └── seed.py                # Initial content + cluster seeding
├── integrations/
│   └── email_service.py       # SendGrid/SMTP + IMAP reply polling
├── config/
│   └── settings.py            # Configuration + DWC domain knowledge
├── .env.example               # API key template
└── requirements.txt
```
