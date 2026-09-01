# Incident Commander — Multi-Agent Orchestration Sample

A minimal, easy-to-follow reference showing how to build a **multi-agent orchestration**
with the [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) and run
it as a **Microsoft Foundry hosted agent**.

Three simple agents are involved. Incident Commander is the one the caller talks to; it
delegates to the other two as **tools**, using the Agent Framework's `Agent.as_tool()`
("agents-as-tools") pattern:

```
                         ┌───────────────────────┐
                    ┌──> │   Grid Operations     │
                    │    │  (technical detail)   │
┌──────────────────┐│    └───────────────────────┘
│ Incident Commander││
│ (triage & routing)│    ┌───────────────────────┐
└──────────────────┘└──> │  Customer Experience  │
                         │  (customer draft)     │
                         └───────────────────────┘
```

| Agent | Role |
|---|---|
| **Incident Commander** | The agent you talk to. Answers casual messages directly; for a real incident report, calls the two specialists below (in order) and assembles their results. |
| **Grid Operations** | Called as a tool (`consult_grid_operations`). Given the incident details, explains the outage state, affected assets, and restoration options. |
| **Customer Experience** | Called as a tool (`draft_customer_update`). Given the Grid Operations assessment, drafts a short, reviewable customer-facing status update (a draft only — it never auto-publishes). |

There's no hand-written switch/if-else routing logic — **the model itself decides** which
tool(s) to call based on the tool descriptions it's given, the same way it would decide to call
any other tool. Each agent is a separate file under [`src/incident-commander/agents/`](src/incident-commander/agents/),
so you can read, relabel, or extend any one of them independently.

> This sample is deliberately simple: one hosted agent process, one shared model client,
> three plain `Agent` instances. No external connectors — just the core
> agents-as-tools orchestration pattern.

See [`src/incident-commander/main.py`](src/incident-commander/main.py) (entry point) and
[`src/incident-commander/agents/`](src/incident-commander/agents/) (the three agents) for the
full implementation.

## How it works

- `FoundryChatClient` — a single chat client shared by all three agents, pointed at your
  Foundry project + model deployment ([`main.py`](src/incident-commander/main.py)).
- `Agent` — each specialist ([`agents/grid_operations.py`](src/incident-commander/agents/grid_operations.py),
  [`agents/customer_experience.py`](src/incident-commander/agents/customer_experience.py)) is a plain
  `Agent` with its own `instructions` and `name` — no workflow wiring required.
- `Agent.as_tool(name=..., description=..., arg_name=...)` — wraps each specialist agent as a
  callable `FunctionTool` ([`agents/incident_commander.py`](src/incident-commander/agents/incident_commander.py)).
  The `description` is what the orchestrator's model reads to decide *when* to call it.
- `Agent(..., tools=[...])` — Incident Commander is a plain `Agent` too, just with the two
  specialist tools registered. Its `instructions` describe the routing policy in plain English.
- `ResponsesHostServer` — serves Incident Commander over the Foundry **Responses** protocol so
  it can run locally and be deployed as a Foundry hosted agent unchanged.

> **Why not `WorkflowBuilder`?** An earlier version of this sample chained the three agents
> with `WorkflowBuilder` into a fixed pipeline. A built `Workflow` only allows **one active
> `run()` at a time for its whole lifetime** — sending a second message before the first
> fully finishes raises `WorkflowException: Workflow is already running; concurrent runs are
> not allowed on the same instance.` Plain `Agent` instances (and tools built from them) have
> no such restriction, so this agents-as-tools version handles overlapping Playground messages
> correctly, and casual messages (["Hi"](src/incident-commander/agents/incident_commander.py)) get an instant direct reply instead of being forced
> through all three agents every time.

## Prerequisites

1. **Azure Developer CLI (`azd`)**, version 1.27.1 or later — [Install azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
2. Install (or update) the Foundry agent extension:
   ```bash
   azd extension install azure.ai.agents
   # If you already have it, make sure it's current — this sample needs >= 1.0.0-beta.9:
   azd extension update azure.ai.agents
   ```
3. Authenticate:
   ```bash
   az login
   azd auth login
   ```
4. *(Optional)* Python 3.11–3.13 — only needed if you want to run the agent locally before
   deploying (see [Optional: run locally before deploying](#optional-run-locally-before-deploying)).
   Not required to deploy straight to Azure.

## Project layout

```
azure.yaml                        # azd project manifest (agent + model deployment)
src/incident-commander/
  main.py                         # entry point: builds the client, starts ResponsesHostServer
  agents/
    incident_commander.py         # orchestrator — wires the two specialists as tools
    grid_operations.py            # technical specialist agent
    customer_experience.py        # customer-comms specialist agent
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

Clone (or copy) this repository, then run all commands below from the repository root. This
path goes straight to Azure — no local Python setup required.

### 1. Create an azd environment and provision Azure resources

`azure.yaml` is checked in, but the per-environment `azd` state (`.azure/`) is not (see
[Infrastructure](#infrastructure--how-deployment-works-no-hand-written-bicep-needed) below) —
create it once per person/environment:

```bash
azd env new incident-commander-dev
azd env set AZURE_SUBSCRIPTION_ID <your-subscription-id>
azd env set AZURE_LOCATION eastus2

azd provision
```

This creates a new Foundry resource group, account, project, and the `gpt-5.4` model
deployment declared in `azure.yaml`. If provisioning fails with a message about
`azure.ai.agents` not satisfying a version constraint, run `azd extension update azure.ai.agents`
and retry.

### 2. Deploy to Microsoft Foundry

```bash
azd deploy
```

`azd deploy` zips `src/incident-commander/`, uploads it to Foundry, builds the runtime
remotely, and registers a new immutable agent version — no Docker, ACR, or local Python
environment required for the default `code` deploy mode used here.

### 3. Invoke the deployed agent

```bash
azd ai agent invoke "Feeder 12 tripped in the downtown core, ~4,200 customers affected. Cause unknown."
```

### 4. Check status / tear down

```bash
azd ai agent show --output json   # status + endpoints
azd down                          # remove all Azure resources when you're done
```

## Optional: run locally before deploying

Skip this whole section if you just want the agent running in Azure — steps 1–4 above are all
you need. Come back here only if you want to iterate on `main.py` and test changes on your own
machine (`http://localhost:8088`) before running `azd deploy` again.

### Set up Python and run locally

Pick the instructions for your platform. Each does the same three things: create a virtual
environment inside `src/incident-commander/`, install `uv` (so `azd ai agent run` installs
dependencies in seconds instead of minutes), then start the agent.

> Use Python **3.11–3.13**. Python 3.14 doesn't yet have prebuilt wheels for some dependencies
> (you'd hit a source build and likely a compiler error) — see the Windows on Arm note below
> if that's your situation.

#### Windows — Intel/AMD (x64)

```powershell
cd src\incident-commander
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install uv
cd ..\..

azd ai agent run --no-client
```

#### Windows on Arm (e.g. Snapdragon)

Native ARM64 Python builds are currently missing prebuilt wheels for some dependencies
(`cryptography`), which fails with a `link.exe not found` / Rust compiler error. Use an
**x64 Python interpreter** instead — Windows on Arm runs x64 apps fine under emulation:

```powershell
cd src\incident-commander
py -3.12-x64 -m venv .venv        # explicitly pick the x64 build, not the arm64 one
.\.venv\Scripts\Activate.ps1
python -m pip install uv
cd ..\..

azd ai agent run --no-client
```

If `py -3.12-x64` isn't found, install it from
[python.org](https://www.python.org/downloads/windows/) — pick the **"Windows installer
(64-bit)"**, not the Arm64 installer, then retry.

#### macOS (Apple Silicon or Intel)

```bash
cd src/incident-commander
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install uv
cd ../..

azd ai agent run --no-client
```

#### Linux (x64 or Arm64)

```bash
cd src/incident-commander
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install uv
cd ../..

azd ai agent run --no-client
```

### Invoke the local agent

Once you see `Starting agent on http://localhost:8088` (this may take a minute on first run
while dependencies install), open a **separate terminal** (same platform, any shell) and run:

```bash
azd ai agent invoke --local "Feeder 12 tripped in the downtown core, ~4,200 customers affected. Cause unknown."
```

When you're happy with local behavior, deploy the same code with `azd deploy` (step 2 above).

## Troubleshooting

- **`azd env set` fails with no environment found.** You skipped `azd env new <name>` — this
  repo doesn't (and shouldn't) commit `.azure/`, so each person/environment creates their own.
- **Provisioning fails with an `azure.ai.agents` version constraint error.** Run
  `azd extension update azure.ai.agents` and re-run `azd provision`.
- **Provisioning fails with `ServiceModelDeprecating` for the model.** The pinned model/version
  in `azure.yaml` (`services.ai-project.deployments[]`) has been deprecated in your region.
  Run `az cognitiveservices model list --location <region> --subscription <sub-id> -o json` to
  find a current, non-deprecated version and update `azure.yaml` accordingly.
- **Local `azd ai agent run` fails building `cryptography` from source** (seen on Python 3.14 /
  Windows on Arm, with errors like `linker link.exe not found`): a prebuilt wheel isn't available
  for that Python version/architecture yet. Delete `src/incident-commander/.venv` and follow the
  platform-specific steps in [Set up Python and run locally](#set-up-python-and-run-locally) —
  on Windows on Arm, make sure you picked the **x64** Python build, not Arm64. This only affects
  the optional local-run path, not `azd deploy`.
- **`py` / `py -3.12-x64` not recognized (Windows).** The [Python Launcher](https://docs.python.org/3/using/windows.html#python-launcher-for-windows)
  isn't installed or that specific version isn't installed. Install Python from
  [python.org](https://www.python.org/downloads/windows/) with "Install launcher for all users"
  checked, or substitute the full path to `python.exe` for that version.

## Customizing for your own scenario

- Rename an agent or edit its `instructions` in its own file under
  [`agents/`](src/incident-commander/agents/) — no other file needs to change.
- Add a fourth specialist: create a new `agents/<name>.py` with a `build_<name>_agent(client)`
  function (same shape as the existing two), then wrap it with `.as_tool(...)` and add it to
  the `tools=[...]` list in [`agents/incident_commander.py`](src/incident-commander/agents/incident_commander.py).
- Change the routing policy by editing Incident Commander's `instructions` in
  [`agents/incident_commander.py`](src/incident-commander/agents/incident_commander.py) — this
  is the only place that decides when each specialist tool gets called.
- Swap the model in `azure.yaml` under `services.ai-project.deployments[]` (update the
  agent's `AZURE_AI_MODEL_DEPLOYMENT_NAME` reference if you change the deployment `name`).

## Next steps

- [Agent Framework workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/) — learn more about `WorkflowBuilder`
- [Workflow as an agent](https://learn.microsoft.com/en-us/agent-framework/workflows/as-agents?pivots=programming-language-python) — serving workflows via the Responses protocol
- [Hosted agents overview](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
- [Deploy a hosted agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent)
- [Manage hosted agents](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/manage-hosted-agent)
