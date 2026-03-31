"""Pipeline configuration and constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AHREFS_API_KEY = os.getenv("AHREFS_API_KEY", "")
CONTENTFUL_SPACE_ID = os.getenv("CONTENTFUL_SPACE_ID", "")
CONTENTFUL_MANAGEMENT_TOKEN = os.getenv("CONTENTFUL_MANAGEMENT_TOKEN", "")
CONTENTFUL_ENVIRONMENT = os.getenv("CONTENTFUL_ENVIRONMENT", "master")
CONTENTFUL_CONTENT_TYPE_ID = os.getenv("CONTENTFUL_CONTENT_TYPE_ID", "blogPost")

# Email configuration (SendGrid recommended, SMTP fallback)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "content-agent@distributorwire.com")
EMAIL_TO = os.getenv("EMAIL_TO", "")  # Your email address
IMAP_HOST = os.getenv("IMAP_HOST", "")  # For polling replies (e.g., imap.gmail.com)
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")

# Scheduler configuration
SCOUT_SCHEDULE_HOUR = int(os.getenv("SCOUT_SCHEDULE_HOUR", "7"))  # 7 AM daily
SCOUT_SCHEDULE_MINUTE = int(os.getenv("SCOUT_SCHEDULE_MINUTE", "0"))
REPLY_POLL_INTERVAL_MINUTES = int(os.getenv("REPLY_POLL_INTERVAL_MINUTES", "5"))

# Scout thresholds
MAX_KEYWORD_DIFFICULTY = int(os.getenv("MAX_KEYWORD_DIFFICULTY", "30"))
MIN_KEYWORD_VOLUME = int(os.getenv("MIN_KEYWORD_VOLUME", "50"))
SCOUT_COMPETITOR_LIMIT = int(os.getenv("SCOUT_COMPETITOR_LIMIT", "5"))
SUGGESTIONS_PER_EMAIL = int(os.getenv("SUGGESTIONS_PER_EMAIL", "5"))

# Model configuration
MODEL = "claude-sonnet-4-6"
MODEL_RESEARCH = "claude-sonnet-4-6"
MODEL_WRITER = "claude-sonnet-4-6"
MAX_TOKENS = 8192
MAX_TOKENS_WRITER = 16384

DWC_DOMAIN = "distributorwire.com"

DWC_PRODUCT_CATEGORIES = {
    "residential": ["URD cable", "SER cable", "SEU cable", "Building wire (NM-B / Romex type)"],
    "commercial": ["Commercial building wire (THHN/THWN-2)", "Machine tool wire (MTW)", "XHHW-2 wire"],
    "industrial": ["Tray cable (VNTC, TC-ER)", "Instrumentation tray cable", "Industrial power cable", "Control cable"],
    "utility": ["Medium voltage cable (MV-105)", "ACSR conductor", "Utility tray cable", "Bare copper and aluminum conductor", "Underground distribution cable"],
}

DWC_SERVICES = [
    "Master distribution / wholesale wire & cable supply",
    "FastQuote online quoting platform",
    "Same-day and next-day shipping",
    "Cut-to-length services",
    "Dedicated account management",
    "Technical support and wire expertise",
    "Stocking programs for electrical distributors",
    "Multi-warehouse national distribution network",
]

DWC_VALUE_PROPOSITIONS = [
    "Master distributor selling exclusively to electrical distributors (never direct to contractors)",
    "Broad inventory across residential, commercial, industrial, and utility wire & cable",
    "Speed and reliability: fast quoting, fast shipping",
    "Deep technical expertise in wire and cable products",
    "Partner, not competitor: DWC supports distributor sales teams, never competes for their customers",
    "National footprint with regional warehouse locations (including Dallas, TX)",
]

DWC_COMPETITORS = [
    {"domain": "classicwire.com", "dr": 29, "traffic": 1587},
    {"domain": "houwire.com", "dr": 30, "traffic": 2798},
    {"domain": "prioritywire.com", "dr": 39, "traffic": 6902},
    {"domain": "servicewire.com", "dr": 40, "traffic": 5811},
    {"domain": "omnicable.com", "dr": 41, "traffic": 24174},
    {"domain": "wireandcableyourway.com", "dr": 29, "traffic": 57385},
    {"domain": "awcwire.com", "dr": 49, "traffic": 43098},
    {"domain": "southwire.com", "dr": 71, "traffic": 104386},
    {"domain": "encorewire.com", "dr": 43, "traffic": 12902},
]

DWC_EXISTING_CONTENT = [
    {"url": "/blogs/What-is-ACSR", "keyword": "what is acsr", "traffic": 84},
    {"url": "/blogs/what-is-thhn-wire", "keyword": "what is thhn", "traffic": 70},
    {"url": "/residential/SER-cable", "keyword": "ser cable", "traffic": 68},
    {"url": "/blogs/what-are-the-main-differences-between-solid-and-stranded-conductors", "keyword": "solid conductor", "traffic": 47},
    {"url": "/residential/urd-cable", "keyword": "urd cable", "traffic": 124},
    {"url": "/utility/medium-voltage", "keyword": "mv 105 cable", "traffic": 47},
    {"url": "/industrial/tray-cable", "keyword": "vntc tray cable", "traffic": 34},
    {"url": "/blogs/cable-jackets-vs-insulation-understanding-the-critical-difference", "keyword": "cable jacket", "traffic": 25},
    {"url": "/blogs/going-undergound-a-look-at-urd-cable", "keyword": "what is urd wire", "traffic": 24},
    {"url": "/blogs/epr-vs-xlpe-insulation-electrical-distributor-guide", "keyword": "epr cable", "traffic": 16},
    {"url": "/blogs/understanding-the-ieee-1202-ft4-70-000-btu-hour-flame-test-for-wire-and", "keyword": "ieee 1202", "traffic": 7},
]

KEYWORD_OPPORTUNITIES = [
    {"keyword": "thhn wire", "volume": 7600, "difficulty": 1, "tp": 1100},
    {"keyword": "mc cable", "volume": 6600, "difficulty": 0, "tp": 150},
    {"keyword": "armored cable", "volume": 1600, "difficulty": 1, "tp": 1200},
    {"keyword": "direct burial wire", "volume": 3000, "difficulty": 0, "tp": 1400},
    {"keyword": "bx cable", "volume": 3300, "difficulty": 0, "tp": 900},
    {"keyword": "ser cable", "volume": 1700, "difficulty": 0, "tp": 700},
    {"keyword": "underground electrical wire", "volume": 1600, "difficulty": 3, "tp": 700},
    {"keyword": "thhn wire meaning", "volume": 2100, "difficulty": 0, "tp": 2500},
    {"keyword": "electrical wiring", "volume": 4800, "difficulty": 9, "tp": 1000},
    {"keyword": "romex cable", "volume": 2100, "difficulty": 0, "tp": 8400},
    {"keyword": "thhn wire size chart", "volume": 200, "difficulty": 10, "tp": 50000},
    {"keyword": "ampacity aluminum wire", "volume": 150, "difficulty": 3, "tp": 48000},
]

TARGET_AUDIENCE = """
Electrical distributors (counter sales, inside sales, outside sales reps, branch managers,
purchasing managers, and owners) who sell wire & cable products to electrical contractors.
These are B2B professionals who need to understand wire & cable specifications, applications,
and code requirements to advise their contractor customers and win deals. They are NOT
contractors themselves. Content should help distributors be more knowledgeable advisors
to their contractor customers, enabling them to sell more effectively.
"""
