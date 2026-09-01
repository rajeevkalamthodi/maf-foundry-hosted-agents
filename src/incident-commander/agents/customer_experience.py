# Copyright (c) Microsoft. All rights reserved.
"""Customer Experience — the customer-communication specialist agent.

Incident Commander calls this agent as a tool (see `incident_commander.py`)
after Grid Operations has produced a technical assessment, to turn it into a
short, reviewable customer-facing update.
"""

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient


def build_customer_experience_agent(client: FoundryChatClient) -> Agent:
    """Create the Customer Experience specialist agent.

    Args:
        client: The shared `FoundryChatClient` (same model deployment as the
            other agents in this sample).
    """
    return Agent(
        client=client,
        name="customer_experience",
        description=(
            "Customer-communication specialist: drafts short, reviewable customer-facing status updates."
        ),
        instructions=(
            "You are the Customer Experience specialist for an electric utility. "
            "Given a Grid Operations technical assessment, draft a short customer-facing status "
            "update: what happened, who is affected, and the estimated restoration outlook. "
            "Keep it clear and empathetic, and free of internal jargon. "
            "Always label your output clearly as a DRAFT for human review — you never publish it yourself."
        ),
    )
