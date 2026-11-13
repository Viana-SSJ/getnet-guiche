"""Free public tools: web search, weather and exchange rates. No API key is needed."""

import re
from datetime import date, timedelta

import httpx
from ddgs import DDGS

TIMEOUT = 15


class Unavailable(Exception):
    """A public API failed: timeout, HTTP error or a reply that is not JSON."""


def _get_json(client: httpx.Client, url: str, params: dict) -> dict:
    try:
        reply = client.get(url, params=params)
        reply.raise_for_status()
        return reply.json()
    except (httpx.HTTPError, ValueError) as error:
        raise Unavailable(f"{url.split('/')[2]}: {error}") from error


WEATHER_CODES = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina com geada", 51: "garoa fraca", 53: "garoa", 55: "garoa forte",
    61: "chuva fraca", 63: "chuva", 65: "chuva forte", 80: "pancadas de chuva fracas",
    81: "pancadas de chuva", 82: "pancadas de chuva fortes", 95: "trovoadas", 96: "trovoadas com granizo",
}


def web_search(query: str) -> dict:
    """Search the public web. Use it only for general questions that are not about Getnet products.

    Args:
        query: The search terms.

    Returns:
        Up to 5 results with title, URL and snippet.
    """
    try:
        results = DDGS().text(query, max_results=5, region="br-pt")
    except Exception as error:  # the search service is unofficial and can refuse requests
        return {"error": f"Web search failed: {error}"}
    return {"results": [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]}


def get_weather(city: str, day: str) -> dict:
    """Get the weather forecast for a city on one day (up to 7 days ahead). Source: Open-Meteo.

    Args:
        city: The city name, for example "Porto Alegre".
        day: The day, in the format YYYY-MM-DD.

    Returns:
        Minimum and maximum temperature, rain probability and a short description.
    """
    try:
        wanted = date.fromisoformat(day)
    except ValueError:
        return {"error": "Use the format YYYY-MM-DD for day."}
    if not 0 <= (wanted - date.today()).days <= 7:
        return {"error": "The forecast covers today and the next 7 days only."}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            found = _get_json(client, "https://geocoding-api.open-meteo.com/v1/search",
                              {"name": city, "count": 1, "language": "pt"}).get("results")
            if not found:
                return {"error": f"City not found: {city}"}
            place = found[0]
            daily = _get_json(client, "https://api.open-meteo.com/v1/forecast", {
                "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                "start_date": day, "end_date": day,
            })["daily"]
    except Unavailable as error:
        return {"error": f"The weather service is unavailable now ({error})."}
    return {
        "city": f'{place["name"]}, {place.get("admin1", "")}, {place.get("country", "")}',
        "day": day,
        "min_c": daily["temperature_2m_min"][0],
        "max_c": daily["temperature_2m_max"][0],
        "rain_probability_pct": daily["precipitation_probability_max"][0],
        "description": WEATHER_CODES.get(daily["weather_code"][0], "sem descrição"),
        "source": "https://open-meteo.com",
    }


def get_exchange_rate(currency: str) -> dict:
    """Get the latest exchange rate of a currency to the Brazilian real.

    The source is the Banco Central do Brasil (PTAX). When it is down, the source is the
    European Central Bank reference rate (Frankfurter).

    Args:
        currency: The ISO code, for example "EUR" or "USD".

    Returns:
        The rate in BRL, the time of the quote and the source.
    """
    code = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        return {"error": "Use a 3-letter currency code, for example EUR."}
    with httpx.Client(timeout=TIMEOUT) as client:
        for source in (_ptax, _ecb):
            try:
                return source(client, code)
            except (Unavailable, KeyError, IndexError):
                continue
    return {"error": f"No exchange-rate service answered for {code}. Try again later."}


def _ptax(client: httpx.Client, code: str) -> dict:
    end = date.today()
    start = end - timedelta(days=7)
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
           "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)")
    params = {"@moeda": f"'{code}'", "@dataInicial": f"'{start:%m-%d-%Y}'",
              "@dataFinalCotacao": f"'{end:%m-%d-%Y}'", "$format": "json"}
    last = _get_json(client, url, params)["value"][-1]
    return {
        "currency": code,
        "buy_brl": last["cotacaoCompra"],
        "sell_brl": last["cotacaoVenda"],
        "quoted_at": last["dataHoraCotacao"],
        "bulletin": last["tipoBoletim"],
        "source": "Banco Central do Brasil (PTAX)",
    }


def _ecb(client: httpx.Client, code: str) -> dict:
    data = _get_json(client, "https://api.frankfurter.dev/v1/latest", {"base": code, "symbols": "BRL"})
    return {
        "currency": code,
        "rate_brl": data["rates"]["BRL"],
        "quoted_at": data["date"],
        "source": "European Central Bank reference rate (Frankfurter), because the PTAX service was unavailable",
    }
