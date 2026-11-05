"""Re-embed and upsert the edited HQ-location website chunks into live Qdrant.

Website chunks are only auto-ingested when the collection is empty, so after
editing chunk text we must manually re-upsert the affected chunks. Upsert is
keyed by the deterministic chunk id, so this overwrites the old vectors/payload
in place (no duplicates).
"""

import sys
from backend import embeddings, vector_store
from backend.website_knowledge import WEBSITE_CHUNKS

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# The two chunks whose text mentions the HQ location (edited for the fix).
TARGET_URLS = {
    "https://www.sparrowi.com/contact-us/",   # chunk 7: office/contact
    "https://www.sparrowi.com/about-us/",      # chunk 14: global presence (also others)
}
# Only re-upsert chunks that actually mention Noida HQ so we don't touch unrelated ones.
targets = [c for c in WEBSITE_CHUNKS if "Noida" in c.text and "Headquarters" in c.text]

print(f"Re-embedding {len(targets)} HQ-location chunk(s):")
for c in targets:
    print(f"  - {c.url}  (id={c.id})")

texts = [c.text for c in targets]
vectors = embeddings.embed_batch(texts)
chunk_ids = [int(c.id, 16) % (2**63) for c in targets]
payloads = [
    {"text": c.text, "table": c.table, "chunk_type": c.chunk_type, "url": c.url}
    for c in targets
]
vector_store.upsert_chunks(chunk_ids, vectors, payloads)
print("Done.")
