"""One-time script to fix misleading Apple/BKC chunks in Qdrant.

The blog post titled "Celebrating a Milestone: Apple's First Store in India
Unveiled at BKC" was misleading — Sparrow did NOT make a model for Apple.
They made a scale model of BKC for Jio World Convention Centre.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from backend import embeddings

client = QdrantClient(host="localhost", port=6333)

# Scroll through ALL points looking for Apple/BKC mentions
target_ids = []
offset = None
while True:
    result = client.scroll(collection_name="sql_chunks", limit=100, offset=offset, with_payload=True)
    points, off = result
    for p in points:
        text = p.payload.get("text", "").lower()
        if "apple" in text and ("bkc" in text or "store" in text):
            target_ids.append(p.id)
    offset = off
    if offset is None:
        break

print(f"Found {len(target_ids)} chunks to fix...")

REPLACEMENTS = [
    # Title
    (
        "Celebrating a Milestone: Apple\u2019s First Store in India Unveiled at BKC",
        "Sparrow Interactive\u2019s Scale Model of BKC for Jio World Convention Centre",
    ),
    (
        "Celebrating a Milestone: Apple's First Store in India Unveiled at BKC",
        "Sparrow Interactive's Scale Model of BKC for Jio World Convention Centre",
    ),
    # Page title metadata
    (
        "Page title: Celebrating a Milestone: Apple\u2019s First Store in India Unveiled at BKC",
        "Page title: Sparrow Interactive\u2019s Scale Model of BKC for Jio World Convention Centre",
    ),
    (
        "Page title: Celebrating a Milestone: Apple's First Store in India Unveiled at BKC",
        "Page title: Sparrow Interactive's Scale Model of BKC for Jio World Convention Centre",
    ),
    # Misleading Apple CEO paragraph (smart quotes)
    (
        "In a momentous occasion that marked a significant milestone for both the city of Mumbai "
        "and the team at Sparrow Interactive, Apple CEO Tim Cook inaugurated India\u2019s first-ever "
        "Apple store at the prestigious Bandra Kurla Complex (BKC). The occasion was met with "
        "enthusiasm from over 5,000 Apple enthusiasts, and the event itself exuded a vibrant "
        "energy, reflecting the incredible spirit of Mumbai.",
        "Sparrow Interactive created a groundbreaking scale model of the Bandra Kurla Complex (BKC) "
        "area for the Jio World Convention Centre. This model captures the vibrant culture, modern "
        "architecture, and bustling energy of Mumbai\u2019s BKC district.",
    ),
    # Same paragraph (straight quotes)
    (
        "In a momentous occasion that marked a significant milestone for both the city of Mumbai "
        "and the team at Sparrow Interactive, Apple CEO Tim Cook inaugurated India's first-ever "
        "Apple store at the prestigious Bandra Kurla Complex (BKC). The occasion was met with "
        "enthusiasm from over 5,000 Apple enthusiasts, and the event itself exuded a vibrant "
        "energy, reflecting the incredible spirit of Mumbai.",
        "Sparrow Interactive created a groundbreaking scale model of the Bandra Kurla Complex (BKC) "
        "area for the Jio World Convention Centre. This model captures the vibrant culture, modern "
        "architecture, and bustling energy of Mumbai's BKC district.",
    ),
    # Section heading
    ("A Connection to Innovation", "Creating a Landmark Scale Model"),
    # Model attribution fix
    (
        "When we set out to create a groundbreaking scale model for Bandra Kurla Complex",
        "When we set out to create a groundbreaking scale model of Bandra Kurla Complex for Jio World Convention Centre",
    ),
    # Inspired Design section (smart quotes)
    (
        "As the curtains rose on the Apple store at BKC, it was evident that the design was "
        "meticulously curated to reflect the city\u2019s essence. The inspiration drawn from "
        "Mumbai\u2019s iconic black-and-yellow cabs found its way into the store\u2019s architecture, "
        "creating a connection between the technology giant and the heartbeat of the city.",
        "Our scale model of BKC was meticulously curated to reflect the area\u2019s essence, "
        "capturing the modern architecture, infrastructure, and vibrant energy of Mumbai\u2019s "
        "most prestigious business district.",
    ),
    # Inspired Design (straight quotes)
    (
        "As the curtains rose on the Apple store at BKC, it was evident that the design was "
        "meticulously curated to reflect the city's essence. The inspiration drawn from "
        "Mumbai's iconic black-and-yellow cabs found its way into the store's architecture, "
        "creating a connection between the technology giant and the heartbeat of the city.",
        "Our scale model of BKC was meticulously curated to reflect the area's essence, "
        "capturing the modern architecture, infrastructure, and vibrant energy of Mumbai's "
        "most prestigious business district.",
    ),
    # Apple sustainability section (smart quotes)
    (
        "Our values at Sparrow Interactive align seamlessly with Apple\u2019s commitment to "
        "sustainability and renewable energy. Witnessing the Apple BKC store, with its dedicated "
        "solar array and zero reliance on fossil fuels, being operationally carbon neutral, left "
        "us proud. It echoed our belief in using innovative technology to create a greener, more "
        "sustainable future.",
        "At Sparrow Interactive, we believe in using innovative technology to create experiences "
        "that inspire. Our scale model of BKC for Jio World Convention Centre reflects our "
        "dedication to precision, innovation, and immersive phygital solutions.",
    ),
    # Apple sustainability (straight quotes)
    (
        "Our values at Sparrow Interactive align seamlessly with Apple's commitment to "
        "sustainability and renewable energy. Witnessing the Apple BKC store, with its dedicated "
        "solar array and zero reliance on fossil fuels, being operationally carbon neutral, left "
        "us proud. It echoed our belief in using innovative technology to create a greener, more "
        "sustainable future.",
        "At Sparrow Interactive, we believe in using innovative technology to create experiences "
        "that inspire. Our scale model of BKC for Jio World Convention Centre reflects our "
        "dedication to precision, innovation, and immersive phygital solutions.",
    ),
    # Enriching Lives heading
    ("Enriching Lives Through Innovation", "Creating Immersive Experiences"),
    # Tim Cook quote and attribution
    (
        "At Apple, our mission is to enrich lives and empower people around the world.",
        "At Sparrow Interactive, our mission is to create immersive experiences that enrich lives and transform spaces.",
    ),
    # Tim Cook visit (smart quotes)
    (
        "Tim Cook\u2019s visit and his words resonated deeply with our vision at Sparrow Interactive.",
        "This project deeply reflects our vision at Sparrow Interactive.",
    ),
    (
        "Tim Cook's visit and his words resonated deeply with our vision at Sparrow Interactive.",
        "This project deeply reflects our vision at Sparrow Interactive.",
    ),
    # The full enriching lives sentence (smart quotes)
    (
        '\u201cAt Apple, our mission is to enrich lives and empower people around the world,\u201d '
        "he expressed. That mission resonates with us too \u2014 our aim is to create immersive "
        "experiences that enrich the lives of individuals, adding a touch of magic to the spaces "
        "they explore.",
        "Our aim is to create immersive experiences that enrich the lives of individuals, "
        "adding a touch of magic to the spaces they explore.",
    ),
    # Tim Cook / Apple attribution line
    ("Tim Cook\nApple", "Sparrow Interactive"),
    # Shared Vision heading
    ("Inspired Design, Shared Vision", "Precision Design, Immersive Vision"),
    ("A Shared Commitment to Sustainability", "Commitment to Innovation"),
]

updated = 0
for cid in target_ids:
    result = client.retrieve(collection_name="sql_chunks", ids=[cid], with_payload=True)
    if not result:
        continue
    point = result[0]
    text = point.payload["text"]
    original = text

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    if text != original:
        new_vector = embeddings.embed_text(text)
        payload = dict(point.payload)
        payload["text"] = text
        client.upsert(
            collection_name="sql_chunks",
            points=[PointStruct(id=cid, vector=new_vector, payload=payload)],
        )
        updated += 1
        print(f"  Updated chunk {cid}")
    else:
        print(f"  No text changes for chunk {cid}")

print(f"\nDone: {updated}/{len(target_ids)} chunks updated")
