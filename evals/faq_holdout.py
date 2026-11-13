"""Make a retrieval holdout that we did not write: the FAQ questions of the Getnet site, and their translation.

    uv run python -m evals.faq_holdout

Each "## question?" heading of a searched page is a query, and its page is the expected result. The English
copy has few words in common with the Portuguese pages, so it tests the embeddings more than BM25.
"""

import json
import re
from pathlib import Path

import litellm
from dotenv import load_dotenv

from agents.getnet.common import MODEL
from agents.getnet.tools.kb_search import kb_files

BATCH = 60


def faq_questions() -> list[dict]:
    cases = []
    for path in kb_files():
        text = path.read_text(encoding="utf-8")
        page = re.search(r"^source: (.+)$", text, re.M)[1]
        cases += [{"query": q.strip(), "expect": [page]} for q in re.findall(r"^## (.+\?)\s*$", text, re.M)]
    return cases


def translate(questions: list[str]) -> list[str]:
    prompt = ("Translate each Portuguese question to English. Keep product names (Get Smart, Get Conta, Pix). "
              'Reply with JSON only: {"english": [...]}, in the same order.\n' + json.dumps(questions, ensure_ascii=False))
    reply = litellm.completion(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0,
                               response_format={"type": "json_object"})
    english = json.loads(reply.choices[0].message.content)["english"]
    assert len(english) == len(questions), "the model dropped a question"
    return english


if __name__ == "__main__":
    load_dotenv()
    cases = faq_questions()
    english = [e for i in range(0, len(cases), BATCH) for e in translate([c["query"] for c in cases[i:i + BATCH]])]
    for name, rows in (("pt", cases), ("en", [{**c, "query": e} for c, e in zip(cases, english)])):
        Path(f"evals/retrieval_faq_{name}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    print(f"{len(cases)} FAQ questions written in Portuguese and English")
