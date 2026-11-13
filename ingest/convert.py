"""Convert HTML and PDF to Markdown, and remove the site layout and repeated text."""

import io
import re
from collections import Counter
from dataclasses import dataclass

from bs4 import BeautifulSoup
from markdownify import markdownify
from pypdf import PdfReader


@dataclass
class Doc:
    url: str
    title: str
    kind: str  # "page", "faq" or "pdf"
    markdown: str


def drop_layout(soup: BeautifulSoup) -> None:
    """Remove the site menu, header, footer and non-text elements."""
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form",
                     "header", "nav", "footer", "img", "button"]):
        tag.decompose()


def faq_to_sections(soup: BeautifulSoup) -> None:
    """Turn each FAQ pop-up into a '## question' heading and its answer, without the duplicate link."""
    for link in soup.select("a.c-more-answers__question"):
        link.decompose()
    for modal in soup.select(".o-modal__content--faq"):
        title = modal.select_one(".o-modal__title")
        text = modal.select_one(".o-modal__text")
        if not (title and text):
            continue
        section = soup.new_tag("section")
        heading = soup.new_tag("h2")
        heading.string = title.get_text(" ", strip=True)
        section.append(heading)
        section.append(text)
        modal.replace_with(section)


def drop_hidden(soup: BeautifulSoup) -> None:
    """Remove elements that the page hides from the reader."""
    for tag in soup.select('[hidden], [aria-hidden="true"], [style*="display:none"], [style*="display: none"]'):
        tag.decompose()


def tidy(markdown: str) -> str:
    """Strip trailing spaces and collapse runs of blank lines."""
    lines = [line.rstrip() for line in markdown.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def drop_repeated_lines(markdown: str) -> str:
    """Keep only the first copy of a line inside one document."""
    seen, kept = set(), []
    for line in markdown.splitlines():
        key = line.strip()
        if key and not key.startswith("#") and key in seen:
            continue
        seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def html_to_doc(html: str, url: str) -> Doc:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    kind = "faq" if soup.select(".o-modal__content--faq") else "page"
    drop_layout(soup)
    faq_to_sections(soup)
    drop_hidden(soup)
    markdown = markdownify(str(soup.body or soup), heading_style="ATX", strip=["a"])
    return Doc(url, title, kind, tidy(drop_repeated_lines(markdown)))


def pdf_to_doc(data: bytes, url: str) -> Doc:
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    title = (reader.metadata.title if reader.metadata else None) or url.rsplit("/", 1)[-1]
    markdown = "\n\n".join(f"## Page {n}\n\n{text}" for n, text in enumerate(pages, 1) if text)
    return Doc(url, title, "pdf", tidy(markdown))


def drop_boilerplate(docs: list[Doc], share: float = 0.3, minimum: int = 3) -> tuple[list[Doc], list[str]]:
    """Remove the lines that are in `share` or more of the web pages, such as banners. PDFs are not changed."""
    pages = [doc for doc in docs if doc.kind != "pdf"]
    frequency = Counter()
    for doc in pages:
        frequency.update({line.strip() for line in doc.markdown.splitlines() if line.strip()})
    limit = max(minimum, share * len(pages))
    removed = {line for line, count in frequency.items() if count >= limit and not line.startswith("#")}
    cleaned = []
    for doc in docs:
        if doc.kind != "pdf":
            lines = [line for line in doc.markdown.splitlines() if line.strip() not in removed]
            doc = Doc(doc.url, doc.title, doc.kind, tidy("\n".join(lines)))
        cleaned.append(doc)
    return cleaned, sorted(removed)
