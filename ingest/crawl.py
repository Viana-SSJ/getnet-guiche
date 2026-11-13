"""Crawl the Getnet site, convert each page and PDF, and write the knowledge base to kb/."""

import re
import shutil
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .convert import Doc, html_to_doc, pdf_to_doc

KB_DIR = Path("kb")
ALLOWED_HOSTS = {"site.getnet.com.br", "www.getnet.com.br", "getnet.com.br"}
START_URLS = [
    "https://site.getnet.com.br/",
    "https://site.getnet.com.br/duvidas/",
    "https://site.getnet.com.br/downloads/documentos-produtos/",
    "https://site.getnet.com.br/boas-vindas/manual-maquinas/",
]
# Blog posts are marketing text.
BLOG_SITEMAP = "https://site.getnet.com.br/post-sitemap.xml"
SKIP = re.compile(
    r"/wp-(admin|json|content/themes)|/feed/|/tag/|/category/|/author/|/page/\d"
    r"|\.(png|jpe?g|webp|gif|svg|css|js|ico|woff2?|zip|mp4)$"
)
MAX_PAGES = 250
MAX_BYTES = 20 * 1024 * 1024
DELAY_SECONDS = 0.5


class FetchError(Exception):
    pass


def check_url(url: str) -> None:
    """Refuse URLs outside the Getnet hosts, so the crawler never leaves the site."""
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise FetchError(f"URL not allowed: {url}")


def fetch(client: httpx.Client, url: str) -> httpx.Response:
    check_url(url)
    time.sleep(DELAY_SECONDS)
    reply = client.get(url)
    check_url(str(reply.url))  # a redirect can leave the allowed hosts
    if reply.status_code != 200:
        raise FetchError(f"HTTP {reply.status_code}")
    if len(reply.content) > MAX_BYTES:
        raise FetchError("too large")
    return reply


def links(base: str, html: str) -> list[str]:
    found = []
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urljoin(base, link["href"]).split("#")[0].split("?")[0]
        parts = urlparse(url)
        if parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS and not SKIP.search(parts.path):
            found.append(url)
    return found


def crawl() -> tuple[list[Doc], list[str]]:
    """Breadth-first crawl from START_URLS. Returns the documents and the errors."""
    docs, errors = [], []
    with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": "getnet-kb crawler"}) as client:
        sitemap = fetch(client, BLOG_SITEMAP).text
        seen = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
        queue = list(START_URLS)
        while queue and len(docs) < MAX_PAGES:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                reply = fetch(client, url)
            except (FetchError, httpx.HTTPError) as error:
                errors.append(f"{url}: {error}")
                continue
            seen.add(str(reply.url))
            kind = reply.headers.get("content-type", "").split(";")[0].strip()
            if kind == "application/pdf":
                doc = pdf_to_doc(reply.content, str(reply.url))
            elif kind == "text/html":
                doc = html_to_doc(reply.text, str(reply.url))
                queue += [found for found in links(str(reply.url), reply.text) if found not in seen]
            else:
                continue
            if not doc.markdown.strip():
                errors.append(f"{url}: no text (scanned PDF or empty page)")
                continue
            docs.append(doc)
            print(f"[{len(docs)}] {doc.kind:4} {reply.url}")
    return docs, errors


def file_name(url: str) -> str:
    """Map a URL to a file in kb/, for example duvidas/pix.md or pdf/manual.md."""
    path = urlparse(url).path.strip("/")
    if path.lower().endswith(".pdf"):
        return "pdf/" + re.sub(r"[^\w.-]", "-", path.rsplit("/", 1)[-1])[:-4].lower() + ".md"
    return (re.sub(r"[^\w/-]", "-", path) or "home") + ".md"


def clean_title(title: str) -> str:
    title = re.sub(r"^Arquivos\s+", "", title)
    return re.sub(r"\s+[-|]\s+Getnet$", "", title).strip().replace('"', "'")


def write(docs: list[Doc], removed: list[str], errors: list[str]) -> None:
    """Replace kb/ with these documents. Also write an index and a report of what the filters did."""
    shutil.rmtree(KB_DIR, ignore_errors=True)
    today = date.today().isoformat()
    rows = []
    for doc in docs:
        path = KB_DIR / file_name(doc.url)
        path.parent.mkdir(parents=True, exist_ok=True)
        title = clean_title(doc.title)
        front = f'---\ntitle: "{title}"\nsource: {doc.url}\nkind: {doc.kind}\nfetched: {today}\n---\n\n'
        path.write_text(f"{front}# {title}\n\n{doc.markdown}", encoding="utf-8")
        rows.append(f"| [{title}]({path.relative_to(KB_DIR)}) | {doc.kind} | {len(doc.markdown.split())} |")
    index = "# Getnet knowledge base\n\n| Document | Kind | Words |\n|---|---|---|\n" + "\n".join(sorted(rows))
    (KB_DIR / "INDEX.md").write_text(index + "\n", encoding="utf-8")
    report = [f"# Ingestion report ({today})", "", f"Documents: {len(docs)}", "",
              f"## Boilerplate lines removed ({len(removed)})", "", *[f"- `{line}`" for line in removed],
              "", f"## Errors ({len(errors)})", "", *[f"- {error}" for error in errors]]
    (KB_DIR / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
