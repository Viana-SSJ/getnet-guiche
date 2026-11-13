"""Hybrid search over kb/: BM25 finds product names and rare words, embeddings find paraphrases."""

import hashlib
import json
import logging
import re
from functools import cache
from pathlib import Path

import bm25s
import numpy as np
import Stemmer
from fastembed import TextEmbedding

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
KB_DIR = ROOT / "kb"
INDEX_DIR = ROOT / ".index"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 6
RRF_K = 60  # the usual constant for reciprocal rank fusion
CHUNK_WORDS, OVERLAP_WORDS = 250, 25
# Documents that do not help a merchant: press releases, internal policies, reports, aggregates.
EXCLUDE = re.compile(
    r"^(INDEX|REPORT|blog|carreiras|imprensa|patrocinios|esg|guia-digital-marca|report-vulnerability"
    r"|duvidas|redirect-app-getnet-brasil|get-code|downloads/politicas|downloads/regulamentos|downloads/documento-socioambiental)\.md$"
    r"|^pdf/.*(aprovad|nota|relese|relatorio|ouvidori|iguldade|lei[-_]|pocket|patrocin|mapa-midi|politica"
    r"|regulamento|fornecedores|conduta|industri|estrategi|gn\.tec|voluntari|3ds-|extrato-eletronico|manul_v10_ee|tabela-ws)"
)


def kb_files() -> list[Path]:
    return sorted(p for p in KB_DIR.rglob("*.md") if not EXCLUDE.search(str(p.relative_to(KB_DIR))))


def split(path: Path) -> list[dict]:
    """Cut one KB file into chunks: one per heading, and long sections into windows."""
    head, body = path.read_text(encoding="utf-8")[4:].split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    title, url = meta.get("title", path.stem).strip('"'), meta.get("source", "")
    chunks = []
    for section in re.split(r"\n(?=#{1,3} )", body):
        words = section.split()
        for start in range(0, len(words), CHUNK_WORDS):
            text = " ".join(words[max(0, start - OVERLAP_WORDS):start + CHUNK_WORDS])
            if len(text) > 20:
                chunks.append({"title": title, "url": url, "text": text})
    return chunks


class Index:
    def __init__(self):
        files = kb_files()
        digest = hashlib.sha256(EMBEDDING_MODEL.encode() + b"".join(p.read_bytes() for p in files)).hexdigest()
        self.model = TextEmbedding(EMBEDDING_MODEL, cache_dir=str(INDEX_DIR / "models"))
        cached = INDEX_DIR / f"{digest[:16]}.json"
        if cached.exists():
            self.chunks = json.loads(cached.read_text())
            self.vectors = np.load(cached.with_suffix(".npy"))
        else:
            log.info("Building the index from %d files", len(files))
            unique = {c["text"]: c for path in files for c in split(path)}
            self.chunks = list(unique.values())
            self.vectors = self._embed([f'{c["title"]}\n{c["text"]}' for c in self.chunks])
            INDEX_DIR.mkdir(exist_ok=True)
            cached.write_text(json.dumps(self.chunks, ensure_ascii=False))
            np.save(cached.with_suffix(".npy"), self.vectors)
        self.stemmer = Stemmer.Stemmer("portuguese")
        self.bm25 = bm25s.BM25()
        self.bm25.index(self._tokens([f'{c["title"]}\n{c["text"]}' for c in self.chunks]), show_progress=False)

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.array(list(self.model.embed(texts, batch_size=64)))  # keeps the Docker build under 1 GB
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def _tokens(self, texts: list[str]):
        return bm25s.tokenize(texts, stopwords="pt", stemmer=self.stemmer, show_progress=False)

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        keyword, _ = self.bm25.retrieve(self._tokens([query]), k=k * 3, show_progress=False)
        meaning = np.argsort(-(self.vectors @ self._embed([query])[0]))[: k * 3]
        scores: dict[int, float] = {}
        for ranking in (keyword[0], meaning):
            for rank, i in enumerate(ranking):
                scores[int(i)] = scores.get(int(i), 0) + 1 / (RRF_K + rank + 1)
        best = sorted(scores, key=scores.get, reverse=True)[:k]
        return [self.chunks[i] for i in best]


@cache
def load_index() -> Index:
    return Index()


def search_kb(query: str) -> dict:
    """Search the Getnet knowledge base: official site, FAQ, machine manuals and terms.

    Use it for any question about Getnet products, rates, machines, Pix, Get Conta, sales advance,
    payment link, crediário or how-to steps.

    Args:
        query: What to look for, in Portuguese.

    Returns:
        The best passages, each with the title and URL of its document.
    """
    return {"results": load_index().search(query)}
