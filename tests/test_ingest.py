import pytest

from ingest.convert import Doc, drop_boilerplate, html_to_doc
from ingest.crawl import FetchError, check_url

PAGE = """
<html><head><title>Arquivos pix - Getnet</title></head><body>
<header><nav>Crediário Parcelamento em até 48x</nav></header>
<a class="c-more-answers__question" href="#">Preciso de conta?</a>
<div class="o-modal__content o-modal__content--faq">
  <div class="o-modal__title">Preciso de conta?</div>
  <div class="o-modal__text">Sim, uma Get Conta.</div>
</div>
<div style="display:none">hidden promo</div>
<footer>Ligue 4002-4000</footer>
</body></html>
"""


def test_faq_becomes_heading_and_answer_without_menu():
    doc = html_to_doc(PAGE, "https://site.getnet.com.br/duvidas/pix/")
    assert doc.kind == "faq"
    assert "## Preciso de conta?\n\nSim, uma Get Conta." in doc.markdown
    assert doc.markdown.count("Preciso de conta?") == 1
    for noise in ("Parcelamento em até 48x", "4002-4000", "hidden promo"):
        assert noise not in doc.markdown


def test_boilerplate_removes_shared_lines_but_keeps_headings_and_content():
    docs = [Doc(f"u{n}", "t", "page", f"# Title\n\nFale conosco\n\nUnique {n}\n") for n in range(4)]
    cleaned, removed = drop_boilerplate(docs)
    assert removed == ["Fale conosco"]
    assert all("# Title" in d.markdown and "Fale conosco" not in d.markdown for d in cleaned)
    assert "Unique 2" in cleaned[2].markdown


def test_boilerplate_ignores_pdfs_when_counting():
    pages = [Doc(f"p{n}", "t", "page", f"Pessoa Física (CPF)\n\nPage {n}\n") for n in range(3)]
    pdfs = [Doc(f"f{n}", "t", "pdf", f"Pessoa Física (CPF)\n\nPdf {n}\n") for n in range(10)]
    cleaned, removed = drop_boilerplate(pages + pdfs)
    assert removed == ["Pessoa Física (CPF)"]
    assert all("Pessoa Física" in d.markdown for d in cleaned if d.kind == "pdf")


@pytest.mark.parametrize("url", [
    "https://evil.example.com/",
    "http://site.getnet.com.br/",  # plain HTTP
    "https://site.getnet.com.br.evil.com/",
    "https://169.254.169.254/latest/meta-data/",
])
def test_crawler_refuses_hosts_outside_the_allow_list(url):
    with pytest.raises(FetchError):
        check_url(url)
