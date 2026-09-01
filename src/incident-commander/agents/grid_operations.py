# Copyright (c) Microsoft. All rights reserved.
"""Grid Operations — the technical specialist agent.

Incident Commander calls this agent as a tool (see `incident_commander.py`)
whenever a message needs a technical outage assessment.
"""

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient


def build_grid_operations_agent(client: FoundryChatClient) -> Agent:
    """Create the Grid Operations specialist agent.

    Args:
        client: The shared `FoundryChatClient` (same model deployment as the
            other agents in this sample).
    """
    return Agent(
        client=client,
        name="grid_operations",
        description=(
            "Technical grid specialist: outage state, affected assets, and restoration options."
        ),
        instructions=(
            "You are the Grid Operations specialist for an electric utility. "
            "Given an incident report or triage summary, explain the likely outage state, "
            "affected assets, and restoration options in plain, operational language. "
            "Add any exact procedure steps that are relevant. Do not invent data you were not given. "
            "Keep your answer to a few short paragraphs."
        ),
    )
