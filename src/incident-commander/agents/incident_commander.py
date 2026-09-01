# Copyright (c) Microsoft. All rights reserved.
"""Incident Commander — the orchestrator agent.

Incident Commander is the single agent the caller talks to. Its two specialists
(`grid_operations`, `customer_experience`) are wrapped as callable *tools* via
Agent Framework's `Agent.as_tool()` — this is the "agents-as-tools" pattern
(see https://github.com/microsoft/agent-framework, `samples/02-agents/tools/`).

There is no hand-written switch/if-else here: the model itself acts as the
switch. On every message it reads the two tool descriptions below and decides
whether to call one, both (in order), or neither:

  - A casual message ("Hi", "Who are you?") gets a direct reply — no tools
    called, no unnecessary delay.
  - A real incident report triggers `consult_grid_operations` first, then
    `draft_customer_update` with that result, then Incident Commander
    assembles both into one reply.

This is deliberately simpler than an Agent Framework `WorkflowBuilder`
pipeline: each agent here is a plain `Agent`, so there's no shared, single-run
`Workflow` instance to serialize concurrent requests behind (a `Workflow` only
allows one active `run()` at a time — see the Agent Framework source,
`_workflows/_workflow.py`). That single-instance lock is what caused the
"Workflow is already running; concurrent runs are not allowed on the same
instance" error when two messages arrived close together in the Playground.
Plain `Agent` instances (and the tools built from them) have no such
restriction, so this version handles overlapping requests correctly.
"""

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

from agents.customer_experience import build_customer_experience_agent
from agents.grid_operations import build_grid_operations_agent


def build_incident_commander_agent(client: FoundryChatClient) -> Agent:
    """Create the Incident Commander orchestrator agent.

    Args:
        client: The shared `FoundryChatClient` (same model deployment as the
            two specialist agents wrapped as tools below).
    """
    grid_operations_tool = build_grid_operations_agent(client).as_tool(
        name="consult_grid_operations",
        description=(
            "Get the Grid Operations technical assessment (outage state, affected assets, "
            "restoration options) for an incident. Call this first for any real incident report — "
            "not for casual messages."
        ),
        arg_name="incident_context",
        arg_description="The incident report or triage summary to analyze.",
    )

    customer_experience_tool = build_customer_experience_agent(client).as_tool(
        name="draft_customer_update",
        description=(
            "Draft a short, reviewable customer-facing status update from a technical assessment. "
            "Call this after consult_grid_operations for any real incident report."
        ),
        arg_name="technical_assessment",
        arg_description="The Grid Operations technical assessment to turn into a customer update.",
    )

    return Agent(
        client=client,
        name="incident_commander",
        description="Incident Commander: triages incident reports and routes to specialists.",
        instructions=(
            "You are the Incident Commander for an electric utility. "
            "For casual messages (greetings, small talk, questions about who you are), just answer "
            "directly and briefly — do not call any tools.\n\n"
            "For an actual incident report, do the following in order:\n"
            "1. Call `consult_grid_operations` with the incident details to get the technical assessment.\n"
            "2. Call `draft_customer_update` with that assessment to get a customer-facing draft.\n"
            "3. Reply with a short triage summary, followed by both results clearly labeled "
            "'Grid Operations assessment' and 'Customer update (DRAFT — for human review)'.\n\n"
            "You never replace a specialist's judgment — you only classify, route, and assemble."
        ),
        tools=[grid_operations_tool, customer_experience_tool],
    )
