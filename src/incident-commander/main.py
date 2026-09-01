# Copyright (c) Microsoft. All rights reserved.
"""Incident Commander — a simple 3-agent orchestration sample.

Hosted on Microsoft Foundry as a single hosted agent using the Responses
protocol. Incident Commander is the agent the caller talks to; it delegates
to two specialists — Grid Operations and Customer Experience — using the
Microsoft Agent Framework's "agents-as-tools" pattern (`Agent.as_tool()`).

Each agent lives in its own module under `agents/`:

    agents/incident_commander.py   — orchestrator (this is the entry point agent)
    agents/grid_operations.py      — technical specialist, called as a tool
    agents/customer_experience.py — customer-comms specialist, called as a tool

There's no hand-written switch/if-else in this file — the routing decision
("which specialist(s) does this message need?") is made by the model itself,
based on the tool descriptions registered on Incident Commander. See
`agents/incident_commander.py` for the full explanation and instructions.
"""

import os

from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agents.incident_commander import build_incident_commander_agent

# Load environment variables from .env file (local development only)
load_dotenv()


def main():
    # A single chat client, shared by all three agents, pointed at the
    # Foundry project + model deployment configured in azure.yaml.
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    incident_commander = build_incident_commander_agent(client)

    server = ResponsesHostServer(incident_commander)
    server.run()


if __name__ == "__main__":
    main()


