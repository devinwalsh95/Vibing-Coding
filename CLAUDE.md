# SAP Presales Sales Advisor

Three-phase Streamlit app that guides SAP presales professionals through the full sales cycle: Discovery → Demo Prep → Demo Delivery. Each phase uses the previous phase's output as context and produces downloadable, refineable briefs.

## Running the app

```powershell
cd C:\Users\I763056\presales-discovery
$env:ANTHROPIC_API_KEY = "your-hyperspace-key"
$env:ANTHROPIC_BASE_URL = "http://localhost:6655/anthropic"
py -m streamlit run app.py
```

The Hyperspace local proxy must be running before starting the app. Check `http://localhost:6655` in the browser to confirm.

## Infrastructure

- **LLM**: Claude via SAP Hyperspace AI (internal proxy), not direct Anthropic API
- **Proxy**: local proxy at `http://localhost:6655` forwards to `https://api.hyperspace.tools.sap/llm-proxy/anthropic/v1/messages`
- **Model ID**: `anthropic--claude-4.6-opus` (Hyperspace format — not `claude-opus-4-6`)
- **No web search**: not supported through Hyperspace; Claude uses training knowledge only
- **No adaptive thinking**: not supported through Hyperspace; omit the `thinking` parameter entirely
- **API key**: Hyperspace UUID-format key, set as `ANTHROPIC_API_KEY`

## Key files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI — tabs for all three phases |
| `agent.py` | `run_discovery()`, `run_demo_prep()`, `run_demo_delivery()`, `refine_section()` |
| `diagram.py` | Horseshoe process flow diagram via Plotly (Discovery phase only) |
| `export.py` | Markdown → Word (.docx) export, used by all three phases |
| `solutions/*.md` | SAP solution knowledge files injected into system prompts |

## Solution scope

| UI Label | File |
|----------|------|
| SAP Cloud ERP (Public Cloud) | `cloud_erp_public.md` |
| SAP Cloud ERP (Private Cloud) | `cloud_erp_private.md` |
| SAP Business Network | `sap_business_network.md` |
| SAP Ariba | `ariba.md` |
| SAP Integrated Business Planning | `ibp.md` |
| SAP Digital Manufacturing Cloud | `dmc.md` |
| SAP Field Service Management | `fsm.md` |

To add a new solution: create a `.md` file in `solutions/` and add a new entry to `SOLUTION_FILES` in `agent.py`.

## Phase architecture

**Phase 1 — Discovery**: Generates a company intelligence brief and targeted discovery questions anchored to named business process steps. Includes a Plotly horseshoe process flow diagram.

**Phase 2 — Demo Prep**: Takes the discovery brief as input. Produces a timed demo agenda, per-capability talking points (tied to specific discovery findings), anticipated objections, wow moments, and a value story.

**Phase 3 — Demo Delivery**: Takes the demo prep brief as input. Produces a live cheat sheet, post-demo follow-up plan (with email draft), and an executive summary slide outline.

Each phase: streams output live → stores in session_state → supports section refinement → downloadable as Markdown or Word.

## Section refinement

After any phase generates output, a "Refine a Section" expander appears. `refine_section()` in `agent.py` rewrites only the selected section body using the full brief as context, then splices the result back via `_replace_section()`.

## Prompt design notes

**Discovery questions**: Anchored to named business process steps. "Process-curious" style — explore how the process works today, let the customer reveal the pain. "Casually specific" calibration. SPIN arc: lead = Situation/Problem, probe 1 = Implication, probe 2 = Need-Payoff.

**Demo prep talking points**: Must reference the customer's specific situation from the discovery brief — not generic SAP feature descriptions. Every section grounded in a discovery finding.

**Demo delivery cheat sheet**: Scannable bullets, no paragraphs. Follow-up email written as a human, not corporate copy.


Streamlit app that generates AI-powered discovery briefs for SAP presales calls. Given a company name, industry, SAP solutions being positioned, and optional context, it produces a structured brief with company intelligence, industry context, strategic positioning, and targeted discovery questions — then lets the user refine individual sections without regenerating the whole brief.

## Running the app

```powershell
cd C:\Users\I763056\presales-discovery
$env:ANTHROPIC_API_KEY = "your-hyperspace-key"
$env:ANTHROPIC_BASE_URL = "http://localhost:6655/anthropic"
py -m streamlit run app.py
```

The Hyperspace local proxy must be running before starting the app. Check `http://localhost:6655` in the browser to confirm.

## Infrastructure

- **LLM**: Claude via SAP Hyperspace AI (internal proxy), not direct Anthropic API
- **Proxy**: local proxy at `http://localhost:6655` forwards to `https://api.hyperspace.tools.sap/llm-proxy/anthropic/v1/messages`
- **Model ID**: `anthropic--claude-4.6-opus` (Hyperspace format — not `claude-opus-4-6`)
- **No web search**: not supported through Hyperspace; Claude uses training knowledge only
- **No adaptive thinking**: not supported through Hyperspace; omit the `thinking` parameter entirely
- **API key**: Hyperspace UUID-format key, set as `ANTHROPIC_API_KEY`

## Key files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI — form, output display, section refinement |
| `agent.py` | `run_discovery()` and `refine_section()` — prompt logic, streaming |
| `diagram.py` | Horseshoe process flow diagram via Plotly |
| `export.py` | Markdown → Word (.docx) export |
| `solutions/*.md` | SAP solution knowledge files injected into the system prompt |

## Adding or editing SAP solutions

Edit or add `.md` files in `solutions/`, then register them in `agent.py`:

```python
SOLUTION_FILES = {
    "SAP S/4HANA Cloud": "s4hana.md",
    # add new entry here
}
```

The solution name appears in the UI multiselect automatically.

## Prompt design notes

- Questions are anchored to named business process steps (O2C, P2P, supply chain collaboration, manufacturing, financial close)
- Style: "process-curious" — explore how the process works today, let the customer reveal the pain
- "Casually specific" calibration: specific enough to sound credible, vague enough to stay relevant if an assumption is slightly off
- SPIN arc: lead question = Situation/Problem, probe 1 = Implication, probe 2 = Need-Payoff
- Follow-on probes formatted as `> *If they describe X:* ...` blockquotes
- 10–12 lead questions across 3–5 process themes per brief

## Section refinement

After generation, a "Refine a Section" expander appears. It calls `refine_section()` in `agent.py`, which rewrites only the selected section body using the full brief as context, then splices the result back into `session_state.brief_output`.
