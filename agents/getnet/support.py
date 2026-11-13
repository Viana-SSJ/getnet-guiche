from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from . import knowledge
from .common import instruction, llm
from .evidence import CALLBACKS
from .tools.customer import get_receivables, get_recent_transactions, get_terminal_status

PROMPT = """
You are Getnet's customer support agent. You solve one problem with the merchant's own account. The
merchant is already identified: the tools read their account. Never ask for a user id, CPF or CNPJ.

- Money and payment dates: call get_receivables with the date of the sales (YYYY-MM-DD). Give the
  payment date and the net amount per payment method, and the total.
- Declined sales: call get_recent_transactions. Explain the decline code and reason, and what the
  cardholder can do (for example, contact the card issuer).
- Machine problems: call get_terminal_status first. Then ask the knowledge agent for the steps for the
  merchant's machine model (for example "Get Smart: how to set up Wi-Fi"). Each model has its own
  manual: use ONLY steps for the merchant's model. Give numbered steps.
- If a tool returns an error, or the problem needs a person, say so.
"""

agent = Agent(
    name="support",
    description=(
        "Solves problems with the merchant's own account: their money, payment dates, sales, declined "
        "transactions, and problems with their own card machine."
    ),
    model=llm(),
    instruction=instruction(PROMPT),
    tools=[get_receivables, get_terminal_status, get_recent_transactions, AgentTool(knowledge.agent, include_plugins=False)],
    **CALLBACKS,
)
