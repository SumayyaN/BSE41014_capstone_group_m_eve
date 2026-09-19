"""
Download all sources listed in the Corpus/Source Register.
Saves each source to raw_docs/ - PDFs as .pdf, webpages as .html
"""
import requests
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw_docs"
RAW_DIR.mkdir(parents=True, exist_ok=True)


# Sources from the Corpus/Source Register (excluding the dynamic timetable portal,
# which cannot be embedded as static text per the register's own note)
SOURCES = [
    {
        "id": "anchor_freshers_joining_instructions",
        "title": "Freshers' Joining Instructions 2026/2027",
        "url": "https://news.mak.ac.ug/wp-content/uploads/2026/06/Makerere-Freshers-Joining-Instructions-2026-2027-Jul26-1.pdf",
        "type": "pdf",
    },
    {
        "id": "webmail_activation",
        "title": "Activating Your Makerere Webmail Account",
        "url": "https://answers.mak.ac.ug/sites/default/files/article-files/ACTIVATING%20YOUR%20MAKERERE%20WEBMAIL%20ACCOUNT.pdf",
        "type": "pdf",
    },
    {
        "id": "muele_tutorial",
        "title": "Student Tutorial on Accessing and Using MUELE",
        "url": "https://answers.mak.ac.ug/support-and-training/student-tutorial-accessing-and-using-muele",
        "type": "html",
    },
    {
        "id": "muele_create_account",
        "title": "How to Create a MUELE Account",
        "url": "https://answers.mak.ac.ug/support-and-training/how-create-muele-account",
        "type": "html",
    },
    {
        "id": "acmis_activate",
        "title": "How To Activate Your Mak Student's Portal (ACMIS)",
        "url": "https://news.mak.ac.ug/2021/12/how-to-activate-your-mak-students-portal-acmis/",
        "type": "html",
    },
    {
        "id": "acmis_mobile_app",
        "title": "Makerere University ACMIS Mobile App Guide",
        "url": "https://answers.mak.ac.ug/software-applications/makerere-university-acmis-mobile-app-guide",
        "type": "html",
    },
    {
        "id": "makair_wifi",
        "title": "New Guidelines For Connecting To MAKAIR",
        "url": "https://answers.mak.ac.ug/support-and-training/new-guidelines-connecting-makair",
        "type": "html",
    },
    {
        "id": "eduroam",
        "title": "Eduroam and access to the Metro-Eduroam Network",
        "url": "https://dicts.mak.ac.ug/articles/eduroam-and-access-metro-eduroam-network",
        "type": "html",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BSE4104-CapstoneBot/1.0)"}

def download_all():
    results = []
    for source in SOURCES:
        ext = "pdf" if source["type"] == "pdf" else "html"
        out_path = RAW_DIR / f"{source['id']}.{ext}"
        try:
            resp = requests.get(source["url"], headers=HEADERS, timeout=20)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            print(f"[OK]   {source['id']} -> {out_path.name} ({len(resp.content)} bytes)")
            results.append({**source, "status": "ok", "path": str(out_path)})
        except Exception as e:
            print(f"[FAIL] {source['id']} -> {e}")
            results.append({**source, "status": "failed", "error": str(e)})
    return results

if __name__ == "__main__":
    download_all()