"""
SAP Presales Sales Advisor — Streamlit UI
Three-phase tool: Discovery → Demo Prep → Demo Delivery
"""

import os
import re
import streamlit as st
from agent import run_discovery, run_demo_prep, run_demo_delivery, refine_section, SOLUTION_FILES
from diagram import extract_process_flow, render_process_flow
from export import md_to_docx

st.set_page_config(
    page_title="SAP Presales Sales Advisor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .header-bar {
        background: linear-gradient(90deg, #0066A1 0%, #00B2E3 100%);
        padding: 1.2rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .header-bar h1 { color: white !important; margin: 0; font-size: 1.8rem; }
    .header-bar p {
        color: rgba(255,255,255,0.85) !important;
        margin: 0.2rem 0 0 0;
        font-size: 0.95rem;
    }
    .stMarkdown strong { color: #0066A1; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stFormSubmitButton button {
        background-color: #0066A1 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 2rem !important;
        font-size: 1rem !important;
    }
    .stFormSubmitButton button:hover { background-color: #005580 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="header-bar">
        <h1>🔍 SAP Presales Sales Advisor</h1>
        <p>AI-powered sales toolkit — Discovery · Demo Prep · Demo Delivery</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Check API key ─────────────────────────────────────────────────────────────
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY not found.** Set this environment variable before running:\n\n"
        "```\n$env:ANTHROPIC_API_KEY = \"your-key\"\n```",
        icon="🔑",
    )
    st.stop()

# ── Password gate ─────────────────────────────────────────────────────────────
# Only active when APP_PASSWORD is set in Streamlit secrets.
# Skip entirely for local runs (where secrets aren't configured).
_app_password = st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") else ""
if _app_password:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.markdown("#### Access")
        pwd = st.text_input("Password", type="password", key="_pwd")
        if st.button("Enter", type="primary"):
            if pwd == _app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.", icon="🔒")
        st.stop()


INDUSTRIES = [
    "Aerospace & Defense", "Automotive", "Banking & Financial Services",
    "Chemicals", "Consumer Goods / FMCG", "Energy & Utilities",
    "Engineering, Construction & Operations", "Healthcare & Life Sciences",
    "High Tech & Electronics", "Industrial Machinery & Components", "Insurance",
    "Media & Entertainment", "Mill Products & Mining", "Oil & Gas",
    "Pharmaceuticals & Biotech", "Professional Services", "Public Sector",
    "Retail & Fashion", "Telecommunications", "Transportation & Logistics",
    "Wholesale Distribution", "Other",
]

DISCOVERY_SECTIONS = ["Company Intelligence", "Industry Context", "Strategic Positioning", "Discovery Questions"]
DEMO_PREP_SECTIONS = ["Demo Agenda", "Talking Points", "Anticipated Objections", "Wow Moments", "Value Story"]
DEMO_DELIVERY_SECTIONS = ["Live Cheat Sheet", "Post-Demo Follow-Up Plan", "Executive Summary Slide Outline"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_section(markdown_text: str, section_name: str) -> str:
    pattern = rf"^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown_text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""

def _replace_section(markdown_text: str, section_name: str, new_body: str) -> str:
    pattern = rf"(^## {re.escape(section_name)}\s*\n)(.*?)(?=^## |\Z)"
    replacement = rf"\g<1>{new_body.strip()}\n\n"
    return re.sub(pattern, replacement, markdown_text, flags=re.MULTILINE | re.DOTALL)

def _download_row(output: str, slug: str, prefix: str):
    """Render side-by-side Markdown + Word download buttons."""
    dl1, dl2 = st.columns([1, 1])
    with dl1:
        st.download_button(
            label="Download as Markdown",
            data=output,
            file_name=f"{prefix}_{slug}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            label="Download as Word",
            data=md_to_docx(output),
            file_name=f"{prefix}_{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

def _refine_expander(output_key: str, sections: list[str], inputs: dict, expander_key_suffix: str):
    """Render the 'Refine a Section' expander for any phase."""
    if not st.session_state.get(output_key):
        return
    st.divider()
    with st.expander("Refine a Section", expanded=False):
        st.caption("Select a section and describe what you'd like changed. Only that section will be rewritten.")
        c1, c2 = st.columns([1, 2])
        with c1:
            section = st.selectbox("Section", options=sections, key=f"section_{expander_key_suffix}")
        with c2:
            instructions = st.text_area(
                "Instructions",
                placeholder="e.g., Add more objections around implementation timeline. Make the agenda tighter.",
                height=80,
                key=f"instructions_{expander_key_suffix}",
            )
        if st.button("Refine Section", key=f"refine_btn_{expander_key_suffix}", type="primary"):
            if not instructions.strip():
                st.warning("Please enter refinement instructions.", icon="⚠️")
            else:
                current = _parse_section(st.session_state[output_key], section)
                ph = st.empty()
                refined = ""
                with st.spinner(f"Rewriting {section}..."):
                    try:
                        for chunk in refine_section(
                            section_name=section,
                            current_content=current,
                            full_brief=st.session_state[output_key],
                            instructions=instructions.strip(),
                            company=inputs.get("company", ""),
                            industry=inputs.get("industry", ""),
                            solutions=inputs.get("solutions", []),
                        ):
                            refined += chunk
                            ph.markdown(refined)
                        st.session_state[output_key] = _replace_section(
                            st.session_state[output_key], section, refined
                        )
                        st.success(f"{section} updated!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Refinement failed: {e}", icon="❌")

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "brief_output": "",
    "last_inputs": {},
    "flow_data": None,
    "demo_prep_output": "",
    "demo_prep_last_inputs": {},
    "demo_delivery_output": "",
    "demo_delivery_last_inputs": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 Discovery", "🎯 Demo Prep", "🚀 Demo Delivery"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    with st.form("discovery_form"):
        st.markdown("#### Customer Details")
        col1, col2 = st.columns([1, 1])

        with col1:
            company_name = st.text_input(
                "Company Name *",
                placeholder="e.g., Acme Corporation",
                help="The name of the company you are meeting with.",
            )
            industry = st.selectbox(
                "Industry *",
                options=INDUSTRIES,
                help="Select the industry that best matches this customer.",
            )
            lob = st.multiselect(
                "Line of Business Focus (optional)",
                options=[
                    "Finance & Controlling", "Procurement & Sourcing",
                    "Supply Chain & Logistics", "Manufacturing & Operations",
                    "Sales & Order Management", "HR & Workforce",
                    "IT & Digital Transformation", "Sustainability & ESG",
                ],
                default=[],
                help="Narrow the discovery focus to specific business functions.",
            )

        with col2:
            solutions = st.multiselect(
                "SAP Solutions Being Positioned *",
                options=list(SOLUTION_FILES.keys()),
                default=[],
                help="Select one or more SAP solutions you plan to position in this meeting.",
            )
            additional_context = st.text_area(
                "Additional Context (optional)",
                placeholder="e.g., Customer is on SAP ECC 6.0 with a 2027 deadline. Competing against Oracle.",
                height=120,
            )

        uploaded_files = st.file_uploader(
            "Supporting Documents (optional)",
            type=["pdf", "docx", "txt", "md", "csv", "xlsx", "pptx"],
            accept_multiple_files=True,
            help="Annual reports, RFPs, org charts, meeting notes. Content is fed to the agent.",
        )
        account_context = st.text_area(
            "Account Context (optional)",
            placeholder=(
                "e.g., Meeting with Sarah (CFO) who is championing this deal. "
                "Mike (IT Director) is skeptical. Previous meeting stalled on pricing."
            ),
            height=100,
            help="Stakeholders, deal history, customer preferences, relationship dynamics.",
        )
        submitted_d = st.form_submit_button("Generate Discovery Brief", use_container_width=False)

    if submitted_d:
        errors = []
        if not company_name.strip():
            errors.append("Company Name is required.")
        if not solutions:
            errors.append("Please select at least one SAP solution.")
        if errors:
            for err in errors:
                st.error(err, icon="⚠️")
        else:
            st.session_state.brief_output = ""
            st.session_state.flow_data = None
            st.session_state.last_inputs = {
                "company": company_name.strip(),
                "industry": industry,
                "lob": lob,
                "solutions": solutions,
                "context": additional_context.strip(),
                "account_context": account_context.strip(),
                "uploaded_files": uploaded_files or [],
            }

    d_inputs = st.session_state.last_inputs
    if d_inputs:
        st.divider()
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"### Discovery Brief — **{d_inputs['company']}** | {d_inputs['industry']}")
            st.caption(f"Solutions: {', '.join(d_inputs['solutions'])}")
            if d_inputs.get("uploaded_files"):
                st.caption(f"Documents: {', '.join(f.name for f in d_inputs['uploaded_files'])}")
        with cols[1]:
            if st.button("Clear", key="clear_discovery", use_container_width=True):
                st.session_state.brief_output = ""
                st.session_state.last_inputs = {}
                st.session_state.flow_data = None
                st.rerun()

        if submitted_d and not st.session_state.brief_output:
            ph = st.empty()
            full_text = ""
            with st.spinner("Generating discovery brief..."):
                try:
                    for chunk in run_discovery(
                        company_name=d_inputs["company"],
                        industry=d_inputs["industry"],
                        solutions=d_inputs["solutions"],
                        additional_context=d_inputs.get("context", ""),
                        account_context=d_inputs.get("account_context", ""),
                        lob=d_inputs.get("lob") or [],
                        uploaded_files=d_inputs.get("uploaded_files"),
                    ):
                        full_text += chunk
                        ph.markdown(full_text)
                    clean_text, flow_data = extract_process_flow(full_text)
                    st.session_state.brief_output = clean_text
                    st.session_state.flow_data = flow_data
                    ph.markdown(clean_text)
                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="❌")
            st.success("Discovery brief generated!", icon="✅")

        elif st.session_state.brief_output:
            st.markdown(st.session_state.brief_output)

        if st.session_state.flow_data:
            fig = render_process_flow(st.session_state.flow_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        if st.session_state.brief_output:
            slug = d_inputs['company'].replace(' ', '_').lower()
            _download_row(st.session_state.brief_output, slug, "discovery")
            _refine_expander("brief_output", DISCOVERY_SECTIONS, d_inputs, "discovery")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEMO PREP
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    # Pre-fill hint
    if st.session_state.brief_output and not st.session_state.demo_prep_output:
        st.info(
            "Your discovery brief is ready to use. It has been pre-loaded into the form below.",
            icon="💡",
        )

    with st.form("demo_prep_form"):
        st.markdown("#### Demo Details")
        col1, col2 = st.columns([1, 1])

        # Pull defaults from Discovery if available
        d = st.session_state.last_inputs

        with col1:
            dp_company = st.text_input(
                "Company Name *",
                value=d.get("company", ""),
                placeholder="e.g., Acme Corporation",
            )
            dp_industry = st.selectbox(
                "Industry *",
                options=INDUSTRIES,
                index=INDUSTRIES.index(d["industry"]) if d.get("industry") in INDUSTRIES else 0,
            )
            dp_duration = st.selectbox(
                "Demo Duration *",
                options=["30 minutes", "45 minutes", "60 minutes", "90 minutes"],
                index=2,
            )

        with col2:
            dp_solutions = st.multiselect(
                "SAP Solutions Being Demonstrated *",
                options=list(SOLUTION_FILES.keys()),
                default=d.get("solutions", []),
            )
            dp_focus = st.text_area(
                "Demo Focus (optional)",
                placeholder="e.g., CFO cares most about close speed and working capital. Skip shop-floor content.",
                height=80,
            )
            dp_audience = st.text_area(
                "Audience in the Room (optional)",
                placeholder="e.g., CFO (Sarah), VP IT (Mike — skeptical), 2 controllers.",
                height=80,
            )

        dp_brief = st.text_area(
            "Discovery Brief *",
            value=st.session_state.brief_output,
            placeholder="Paste your discovery brief here, or generate one in the Discovery tab first.",
            height=200,
            help="This brief is used to ground all demo prep content in the customer's specific situation.",
        )

        submitted_dp = st.form_submit_button("Generate Demo Prep", use_container_width=False)

    if submitted_dp:
        errors = []
        if not dp_company.strip():
            errors.append("Company Name is required.")
        if not dp_solutions:
            errors.append("Please select at least one SAP solution.")
        if not dp_brief.strip():
            errors.append("Discovery Brief is required.")
        if errors:
            for err in errors:
                st.error(err, icon="⚠️")
        else:
            st.session_state.demo_prep_output = ""
            st.session_state.demo_prep_last_inputs = {
                "company": dp_company.strip(),
                "industry": dp_industry,
                "solutions": dp_solutions,
                "duration": dp_duration,
                "focus": dp_focus.strip(),
                "audience": dp_audience.strip(),
                "brief": dp_brief.strip(),
            }

    dp_inputs = st.session_state.demo_prep_last_inputs
    if dp_inputs:
        st.divider()
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"### Demo Prep — **{dp_inputs['company']}** | {dp_inputs['industry']}")
            st.caption(f"Solutions: {', '.join(dp_inputs['solutions'])} · {dp_inputs['duration']}")
        with cols[1]:
            if st.button("Clear", key="clear_demo_prep", use_container_width=True):
                st.session_state.demo_prep_output = ""
                st.session_state.demo_prep_last_inputs = {}
                st.rerun()

        if submitted_dp and not st.session_state.demo_prep_output:
            ph = st.empty()
            full_text = ""
            with st.spinner("Generating demo prep..."):
                try:
                    for chunk in run_demo_prep(
                        company_name=dp_inputs["company"],
                        industry=dp_inputs["industry"],
                        solutions=dp_inputs["solutions"],
                        discovery_brief=dp_inputs["brief"],
                        demo_duration=dp_inputs["duration"],
                        demo_focus=dp_inputs.get("focus", ""),
                        audience=dp_inputs.get("audience", ""),
                    ):
                        full_text += chunk
                        ph.markdown(full_text)
                    st.session_state.demo_prep_output = full_text
                    ph.markdown(full_text)
                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="❌")
            st.success("Demo prep generated!", icon="✅")

        elif st.session_state.demo_prep_output:
            st.markdown(st.session_state.demo_prep_output)

        if st.session_state.demo_prep_output:
            slug = dp_inputs['company'].replace(' ', '_').lower()
            _download_row(st.session_state.demo_prep_output, slug, "demo_prep")
            _refine_expander("demo_prep_output", DEMO_PREP_SECTIONS, dp_inputs, "demo_prep")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DEMO DELIVERY
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if st.session_state.demo_prep_output and not st.session_state.demo_delivery_output:
        st.info(
            "Your demo prep brief is ready to use. It has been pre-loaded into the form below.",
            icon="💡",
        )

    with st.form("demo_delivery_form"):
        st.markdown("#### Delivery Details")
        col1, col2 = st.columns([1, 1])

        dp = st.session_state.demo_prep_last_inputs or st.session_state.last_inputs

        with col1:
            dd_company = st.text_input(
                "Company Name *",
                value=dp.get("company", ""),
                placeholder="e.g., Acme Corporation",
            )
            dd_industry = st.selectbox(
                "Industry *",
                options=INDUSTRIES,
                index=INDUSTRIES.index(dp["industry"]) if dp.get("industry") in INDUSTRIES else 0,
            )

        with col2:
            dd_solutions = st.multiselect(
                "SAP Solutions *",
                options=list(SOLUTION_FILES.keys()),
                default=dp.get("solutions", []),
            )
            dd_context = st.text_area(
                "Last-Minute Context (optional)",
                placeholder="e.g., CIO just joined the call. They mentioned Oracle renewed yesterday. CFO has a hard stop at :45.",
                height=100,
            )

        dd_prep_brief = st.text_area(
            "Demo Prep Brief *",
            value=st.session_state.demo_prep_output,
            placeholder="Paste your demo prep brief here, or generate one in the Demo Prep tab first.",
            height=200,
            help="The delivery pack will be grounded entirely in this brief.",
        )

        submitted_dd = st.form_submit_button("Generate Delivery Pack", use_container_width=False)

    if submitted_dd:
        errors = []
        if not dd_company.strip():
            errors.append("Company Name is required.")
        if not dd_solutions:
            errors.append("Please select at least one SAP solution.")
        if not dd_prep_brief.strip():
            errors.append("Demo Prep Brief is required.")
        if errors:
            for err in errors:
                st.error(err, icon="⚠️")
        else:
            st.session_state.demo_delivery_output = ""
            st.session_state.demo_delivery_last_inputs = {
                "company": dd_company.strip(),
                "industry": dd_industry,
                "solutions": dd_solutions,
                "context": dd_context.strip(),
                "prep_brief": dd_prep_brief.strip(),
            }

    dd_inputs = st.session_state.demo_delivery_last_inputs
    if dd_inputs:
        st.divider()
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"### Demo Delivery Pack — **{dd_inputs['company']}** | {dd_inputs['industry']}")
            st.caption(f"Solutions: {', '.join(dd_inputs['solutions'])}")
        with cols[1]:
            if st.button("Clear", key="clear_demo_delivery", use_container_width=True):
                st.session_state.demo_delivery_output = ""
                st.session_state.demo_delivery_last_inputs = {}
                st.rerun()

        if submitted_dd and not st.session_state.demo_delivery_output:
            ph = st.empty()
            full_text = ""
            with st.spinner("Generating delivery pack..."):
                try:
                    for chunk in run_demo_delivery(
                        company_name=dd_inputs["company"],
                        industry=dd_inputs["industry"],
                        solutions=dd_inputs["solutions"],
                        demo_prep_brief=dd_inputs["prep_brief"],
                        last_minute_context=dd_inputs.get("context", ""),
                    ):
                        full_text += chunk
                        ph.markdown(full_text)
                    st.session_state.demo_delivery_output = full_text
                    ph.markdown(full_text)
                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="❌")
            st.success("Delivery pack generated!", icon="✅")

        elif st.session_state.demo_delivery_output:
            st.markdown(st.session_state.demo_delivery_output)

        if st.session_state.demo_delivery_output:
            slug = dd_inputs['company'].replace(' ', '_').lower()
            _download_row(st.session_state.demo_delivery_output, slug, "demo_delivery")
            _refine_expander("demo_delivery_output", DEMO_DELIVERY_SECTIONS, dd_inputs, "demo_delivery")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Powered by Claude Opus · "
    "Solution knowledge from local SAP capability files · "
    "For internal SAP presales use only"
)
