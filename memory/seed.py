"""Seed the memory database with DWC's existing content and initial cluster map.

Run this once before the first pipeline or scout run so agents know
what content already exists on distributorwire.com.

Usage:
    python main.py --seed
    python -m memory.seed
"""

from memory.store import record_published_content, update_cluster

EXISTING_ARTICLES = [
    {"title": "What is ACSR?", "slug": "what-is-acsr", "primary_keyword": "what is acsr", "url": "/blogs/What-is-ACSR", "cluster_name": "utility-conductors", "word_count": 0, "meta_description": ""},
    {"title": "What is THHN Wire?", "slug": "what-is-thhn-wire", "primary_keyword": "what is thhn", "url": "/blogs/what-is-thhn-wire", "cluster_name": "building-wire", "word_count": 0, "meta_description": ""},
    {"title": "SER Cable", "slug": "ser-cable", "primary_keyword": "ser cable", "url": "/residential/SER-cable", "cluster_name": "residential-cable", "word_count": 0, "meta_description": ""},
    {"title": "Solid vs Stranded Conductors: Main Differences", "slug": "solid-vs-stranded-conductors", "primary_keyword": "solid conductor", "url": "/blogs/what-are-the-main-differences-between-solid-and-stranded-conductors", "cluster_name": "wire-fundamentals", "word_count": 0, "meta_description": ""},
    {"title": "URD Cable", "slug": "urd-cable", "primary_keyword": "urd cable", "url": "/residential/urd-cable", "cluster_name": "underground-cable", "word_count": 0, "meta_description": ""},
    {"title": "Medium Voltage Cable", "slug": "medium-voltage", "primary_keyword": "mv 105 cable", "url": "/utility/medium-voltage", "cluster_name": "medium-voltage", "word_count": 0, "meta_description": ""},
    {"title": "Tray Cable", "slug": "tray-cable", "primary_keyword": "vntc tray cable", "url": "/industrial/tray-cable", "cluster_name": "tray-cable", "word_count": 0, "meta_description": ""},
    {"title": "Cable Jackets vs Insulation: Understanding the Critical Difference", "slug": "cable-jackets-vs-insulation", "primary_keyword": "cable jacket", "url": "/blogs/cable-jackets-vs-insulation-understanding-the-critical-difference", "cluster_name": "wire-fundamentals", "word_count": 0, "meta_description": ""},
    {"title": "Going Underground: A Look at URD Cable", "slug": "going-underground-urd-cable", "primary_keyword": "what is urd wire", "url": "/blogs/going-undergound-a-look-at-urd-cable", "cluster_name": "underground-cable", "word_count": 0, "meta_description": ""},
    {"title": "EPR vs XLPE Insulation: Electrical Distributor Guide", "slug": "epr-vs-xlpe-insulation", "primary_keyword": "epr cable", "url": "/blogs/epr-vs-xlpe-insulation-electrical-distributor-guide", "cluster_name": "medium-voltage", "word_count": 0, "meta_description": ""},
    {"title": "Understanding the IEEE 1202 FT4 70,000 BTU/Hour Flame Test", "slug": "ieee-1202-flame-test", "primary_keyword": "ieee 1202", "url": "/blogs/understanding-the-ieee-1202-ft4-70-000-btu-hour-flame-test-for-wire-and", "cluster_name": "cable-testing-standards", "word_count": 0, "meta_description": ""},
]

INITIAL_CLUSTERS = [
    {"name": "building-wire", "theme": "THHN, THWN-2, XHHW, and other building wire types for commercial and residential construction",
     "keywords": [{"keyword": "thhn wire", "volume": 7600, "difficulty": 1, "status": "opportunity"}, {"keyword": "what is thhn", "volume": 150, "difficulty": 0, "status": "published"}, {"keyword": "thhn wire meaning", "volume": 2100, "difficulty": 0, "status": "opportunity"}, {"keyword": "thhn wire size chart", "volume": 200, "difficulty": 10, "status": "opportunity"}, {"keyword": "xhhw wire", "volume": 500, "difficulty": None, "status": "opportunity"}]},
    {"name": "residential-cable", "theme": "SER, SEU, NM-B, and other residential wiring products",
     "keywords": [{"keyword": "ser cable", "volume": 1700, "difficulty": 0, "status": "published"}, {"keyword": "romex cable", "volume": 2100, "difficulty": 0, "status": "opportunity"}, {"keyword": "seu cable", "volume": 300, "difficulty": None, "status": "opportunity"}]},
    {"name": "underground-cable", "theme": "URD cable and direct burial wire for underground distribution",
     "keywords": [{"keyword": "urd cable", "volume": 700, "difficulty": None, "status": "published"}, {"keyword": "what is urd wire", "volume": 90, "difficulty": None, "status": "published"}, {"keyword": "direct burial wire", "volume": 3000, "difficulty": 0, "status": "opportunity"}, {"keyword": "underground electrical wire", "volume": 1600, "difficulty": 3, "status": "opportunity"}]},
    {"name": "tray-cable", "theme": "VNTC, TC-ER, and instrumentation tray cable for industrial/utility",
     "keywords": [{"keyword": "vntc tray cable", "volume": 200, "difficulty": None, "status": "published"}, {"keyword": "tray cable types", "volume": 90, "difficulty": None, "status": "opportunity"}, {"keyword": "instrumentation tray cable", "volume": 150, "difficulty": None, "status": "opportunity"}]},
    {"name": "medium-voltage", "theme": "MV-105, EPR, XLPE insulation for medium voltage distribution",
     "keywords": [{"keyword": "mv 105 cable", "volume": 150, "difficulty": None, "status": "published"}, {"keyword": "epr cable", "volume": 250, "difficulty": None, "status": "published"}, {"keyword": "medium voltage cable", "volume": 150, "difficulty": None, "status": "opportunity"}]},
    {"name": "utility-conductors", "theme": "ACSR, bare copper/aluminum conductors for utility/overhead",
     "keywords": [{"keyword": "what is acsr", "volume": 90, "difficulty": None, "status": "published"}, {"keyword": "acsr conductor", "volume": 200, "difficulty": None, "status": "opportunity"}, {"keyword": "ampacity aluminum wire", "volume": 150, "difficulty": 3, "status": "opportunity"}]},
    {"name": "wire-fundamentals", "theme": "Core concepts: jacket vs insulation, solid vs stranded, gauge, ampacity",
     "keywords": [{"keyword": "solid conductor", "volume": 90, "difficulty": None, "status": "published"}, {"keyword": "cable jacket", "volume": 350, "difficulty": None, "status": "published"}, {"keyword": "electrical wiring", "volume": 4800, "difficulty": 9, "status": "opportunity"}]},
    {"name": "cable-testing-standards", "theme": "IEEE, UL, and NEC testing standards for wire and cable",
     "keywords": [{"keyword": "ieee 1202", "volume": 80, "difficulty": None, "status": "published"}]},
    {"name": "armored-cable", "theme": "MC cable, BX cable, and armored cable for commercial/industrial",
     "keywords": [{"keyword": "mc cable", "volume": 6600, "difficulty": 0, "status": "opportunity"}, {"keyword": "armored cable", "volume": 1600, "difficulty": 1, "status": "opportunity"}, {"keyword": "bx cable", "volume": 3300, "difficulty": 0, "status": "opportunity"}]},
    {"name": "industrial-wire", "theme": "Machine tool wire, control cable, industrial-grade products",
     "keywords": [{"keyword": "machine tool wire", "volume": 500, "difficulty": None, "status": "opportunity"}]},
]


def seed():
    print("Seeding published content...")
    for article in EXISTING_ARTICLES:
        record_published_content(**article)
        print(f"  + {article['title']} ({article['primary_keyword']})")

    print(f"\nSeeding {len(INITIAL_CLUSTERS)} topical clusters...")
    for cluster in INITIAL_CLUSTERS:
        update_cluster(name=cluster["name"], theme=cluster["theme"], keywords=cluster["keywords"])
        opps = sum(1 for k in cluster["keywords"] if k["status"] == "opportunity")
        pubs = sum(1 for k in cluster["keywords"] if k["status"] == "published")
        print(f"  + {cluster['name']}: {pubs} published, {opps} opportunities")

    print(f"\nDone. {len(EXISTING_ARTICLES)} articles and {len(INITIAL_CLUSTERS)} clusters seeded.")


if __name__ == "__main__":
    seed()
