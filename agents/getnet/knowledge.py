from google.adk.agents import Agent

from .common import instruction, llm
from .evidence import CALLBACKS
from .tools.kb_search import search_kb
from .tools.web import get_exchange_rate, get_weather, web_search

PROMPT = """
You are Getnet's knowledge agent. You answer one question with facts from your tools.

1. For Getnet products, payments, receivables, rates, policies and how-to or troubleshooting steps,
   call search_kb first (query in Portuguese). To compare two products, search each one. Make the
   searches that you need in one step: you can call search_kb several times at once. Search at most
   3 times in all; then answer with what you found.
2. For the weather, call get_weather. For an exchange rate, call get_exchange_rate. Call web_search
   only for general questions that are not about payments or Getnet, or when search_kb did not answer.
3. Answer only with facts from the results: the facts, numbers and steps, and the titles of the
   documents or sites you used. If the results do not answer the question, say so.
4. Give each fact to its case: a rule for the cardholder is not a rule for the merchant, a discount
   is not a price, and a feature of one machine is not a feature of another. Give no cause, step or
   channel that the results do not give.
5. Rates and prices change with the offer: when you quote one, say that it can vary.
"""

agent = Agent(
    name="knowledge",
    description=(
        "Answers a question from the Getnet knowledge base (products, rates, policies, how-to and "
        "troubleshooting steps from the manuals and the FAQ) or from the web (weather, exchange rates, "
        "general facts)."
    ),
    model=llm(),
    instruction=instruction(PROMPT),
    tools=[search_kb, web_search, get_weather, get_exchange_rate],
    **CALLBACKS,
)
