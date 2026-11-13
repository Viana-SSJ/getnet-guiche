import json
from datetime import date
from pathlib import Path

import pytest

from agents.getnet.chat import INJECTION_LIMIT
from agents.getnet.grounding import ungrounded
from evals import injection
from evals.judge import conformal_threshold, corrupt

TODAY = date(2026, 11, 9)
RECEIVABLES = {"tool": "support.get_receivables", "args": {"sale_date": "2026-11-08"},
               "result": {"receivables": [{"net": 45.12, "payment_date": "2026-11-09"}, {"net": 116.77, "payment_date": "2026-11-10"}]}}
SEARCH = {"tool": "knowledge.search_kb", "args": {"query": "crediário"},
          "result": {"results": [{"text": "Parcele em até 48x. Taxa única de 3,45%. Ligue 4003 4000, das 6h às 22h."}]}}


def check(answer, evidence=(RECEIVABLES, SEARCH)):
    return ungrounded(answer, list(evidence), "Phone 4002-4000 (capitals).", TODAY)


def test_numbers_from_the_tools_are_grounded_in_any_format():
    assert check("Você recebe R$ 45,12 em 09/11/2026 e R$ 116,77 amanhã, 10/11.") == []
    assert check("Up to 48 installments, a 3.45% fee; call 4003-4000 or 4002-4000 from 6h.") == []
    assert check("Ligue 4002–4000 ou 4003 4000.") == []  # an en dash, a no-break space


def test_a_total_of_account_amounts_is_grounded():
    assert check("Total: R$ 161,89.") == []
    assert check("Total: R$ 51,45.", [SEARCH]) == ["51,45"]  # search results are not added up


def test_a_changed_or_invented_number_is_not():
    assert check("Você recebe R$ 45,13.") == ["45,13"]
    assert check("Parcele em até 49x, ligue 4004-4000, aviso de 30 dias.") == ["49", "4004-4000", "30"]


def test_a_date_in_a_file_name_is_grounded():
    contract = {"tool": "knowledge.search_kb", "args": {}, "result": {"results": [{"title": "20260813_contrato.pdf"}]}}
    assert check("O contrato de 13/08/2026 diz isso.", [contract]) == []


def test_small_counts_years_and_nearby_dates_are_free():
    assert check("Siga os 3 passos. Em 2026, hoje 09/11 e ontem 08/11.", []) == []


def test_corrupt_changes_one_number_from_the_tools():
    answer = "Você recebe R$ 45,12 em 09/11."
    changed = corrupt(answer, "45,12 45.12")
    assert changed != answer and "45,12" not in changed and "09/11" in changed
    assert corrupt("Olá! Posso ajudar?", "45,12") is None


def test_a_number_before_a_slash_and_a_word_or_inside_a_name_is_grounded():
    rent = {"tool": "knowledge.search_kb", "args": {}, "result": {"results": [
        {"title": "202403_Termo_Get_Conta.pdf", "text": "Aluguel de R$ 14,90/mês acima de R$ 2.000; mais de 100 apps."}]}}
    assert check("O aluguel cai para R$ 14,90 por mês (termo 202403); são mais de 100 apps.", [rent]) == []
    assert check("Em 09/11 o aluguel é R$ 15,90.", [rent]) == ["15,90"]


def test_the_conformal_threshold_flags_at_least_one_minus_alpha_of_the_unfaithful_answers():
    scores = [0.1 * i for i in range(1, 10)]  # 9 unfaithful answers
    assert conformal_threshold(scores, alpha=0.2) == pytest.approx(0.8)  # ceil(10 * 0.8) = the 8th smallest
    assert conformal_threshold(scores, alpha=0.5) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        conformal_threshold(scores, alpha=0.05)  # 9 answers cannot give 95 %


def test_the_injection_limit_of_the_api_is_the_calibrated_one():
    rows = json.loads(sorted(Path("evals/results").glob("injection-*.json"))[-1].read_text())["rows"]
    assert INJECTION_LIMIT == injection.threshold(rows)
