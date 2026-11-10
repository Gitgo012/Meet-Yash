import logging
import os

from rag.db import get_connection
from rag.embeddings import embed_text

logger = logging.getLogger("meet-yash.rag")

def retrieve_resume_context(query: str, profile: str = "general", top_k: int = 5):
    """
    Returns (formatted_context, source_refs). RAG is optional: if the
    database is not configured or temporarily unavailable, chat continues
    using YASH_PROFILE and STORY_BANK.
    """
    if not os.getenv("DATABASE_URL"):
        return "", []

    try:
        query_vector = embed_text(query)
        profile_filter = None if profile in (None, "", "auto", "general") else profile

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_file, profile, content,
                           1 - (embedding <=> %s) AS similarity
                    FROM resume_chunks
                    WHERE (%s IS NULL OR profile = %s)
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (query_vector, profile_filter, profile_filter, query_vector, top_k)
                )
                rows = cur.fetchall()

        threshold = float(os.getenv("RAG_MIN_SIMILARITY", "0.30"))
        relevant = [
            row for row in rows
            if row[3] is not None and float(row[3]) >= threshold
        ]

        if not relevant:
            return "", []

        sections = []
        sources = []
        seen = set()

        for source_file, source_profile, content, similarity in relevant:
            sections.append(
                f"[Source: {source_file} | Profile: {source_profile}]\n{content}"
            )
            key = (source_file, source_profile)
            if key not in seen:
                sources.append({
                    "source_file": source_file,
                    "profile": source_profile,
                    "similarity": round(float(similarity), 3)
                })
                seen.add(key)

        return "\n\n---\n\n".join(sections), sources

    except Exception as error:
        logger.warning("Resume retrieval unavailable; continuing without RAG: %s", error)
        return "", []
