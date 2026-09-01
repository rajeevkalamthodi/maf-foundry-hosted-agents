# Incident Commander — Multi-Agent Orchestration Sample

A minimal, easy-to-follow reference showing how to build a **multi-agent orchestration**
with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) and run
it as a **Microsoft Foundry hosted agent**.

Three simple agents are chained into one linear pipeline using the Agent Framework's
`WorkflowBuilder`:

```
┌──────────────────────┐     ┌─────────────────────┐     ┌───────────────────────┐
│  Incident Commander   │ --> │   Grid Operations    │ --> │  Customer Experience  │
│  (triage & routing)   │     │  (technical detail)   │     │  (customer draft)     │
└──────────────────────┘     └─────────────────────┘     └───────────────────────┘
```

| Agent | Role |
|---|---|
| **Incident Commander** | Reads the raw incident report, classifies intent/severity, and produces a short triage summary. |
| **Grid Operations** | Takes the triage summary and adds the technical outage / asset / restoration assessment. |
| **Customer Experience** | Turns the technical assessment into a short, reviewable customer-facing status update (a draft only — it never auto-publishes). |

Each agent only sees the previous agent's output (`context_mode="last_agent"`), and only the
final Customer Experience draft is returned to the caller. This is the same orchestration
pattern you'd use for any sequential multi-agent pipeline — the code is intentionally generic
so you can relabel the agents and instructions for your own scenario.

> This sample is deliberately simple: one hosted agent process, one shared model client,
> three `Agent` instances wired together with `WorkflowBuilder`. No tools, no external
> connectors — just the core orchestration pattern.

See [`src/incident-commander/main.py`](src/incident-commander/main.py) for the full
implementation (~100 lines, heavily commented).

## How it works

- `FoundryChatClient` — a single chat client shared by all three agents, pointed at your
  Foundry project + model deployment.
- `Agent` — each of the three specialists is a plain `Agent` with its own `instructions` and `name`.
- `AgentExecutor(agent, context_mode="last_agent")` — wraps each agent so it only receives the
  previous step's output, not the full conversation history.
- `WorkflowBuilder` — wires the three executors into a linear pipeline (`start_executor` +
  `add_edge(...)`) and limits the returned output to the final executor (`output_executors=[...]`).
- `.build().as_agent()` — converts the workflow into a standard Agent Framework agent.
- `ResponsesHostServer` — serves that agent over the Foundry **Responses** protocol so it can
  run locally and be deployed as a Foundry hosted agent unchanged.

## Prerequisites

1. **Azure Developer CLI (`azd`)** — [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
2. Install the Foundry agent extension:
   ```bash
   azd extension install azure.ai.agents
   ```
3. Authenticate:
   ```bash
   az login
   azd auth login
   ```
4. Python 3.13 (for local runs outside `azd ai agent run`)

## Project layout

```
azure.yaml                        # azd project manifest (agent + model deployment)
src/incident-commander/
  main.py                         # the 3-agent orchestration (Incident Commander -> Grid Operations -> Customer Experience)
  requirements.txt                # agent-framework + hosting dependencies
  Dockerfile                      # container definition (used only for container deploy mode)
  .env.example                    # local-only env var template (never commit real values)
```

## Infrastructure — how deployment works (no hand-written Bicep needed)

This sample uses the **Foundry azd extension's built-in infrastructure provider**
(`infra: provider: microsoft.foundry` in [`azure.yaml`](azure.yaml)). This is the current
Microsoft best practice for hosted agents: `azd provision` / `azd deploy` generate and manage
the underlying Bicep for you — the Foundry account, project, model deployment, App Insights,
and Log Analytics workspace — so there are no Bicep files to maintain or drift from in this repo.

Configuration lives in two places, matching standard `azd` conventions:

- **`azure.yaml`** — the declarative, committed source of truth: agent definition, model
  deployment (`services.ai-project.deployments[]`), CPU/memory, protocol.
- **`azd` environment values** (`.azure/<env>/.env`, managed by `azd env set` / `azd env get-values`)
  — per-environment, **not committed**: subscription, region, resulting project endpoint,
  resolved model deployment name. This is how you get separate `dev` / `test` / `prod`
  environments from the same code.

`src/incident-commander/.env` (local-only, git-ignored) is only used for **local runs** —
it lets `azd ai agent run` reach your Foundry project without needing the full `azd`
environment. Never put secrets or committed config there; both `FOUNDRY_PROJECT_ENDPOINT`
and `AZURE_AI_MODEL_DEPLOYMENT_NAME` are non-secret identifiers (auth uses your Azure identity
via `DefaultAzureCredential`, not API keys).

If you need full control over the infrastructure (custom networking, bring-your-own resources,
private endpoints, etc.), see [Standard Agent Setup](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-agent)
in the Foundry docs — that path does let you supply your own Bicep/capability-host templates.

## Run it

### 1. Provision Azure resources

```bash
azd env set AZURE_SUBSCRIPTION_ID <your-subscription-id>
azd env set AZURE_LOCATION eastus2

azd provision
```

This creates a new Foundry resource group, account, project, and the `gpt-5.4` model
deployment declared in `azure.yaml`.

### 2. Run locally

```bash
cd src/incident-commander
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux
python -m pip install uv
cd ..\..

azd ai agent run --no-client
```

In a separate terminal:

```bash
azd ai agent invoke --local "Feeder 12 tripped in the downtown core, ~4,200 customers affected. Cause unknown."
```

### 3. Deploy to Microsoft Foundry

```bash
azd deploy
```

`azd deploy` zips `src/incident-commander/`, uploads it to Foundry, builds the runtime
remotely, and registers a new immutable agent version — no Docker or ACR required for the
default `code` deploy mode used here.

### 4. Invoke the deployed agent

```bash
azd ai agent invoke "Feeder 12 tripped in the downtown core, ~4,200 customers affected. Cause unknown."
```

### 5. Check status / tear down

```bash
azd ai agent show --output json   # status + endpoints
azd down                          # remove all Azure resources when you're done
```

## Customizing for your own scenario

- Rename the three `Agent` instances and edit their `instructions` in
  [`main.py`](src/incident-commander/main.py) — the orchestration wiring (`WorkflowBuilder`,
  `add_edge`, `output_executors`) does not need to change.
- Add a fourth agent by creating another `Agent` + `AgentExecutor` and wiring it with
  `add_edge(...)` into the pipeline.
- Swap the model in `azure.yaml` under `services.ai-project.deployments[]` (update the
  agent's `AZURE_AI_MODEL_DEPLOYMENT_NAME` reference if you change the deployment `name`).

## Next steps

- [Agent Framework workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/) — learn more about `WorkflowBuilder`
- [Workflow as an agent](https://learn.microsoft.com/en-us/agent-framework/workflows/as-agents?pivots=programming-language-python) — serving workflows via the Responses protocol
- [Hosted agents overview](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
- [Deploy a hosted agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent)
- [Manage hosted agents](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-agent)
