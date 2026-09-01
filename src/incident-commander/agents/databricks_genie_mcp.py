# Copyright (c) Microsoft. All rights reserved.
"""Optional fourth tool: the Databricks Genie MCP agent.

Databricks Genie spaces expose a managed MCP server that lets any MCP client
ask natural-language data questions, with no Databricks SDK required:

    https://<workspace-hostname>/api/2.0/mcp/genie/{genie_space_id}

(see https://docs.databricks.com/aws/en/agents/mcp-tools/managed-mcp). This
module connects to that endpoint with Agent Framework's `MCPStreamableHTTPTool`
— the same MCP client class the framework's other samples use for Foundry
toolboxes and A2A delegation — and exposes it as a tool Incident Commander can
call. No separate hosted agent is required; the Genie MCP server *is* the
"agent" here.

Requires environment variables (set via `azd env set` + the agent's
`environmentVariables` in azure.yaml for the deployed agent, or `.env` for
local runs — see `.env.example` and the README):

    DATABRICKS_HOST            e.g. https://adb-1234567890123456.7.azuredatabricks.net
    DATABRICKS_GENIE_SPACE_ID  the target Genie space ID (Genie space -> Settings -> Copy space ID)
    DATABRICKS_TOKEN           a Databricks personal access token, or — for production —
                               a service-principal OAuth (M2M) token:
                               https://learn.microsoft.com/azure/databricks/dev-tools/auth/oauth-m2m

This tool is only registered on Incident Commander when `DATABRICKS_GENIE_SPACE_ID`
is set (see `agents/incident_commander.py`), so the sample keeps running
unmodified until you've connected your own Genie space.
"""

import os

from agent_framework import MCPStreamableHTTPTool
from httpx import AsyncClient


def build_databricks_genie_mcp_tool() -> MCPStreamableHTTPTool:
    """Build an MCP tool connected to a Databricks Genie space's managed MCP server.

    Call this only after confirming `DATABRICKS_GENIE_SPACE_ID` is set (see
    `agents/incident_commander.py`) — it reads `DATABRICKS_HOST`,
    `DATABRICKS_GENIE_SPACE_ID`, and `DATABRICKS_TOKEN` directly and raises
    `KeyError` if any of them is missing.

    The returned tool is unconnected — `Agent`/`ResponsesHostServer` connect it
    on first use and close it at shutdown, the same lifecycle used for
    `FoundryToolbox` in the Foundry Toolbox sample.
    """
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    space_id = os.environ["DATABRICKS_GENIE_SPACE_ID"]
    token = os.environ["DATABRICKS_TOKEN"]

    return MCPStreamableHTTPTool(
        name="databricks_genie",
        description=(
            "Databricks Genie: ask natural-language questions against the utility's "
            "grid/asset data. Use this for specific numbers or history you don't "
            "already have — e.g. past outage counts for a feeder, asset install dates, "
            "or historical restoration times — before drafting the technical assessment."
        ),
        url=f"{host}/api/2.0/mcp/genie/{space_id}",
        # Static auth header for every request to this MCP server.
        http_client=AsyncClient(headers={"Authorization": f"Bearer {token}"}),
    )
