"""
Extract plain text from the raw PDF/HTML sources downloaded by download_sources.py.
Saves one .txt file per source into data/extracted/, plus a manifest.json
recording provenance (title, url, source id) for each - this is what lets us
cite the correct source later when answering a question.
"""
import json
from pathlib import Path

from pypdf import PdfReader
from bs4 import BeautifulSoup

from download_sources import SOURCES

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw_docs"
EXTRACTED_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    # Remove elements that aren't real page content
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse excess blank lines left over from stripped tags
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def extract_all():
    manifest = []
    for source in SOURCES:
        ext = "pdf" if source["type"] == "pdf" else "html"
        raw_path = RAW_DIR / f"{source['id']}.{ext}"
        if not raw_path.exists():
            print(f"[SKIP] {source['id']} - raw file not found, run download_sources.py first")
            continue

        try:
            if source["type"] == "pdf":
                text = extract_pdf_text(raw_path)
            else:
                text = extract_html_text(raw_path)

            text = text.strip()
            if not text:
                print(f"[WARN] {source['id']} - extracted empty text, check the raw file manually")
                continue

            out_path = EXTRACTED_DIR / f"{source['id']}.txt"
            out_path.write_text(text, encoding="utf-8")

            manifest.append({
                "id": source["id"],
                "title": source["title"],
                "url": source["url"],
                "extracted_path": str(out_path),
                "char_count": len(text),
            })
            print(f"[OK]   {source['id']} -> {out_path.name} ({len(text)} chars)")

        except Exception as e:
            print(f"[FAIL] {source['id']} -> {e}")

    manifest_path = EXTRACTED_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written to {manifest_path} ({len(manifest)} sources)")
    return manifest


if __name__ == "__main__":
    extract_all()