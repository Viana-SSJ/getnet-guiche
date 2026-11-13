from datetime import date, timedelta
from types import SimpleNamespace

from agents.getnet.tools.customer import add_business_days, get_receivables, get_terminal_status
from agents.getnet.tools.web import get_exchange_rate, get_weather

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def ctx(user_id):
    return SimpleNamespace(user_id=user_id)


def test_receivables_use_the_user_from_the_context_only():
    mine = get_receivables(YESTERDAY, ctx("cliente1988"))
    other = get_receivables(YESTERDAY, ctx("cliente2000"))
    assert {r["transaction"] for r in mine["receivables"]} == {"T1001", "T1002", "T1003", "T1004"}
    assert {r["transaction"] for r in other["receivables"]} == {"T9001"}


def test_unknown_user_gets_no_data():
    assert "error" in get_receivables(YESTERDAY, ctx("nobody"))
    assert "error" in get_terminal_status(ctx("nobody"))


def test_receivables_exclude_declined_sales_and_compute_fees():
    rows = {r["transaction"]: r for r in get_receivables(YESTERDAY, ctx("cliente1988"))["receivables"]}
    assert "T1005" not in rows  # declined
    assert rows["T1002"]["fee"] == 3.23 and rows["T1002"]["net"] == 116.77
    assert rows["T1004"]["payment_date"] == YESTERDAY  # Pix is paid on the same day


def test_business_days_skip_weekends():
    friday = date(2026, 11, 6)
    assert add_business_days(friday, 1) == date(2026, 11, 9)
    assert add_business_days(friday, 2) == date(2026, 11, 10)


def test_tools_refuse_bad_input_without_a_network_call():
    assert "error" in get_exchange_rate("euro; DROP")
    assert "error" in get_weather("Porto Alegre", "tomorrow")
    assert "error" in get_weather("Porto Alegre", "2000-01-01")


def fake_http(monkeypatch, handler):
    """Route the web tools' HTTP calls to `handler`, offline."""
    import httpx

    from agents.getnet.tools import web

    real = httpx.Client
    monkeypatch.setattr(web.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_exchange_rate_falls_back_to_the_ecb_when_ptax_is_down(monkeypatch):
    import httpx

    def handler(request):
        if "bcb.gov.br" in request.url.host:
            return httpx.Response(502, text="<html>Bad Gateway</html>")
        return httpx.Response(200, json={"date": "2026-11-06", "rates": {"BRL": 6.14}})

    fake_http(monkeypatch, handler)
    rate = get_exchange_rate("EUR")
    assert rate["rate_brl"] == 6.14 and "European Central Bank" in rate["source"]


def test_tools_return_an_error_instead_of_raising_when_apis_are_down(monkeypatch):
    import httpx

    fake_http(monkeypatch, lambda request: httpx.Response(502, text="<html>down</html>"))
    assert "error" in get_exchange_rate("EUR")
    assert "error" in get_weather("Porto Alegre", date.today().isoformat())

