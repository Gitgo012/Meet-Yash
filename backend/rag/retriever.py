
import logging
import os

from rag.db import get_connection
from rag.embeddings import embed_text

logger = logging.getLogger("meet-yash.rag")


def retrieve_resume_context(
    query: str,
    profile: str = "general",
    top_k: int = 5
):
    """
    Retrieve relevant resume chunks using pgvector cosine similarity.

    Returns:
        tuple: (formatted_context, source_refs)

    RAG is optional. If retrieval fails, the application
    continues using YASH_PROFILE and STORY_BANK.
    """

    if not os.getenv("DATABASE_URL"):
        return "", []

    conn = None

    try:
        # 1. Generate embedding for the user's question
        query_embedding = embed_text(query)

        # 2. Convert embedding to pgvector-compatible text
        query_vector = "[" + ",".join(
            str(float(value)) for value in query_embedding
        ) + "]"

        # 3. Determine profile filter
        profile_filter = (
            None if profile in ("general", "auto") else profile
        )

        # 4. Connect to Supabase
        conn = get_connection()

        with conn.cursor() as cur:

            # 5. Retrieve semantically similar resume chunks
            cur.execute(
                """
                SELECT
                    source_file,
                    profile,
                    content,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM resume_chunks
                WHERE (%s::text IS NULL OR profile = %s)
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_vector,
                    profile_filter,
                    profile_filter,
                    query_vector,
                    top_k
                )
            )

            rows = cur.fetchall()

        # 6. Apply similarity threshold
        threshold = float(
            os.getenv("RAG_MIN_SIMILARITY", "0.30")
        )

        relevant = [
            row for row in rows
            if row[3] is not None
            and float(row[3]) >= threshold
        ]

        if not relevant:
            return "", []

        # 7. Build context and source metadata
        sections = []
        sources = []
        seen = set()

        for source_file, source_profile, content, similarity in relevant:

            sections.append(
                f"[Source: {source_file} | Profile: {source_profile}]\n"
                f"{content}"
            )

            key = (source_file, source_profile)

            if key not in seen:
                sources.append({
                    "source_file": source_file,
                    "profile": source_profile,
                    "similarity": round(float(similarity), 3)
                })

                seen.add(key)

        formatted_context = "\n\n---\n\n".join(sections)

        return formatted_context, sources

    except Exception as error:
        logger.warning(
            "Resume retrieval unavailable; continuing without RAG: %s",
            error
        )
        return "", []

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
