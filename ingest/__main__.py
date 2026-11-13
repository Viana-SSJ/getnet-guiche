"""Crawl the Getnet site and rewrite kb/. Run: make ingest"""

from .convert import drop_boilerplate
from .crawl import crawl, write

if __name__ == "__main__":
    docs, errors = crawl()
    docs, removed = drop_boilerplate(docs)
    write(docs, removed, errors)
    print(f"{len(docs)} documents, {len(removed)} boilerplate lines removed, {len(errors)} errors. See kb/REPORT.md.")
