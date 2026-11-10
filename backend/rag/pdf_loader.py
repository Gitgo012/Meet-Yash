from pathlib import Path
from pypdf import PdfReader

def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {page_number}]\n{text}")
    result = "\n\n".join(pages).strip()
    if not result:
        raise ValueError(f"No extractable text found in {path.name}. It may be a scanned PDF.")
    return result
