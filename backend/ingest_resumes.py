import argparse
import re
from pathlib import Path

from rag.chunker import chunk_text
from rag.db import get_connection
from rag.embeddings import embed_text
from rag.pdf_loader import extract_pdf_text

PROFILE_RULES = [
    (("da_resume", "data_analyst", "_da_", "analytics"), "data_analyst"),
    (("junior_ds", "data_scientist", "_ds_"), "data_scientist"),
    (("de_resume", "data_engineer", "_de_"), "data_engineer"),
    (("gen_ai", "genai", "generative_ai"), "genai"),
]

def infer_profile(filename: str) -> str:
    normalized = filename.lower().replace("-", "_").replace(" ", "_")
    for markers, profile in PROFILE_RULES:
        if any(marker in normalized for marker in markers):
            return profile
    raise ValueError(
        f"Cannot infer role profile from '{filename}'. Rename it with one of "
        "these hints: DA, Junior_DS, DE, GenAI, or add a mapping in ingest_resumes.py."
    )

def ingest_file(path: Path, profile: str):
    text = extract_pdf_text(path)
    chunks = chunk_text(text)
    prepared = []
    for index, chunk in enumerate(chunks):
        prepared.append((index, chunk, embed_text(chunk)))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resume_chunks WHERE source_file = %s", (path.name,))
            for index, chunk, vector in prepared:
                cur.execute(
                    """
                    INSERT INTO resume_chunks
                        (profile, source_file, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_file, chunk_index)
                    DO UPDATE SET
                        profile = EXCLUDED.profile,
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                    """,
                    (profile, path.name, index, chunk, vector)
                )
        conn.commit()

    print(f"Ingested {path.name}: profile={profile}, chunks={len(prepared)}")

def main():
    parser = argparse.ArgumentParser(description="Ingest role-specific PDF resumes into Supabase pgvector.")
    parser.add_argument("--directory", default="resumes", help="Directory containing resume PDFs")
    parser.add_argument("--profile", default=None, help="Optional profile override for every PDF in this run")
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        raise SystemExit(f"Resume directory does not exist: {directory.resolve()}")

    pdfs = sorted(directory.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF resumes found in {directory.resolve()}")

    for pdf in pdfs:
        profile = args.profile or infer_profile(pdf.name)
        ingest_file(pdf, profile)

if __name__ == "__main__":
    main()
