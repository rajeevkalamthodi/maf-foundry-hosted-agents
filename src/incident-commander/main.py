# Copyright (c) Microsoft. All rights reserved.
"""Incident Commander — a simple 3-agent orchestration sample.

Demonstrates the Microsoft Agent Framework's `WorkflowBuilder`, hosted on
Microsoft Foundry as a single hosted agent using the Responses protocol.

Three specialized agents are chained into one linear pipeline:

    Incident Commander -> Grid Operations -> Customer Experience

1. Incident Commander — reads the raw incident report, classifies the
   intent/severity, and produces an initial triage summary.
2. Grid Operations    — adds the technical outage/asset/restoration
   assessment on top of the triage summary.
3. Customer Experience — turns the technical assessment into a short,
   reviewable customer-facing update (a draft for a human to approve;
   it never auto-publishes).

Each agent only sees the previous agent's output (`context_mode="last_agent"`),
and the workflow returns only the final Customer Experience draft to the
caller — the same "assembly line" pattern used by any Agent Framework
workflow, just relabeled for an incident-response scenario.
"""

import os

from agent_framework import Agent, AgentExecutor, WorkflowBuilder
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

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

    incident_commander = Agent(
        client=client,
        instructions=(
            "You are the Incident Commander for an electric utility. "
            "Given a raw incident report, classify its intent and severity (H1-H6), "
            "identify what is affected, and write a short, structured triage summary "
            "for the specialist teams that will act next. Be concise and factual. "
            "You never replace a specialist's judgment — you only frame the problem."
        ),
        name="incident_commander",
    )

    grid_operations = Agent(
        client=client,
        instructions=(
            "You are the Grid Operations specialist. Given the Incident Commander's "
            "triage summary, explain the likely outage state, affected assets, and "
            "restoration options in plain, operational language. Add any exact "
            "procedure steps that are relevant. Do not invent data you were not given."
        ),
        name="grid_operations",
    )

    customer_experience = Agent(
        client=client,
        instructions=(
            "You are the Customer Experience specialist. Given the Grid Operations "
            "technical assessment, draft a short customer-facing status update: "
            "what happened, who is affected, and the estimated restoration outlook. "
            "Keep it clear and empathetic. Label it clearly as a DRAFT for human "
            "review — you never publish it yourself."
        ),
        name="customer_experience",
    )

    # Wrap each agent in an AgentExecutor. `context_mode="last_agent"` means each
    # step only sees the previous step's output, not the full conversation history.
    commander_executor = AgentExecutor(incident_commander, context_mode="last_agent")
    grid_ops_executor = AgentExecutor(grid_operations, context_mode="last_agent")
    customer_exp_executor = AgentExecutor(customer_experience, context_mode="last_agent")

    # Wire the three executors into a linear pipeline:
    #   incident_commander -> grid_operations -> customer_experience
    # Only the final (customer_experience) result is returned to the caller.
    workflow_agent = (
        WorkflowBuilder(
            start_executor=commander_executor,
            output_executors=[customer_exp_executor],
        )
        .add_edge(commander_executor, grid_ops_executor)
        .add_edge(grid_ops_executor, customer_exp_executor)
        .build()
        .as_agent()
    )

    server = ResponsesHostServer(workflow_agent)
    server.run()


if __name__ == "__main__":
    main()

