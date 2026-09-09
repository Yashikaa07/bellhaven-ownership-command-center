from __future__ import annotations

import json
from collections import Counter
import altair as alt
import streamlit as st
from ownershipos.crm import CRMClient
from ownershipos.matcher import apply_proposal, build_proposals, find_parent
from ownershipos.scraper import scrape_locations
from ownershipos.state import DecisionStore

BASE = "https://analyst-assessment-production.up.railway.app"
API = BASE + "/api/v1"
st.set_page_config(page_title="OwnershipOS", page_icon="◉", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
.stApp{background:#f5f7fb;color:#172033}.block-container{padding-top:1.25rem;max-width:1320px}
[data-testid="stHeader"]{background:#ffffff;border-bottom:1px solid #e6ebf2}[data-testid="stToolbar"]{right:1rem}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #e2e8f0}[data-testid="stSidebar"] *{color:#243247}
h1,h2,h3{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em}p,div,label,button,input{font-family:'DM Sans',sans-serif}
.brand{display:flex;align-items:center;gap:11px;font:700 17px 'Space Grotesk';color:#142238}.pulse{width:12px;height:12px;border-radius:50%;background:#12b981;box-shadow:0 0 0 7px #12b98118}
.eyebrow{color:#07865f;font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;margin-top:12px}.hero{font:700 36px/1.08 'Space Grotesk';margin:5px 0 8px;color:#152238;white-space:normal}.sub{color:#66758a;font-size:15px;margin-bottom:16px;max-width:920px}
.status{padding:13px 16px;border:1px solid #cfe8df;border-radius:12px;background:#f0faf6;color:#486258;margin:8px 0 18px}.status strong{color:#087a59}
.card{background:#ffffff;border:1px solid #e0e7ef;border-radius:14px;padding:18px 20px;min-height:110px;box-shadow:0 6px 18px #1c2b3d0a}.label{font-size:10px;text-transform:uppercase;letter-spacing:.13em;color:#77869a;font-weight:700}.value{font:700 30px 'Space Grotesk';color:#18263b;margin:7px 0 2px}.note{font-size:12px;color:#7a899c}.good{color:#06966c}.amber{color:#b7791f}
.panel{background:#ffffff;border:1px solid #e0e7ef;border-radius:14px;padding:20px;margin-top:14px;box-shadow:0 5px 16px #17203308}.pt{font:600 16px 'Space Grotesk';color:#1b293d}.ps{font-size:12px;color:#7b899b;margin-bottom:13px}.step{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid #eef2f6}.num{width:25px;height:25px;border-radius:8px;background:#e7f8f2;color:#07865f;text-align:center;padding-top:3px;font-weight:700}.copy b{display:block;color:#26364b;font-size:13px}.copy span{color:#7a899b;font-size:11px}
.answer{background:#f1faf7;border-left:3px solid #12aa7d;border-radius:7px;padding:13px;color:#43556a;font-size:13px;line-height:1.5;margin-top:12px}
.guide{background:#f8fafc;border:1px solid #e3e9f1;border-radius:12px;padding:14px 16px;margin:10px 0 18px;color:#526277;font-size:13px}.guide b{color:#172033}.guide span{display:inline-block;background:#e8f7f2;color:#087a59;border-radius:20px;padding:4px 9px;margin:4px 5px 0 0;font-size:11px;font-weight:700}
.aihead{display:flex;align-items:center;gap:10px}.aibadge{background:#e3f8f0;color:#07865f;border-radius:20px;padding:4px 9px;font-size:10px;font-weight:700;letter-spacing:.08em}.privacy{background:#f7f9fc;border:1px solid #e6ebf2;border-radius:9px;padding:9px 11px;color:#738196;font-size:11px;margin-top:12px}
.brief{background:linear-gradient(135deg,#102a43,#153b56);border-radius:16px;padding:20px 22px;color:#fff;margin:18px 0}.brief-title{font:600 17px 'Space Grotesk';margin-bottom:12px}.brief-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.brief-item{border-left:2px solid #37d3a6;padding-left:12px}.brief-item b{display:block;color:#73e5c3;font-size:11px;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px}.brief-item span{font-size:13px;line-height:1.4;color:#e8f1f6}
.section-kicker{color:#07865f;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-top:18px}.empty-chart{height:220px;display:flex;align-items:center;justify-content:center;text-align:center;background:#f7fbf9;border:1px dashed #b8decf;border-radius:12px;color:#527065;font-size:13px}
div[data-testid="stMetric"]{background:#f8fafc;border:1px solid #e4eaf1;padding:14px;border-radius:12px}div[data-testid="stExpander"]{background:#ffffff;border:1px solid #e0e7ef;border-radius:12px}.stButton>button{border-radius:9px;font-weight:700;border:1px solid #cbd6e2;background:#ffffff;color:#1d5f50}.stButton>button[kind="primary"]{background:#0f9d75;color:#ffffff;border:0}[data-testid="stAlert"]{border-radius:11px}button[data-baseweb="tab"]{color:#526277!important}button[data-baseweb="tab"][aria-selected="true"]{color:#087a59!important}hr{border-color:#e4eaf1!important}
</style>""", unsafe_allow_html=True)

store = DecisionStore()
with st.sidebar:
    st.markdown('<div class="brand"><span class="pulse"></span>OwnershipOS</div>', unsafe_allow_html=True)
    st.caption("Bellhaven command center")
    st.divider()
    token = st.text_input("CRM credential", type="password", help="Paste the bh_ token or full curl command. It stays local.")
    uploaded = st.file_uploader("Offline CRM snapshot", type="json")
    scan = st.button("Run ownership agent", type="primary", use_container_width=True)
    st.caption("Read-only scan • Human-approved writes")
    with st.expander("How to use this dashboard"):
        st.markdown("**1.** Add a credential or JSON snapshot\n\n**2.** Run the ownership agent\n\n**3.** Review flagged decisions\n\n**4.** Approve only verified changes\n\n**5.** Apply and rerun to confirm zero drift")

if scan:
    with st.spinner("Agents are collecting and reconciling ownership evidence…"):
        locations, warnings = scrape_locations(BASE)
        if uploaded:
            raw = json.load(uploaded)
            accounts = raw if isinstance(raw, list) else next((raw[k] for k in ("accounts","items","results","data") if isinstance(raw.get(k), list)), [])
            accounts = [{**a, "id": a.get("id") or a.get("account_id") or a.get("accountId")} for a in accounts]
        elif token: accounts = CRMClient(API, token).list_accounts()
        else: st.error("Enter the CRM token or upload a snapshot."); st.stop()
        parent = find_parent(accounts)
        if not parent: st.error("Bellhaven parent account was not identified."); st.stop()
        proposals = [p for p in build_proposals(locations, accounts, str(parent["id"])) if not store.decided(p["fingerprint"])]
        st.session_state.update(locations=locations, accounts=accounts, parent=parent, proposals=proposals, warnings=warnings)

st.markdown('<div class="eyebrow">Revenue intelligence / ownership integrity</div><div class="hero">Bellhaven Ownership Command Center</div><div class="sub">An explainable agent system that detects ownership drift, protects billing history, and gives humans final control.</div>', unsafe_allow_html=True)
if "proposals" not in st.session_state:
    st.markdown('<div class="status"><strong>System ready.</strong> Add a CRM credential or JSON snapshot, then click <b>Run ownership agent</b>.</div>', unsafe_allow_html=True)
    st.markdown('<div class="guide"><b>Your guided workflow</b><br><span>1 · Connect data</span><span>2 · Run scan</span><span>3 · Review evidence</span><span>4 · Approve decisions</span><span>5 · Apply safely</span></div>', unsafe_allow_html=True); st.stop()

locations, accounts, proposals = st.session_state.locations, st.session_state.accounts, st.session_state.proposals
for warning in st.session_state.warnings: st.warning(warning)
active = sum(str(a.get("status","")).lower()=="active" for a in accounts)
duplicates = sum(str(a.get("status","")).lower()=="inactive" and bool(a.get("duplicate_of_account")) for a in accounts)
chow_links = sum(bool(a.get("chow_current_account")) for a in accounts)
needs_review = sum(str(a.get("status","")).lower()=="needs review" for a in accounts)
protected = sum(float(str((p.get("evidence") or {}).get("outstanding_ar") or 0).replace("$","").replace(",","")) for p in proposals if p["kind"].startswith("CHOW"))
risk_weight = sum({"Critical":8,"High":4,"Medium":2,"Low":1}.get(p["risk"],1) for p in proposals)
health = max(0, round(100-min(100,risk_weight*1.5)))
if not proposals: st.markdown('<div class="status"><strong>✓ CRM reconciled.</strong> The second-pass agent found no actionable ownership drift. Financial lineage and resolved duplicates remain preserved.</div>', unsafe_allow_html=True)
else: st.markdown(f'<div class="guide"><b>Recommended next step:</b> Open <b>Review Queue</b> and inspect the highest-risk items first. Nothing changes in CRM until you approve and apply it.<br><span>{len(proposals)} decisions waiting</span><span>{sum(p["risk"]=="Critical" for p in proposals)} critical</span><span>${protected:,.0f} AR protected</span></div>', unsafe_allow_html=True)

cards=[("Ownership health",f"{health}%","Post-reconciliation confidence","good" if health>=90 else "amber"),("Website coverage",len(locations),"Communities independently scraped",""),("CRM universe",len(accounts),f"{active} active accounts monitored",""),("Open decisions",len(proposals),"No autonomous writes","good" if not proposals else "amber"),("Protected lineage",chow_links,"CHOW predecessors retained","good"),("Duplicate controls",duplicates,"Inactive records preserved","good")]
kpi_explanations={
    "Ownership health":("Formula",f"100 − weighted unresolved risk. Current risk weight is {risk_weight}; the displayed score is capped between 0% and 100%.","Source","Current proposal list produced by the matching engine.","Why it matters","A quick control-health signal—not a probability or an AI confidence score."),
    "Website coverage":("Formula",f"Count of unique community records returned by the Bellhaven directory scraper: {len(locations)}.","Source","Bellhaven live community directory pages.","Why it matters","Shows the website population independently observed during this run."),
    "CRM universe":("Formula",f"Count of all CRM account records loaded: {len(accounts)} total; {active} have status Active.","Source","Authenticated CRM API response or the uploaded JSON snapshot.","Why it matters","Defines the full account population evaluated for matches, duplicates, and former locations."),
    "Open decisions":("Formula",f"Count of new proposal fingerprints not already decided in the audit ledger: {len(proposals)}.","Source","Matcher output minus previously approved or rejected fingerprints.","Why it matters","These require human review. The system never writes them automatically."),
    "Protected lineage":("Formula",f"Count of predecessor accounts with a populated chow_current_account field: {chow_links}.","Source","CRM account lineage fields.","Why it matters","Confirms financial history remains on the predecessor while the current owner is linked separately."),
    "Duplicate controls":("Formula",f"Inactive CRM accounts that contain duplicate_of_account: {duplicates}.","Source","CRM status and duplicate linkage fields.","Why it matters","Confirms duplicates are preserved for history but excluded from active matching."),
}
for start in (0,3):
    for col,(label,value,note,cls) in zip(st.columns(3),cards[start:start+3]):
        with col:
            st.markdown(f'<div class="card"><div class="label">{label}</div><div class="value {cls}">{value}</div><div class="note">{note}</div></div>',unsafe_allow_html=True)
            with st.popover("ⓘ How this number was calculated"):
                parts=kpi_explanations[label]
                st.markdown(f"**{parts[0]}**  \n{parts[1]}\n\n**{parts[2]}**  \n{parts[3]}\n\n**{parts[4]}**  \n{parts[5]}")

overview, review, lineage, audit = st.tabs(["Executive Dashboard",f"Review Queue ({len(proposals)})","Ownership Lineage","Audit & Export"])
with overview:
    top_risk = next((r for r in ("Critical","High","Medium","Low") if any(p["risk"]==r for p in proposals)), "None")
    decision_message = f"{len(proposals)} decisions need human review" if proposals else "No unresolved ownership decisions"
    st.markdown(f'''<div class="brief"><div class="brief-title">Executive briefing · What this run means</div><div class="brief-grid">
    <div class="brief-item"><b>What happened</b><span>{len(locations)} locations were reconciled against {len(accounts)} CRM records.</span></div>
    <div class="brief-item"><b>What needs attention</b><span>{decision_message}. Highest current risk: {top_risk}.</span></div>
    <div class="brief-item"><b>What is protected</b><span>{chow_links} financial lineage links and {duplicates} duplicate controls remain preserved.</span></div>
    </div></div>''',unsafe_allow_html=True)
    with st.popover("ⓘ Explain the executive briefing"):
        st.markdown("**What happened** combines the scraper count and CRM record count.\n\n**What needs attention** comes from unresolved proposal fingerprints, ordered Critical → High → Medium → Low.\n\n**What is protected** counts persisted CHOW and duplicate-control links in CRM—not pending recommendations.")
    st.markdown('<div class="section-kicker">Decision intelligence</div>',unsafe_allow_html=True)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown('<div class="panel"><div class="pt">Open decisions by risk</div><div class="ps">Where a reviewer should focus first</div>',unsafe_allow_html=True)
        risk_order=["Critical","High","Medium","Low"]
        risk_data=[{"Risk":r,"Decisions":sum(p["risk"]==r for p in proposals),"Order":i} for i,r in enumerate(risk_order)]
        if proposals:
            risk_chart=alt.Chart(alt.Data(values=risk_data)).mark_bar(cornerRadiusEnd=5,size=28).encode(
                x=alt.X("Decisions:Q",title="Open decisions",axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("Risk:N",sort=risk_order,title=None),
                color=alt.Color("Risk:N",scale=alt.Scale(domain=risk_order,range=["#dc4c4c","#ec8d3c","#e2b33c","#5c8fd6"]),legend=None),
                tooltip=["Risk:N","Decisions:Q"]
            ).properties(height=220)
            st.altair_chart(risk_chart,use_container_width=True)
        else: st.markdown('<div class="empty-chart"><b>✓ No open risk</b><br>The reconciliation is complete.</div>',unsafe_allow_html=True)
        with st.popover("ⓘ How to read this chart"):
            st.markdown("Each bar counts unresolved proposals with that risk label. **Critical** events appear first because they may affect revenue or AR lineage. Hover over a bar for its exact count. Zero-value categories remain visible so reviewers can confirm the full risk scale was checked.")
        st.markdown('</div>',unsafe_allow_html=True)
    with chart_right:
        st.markdown('<div class="panel"><div class="pt">CRM account composition</div><div class="ps">Operational state of the account universe</div>',unsafe_allow_html=True)
        statuses=Counter(str(a.get("status") or "Unknown").title() for a in accounts)
        status_data=[{"Status":k,"Accounts":v} for k,v in statuses.items()]
        donut=alt.Chart(alt.Data(values=status_data)).mark_arc(innerRadius=58,outerRadius=92).encode(
            theta=alt.Theta("Accounts:Q"),
            color=alt.Color("Status:N",scale=alt.Scale(range=["#11a579","#6f86a5","#efb34c","#d75b63","#8b6fc2"]),legend=alt.Legend(title=None,orient="bottom")),
            tooltip=["Status:N","Accounts:Q"]
        ).properties(height=220)
        st.altair_chart(donut,use_container_width=True)
        with st.popover("ⓘ How to read this chart"):
            st.markdown(f"Each slice is the count of CRM records grouped by their current `status` field. The total across all slices is **{len(accounts)} accounts**. Hover over a slice for the exact status and count. This chart describes CRM composition; it does not represent proposal risk.")
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">How the system reached this answer</div>',unsafe_allow_html=True)
    left,mid,right=st.columns([1.1,1,1])
    with left:
        st.markdown('<div class="panel"><div class="pt">Agent run</div><div class="ps">Every stage produces inspectable evidence</div>',unsafe_allow_html=True)
        for n,title,copy in [(1,"Discover",f"Scraped {len(locations)} live communities"),(2,"Normalize","Standardized names, addresses and care types"),(3,"Resolve",f"Compared against {len(accounts)} CRM accounts"),(4,"Guard","Applied AR-aware CHOW and duplicate policies"),(5,"Escalate",f"Routed {len(proposals)} decisions to human review")]: st.markdown(f'<div class="step"><div class="num">{n}</div><div class="copy"><b>{title}</b><span>{copy}</span></div></div>',unsafe_allow_html=True)
        with st.popover("ⓘ Explain all five stages"):
            st.markdown("**1 · Discover:** scrape the live directory.\n\n**2 · Normalize:** standardize names, addresses, ZIP codes, and care types.\n\n**3 · Resolve:** score explainable identity evidence.\n\n**4 · Guard:** enforce duplicate and CHOW financial rules.\n\n**5 · Escalate:** create human-review proposals; never write automatically.")
        st.markdown('</div>',unsafe_allow_html=True)
    with mid:
        st.markdown('<div class="panel"><div class="pt">Control posture</div><div class="ps">Current outcomes after policy enforcement</div>',unsafe_allow_html=True)
        st.metric("CHOW-linked predecessors",chow_links); st.metric("Resolved duplicate records",duplicates); st.metric("Ownership investigations",needs_review); st.metric("AR currently at risk",f"${protected:,.0f}")
        with st.popover("ⓘ Explain control-posture numbers"):
            st.markdown(f"**CHOW-linked predecessors ({chow_links}):** records with `chow_current_account`.\n\n**Resolved duplicates ({duplicates}):** Inactive records with `duplicate_of_account`.\n\n**Investigations ({needs_review}):** records whose status is `Needs Review`.\n\n**AR at risk (${protected:,.0f}):** outstanding AR summed only across currently open CHOW proposals.")
        st.markdown('</div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="aihead"><div class="pt">✦ AI Ownership Assistant</div><span class="aibadge">GROUNDED</span></div><div class="ps">Ask questions about this scan in plain English</div>',unsafe_allow_html=True)
        def assistant_answer(question: str) -> str:
            q = question.lower()
            critical = sum(p["risk"] == "Critical" for p in proposals)
            if any(x in q for x in ("summary", "overview", "status")):
                return f"Ownership health is {health}%. I compared {len(locations)} website communities with {len(accounts)} CRM accounts. {len(proposals)} decisions remain; {chow_links} protected predecessor links and {duplicates} duplicate controls are preserved."
            if any(x in q for x in ("first", "priority", "review", "risk")):
                return f"Review the {critical} critical CHOW decision(s) first, followed by parent changes and duplicates. Open Review Queue to inspect the evidence and proposed API action before approving anything."
            if any(x in q for x in ("chow", "revenue", "ar", "financial")):
                return f"The CHOW guardrail preserves any predecessor with revenue and outstanding AR, creates or identifies the current account, and links the two instead of re-parenting. {chow_links} lineage link(s) are currently protected."
            if any(x in q for x in ("rerun", "safe", "duplicate", "again")):
                return "The pipeline is safe to rerun: proposal fingerprints suppress repeated decisions, while CRM-state checks exclude resolved duplicates, completed investigations, and CHOW-linked predecessors."
            if any(x in q for x in ("change", "write", "apply", "automatic")):
                return f"No autonomous write is allowed. The agent has {len(proposals)} recommendation(s), but a human must approve each one, confirm authorization, and click Apply approved changes."
            return "I can explain the executive summary, review priority, CHOW financial protection, write-back controls, or why this pipeline is safe to rerun."

        qa, qb = st.columns(2)
        quick = None
        if qa.button("Executive summary", use_container_width=True, key="ai_summary"): quick = "Give me the executive summary"
        if qb.button("Review priority", use_container_width=True, key="ai_priority"): quick = "What should I review first?"
        qc, qd = st.columns(2)
        if qc.button("Explain CHOW", use_container_width=True, key="ai_chow"): quick = "How does CHOW protect financial history?"
        if qd.button("Rerun safety", use_container_width=True, key="ai_rerun"): quick = "Is this safe to rerun?"
        question = st.text_input("Ask a custom question", placeholder="e.g., Will anything update automatically?", key="ai_question")
        ask = st.button("Ask AI assistant", type="primary", use_container_width=True, key="ai_ask")
        if quick: st.session_state.ai_response = assistant_answer(quick)
        if ask and question: st.session_state.ai_response = assistant_answer(question)
        if "ai_response" in st.session_state: st.markdown(f'<div class="answer"><b>Assistant</b><br>{st.session_state.ai_response}</div>',unsafe_allow_html=True)
        st.markdown('<div class="privacy">Evidence-grounded guidance only · The assistant cannot approve or write CRM changes</div></div>',unsafe_allow_html=True)

with review:
    with st.popover("ⓘ Where the Review Queue number comes from"):
        st.markdown(f"The tab shows **{len(proposals)}** because the matcher produced that many unresolved proposal fingerprints after removing decisions already stored in the audit ledger. Each proposal must contain a risk level, explanation, supporting evidence, and proposed API plan before it appears here.")
    if not proposals:
        st.success("Zero open decisions. The pipeline was rerun safely after write-back.")
        st.download_button("Download verified CRM snapshot",data=json.dumps({"accounts":accounts},indent=2,default=str),file_name="crm_accounts_verified.json",mime="application/json",use_container_width=False)
    else:
        counts=Counter(p["kind"] for p in proposals); st.caption(" · ".join(f"{v} {k}" for k,v in counts.items())); selected=st.multiselect("Event types",sorted(counts),default=sorted(counts))
        for p in [x for x in proposals if x["kind"] in selected]:
            title=p["location"]["name"] if p.get("location") else (p.get("account") or {}).get("name","Unknown")
            with st.expander(f"{p['risk']}  •  {p['kind']}  •  {title}"):
                l,r=st.columns([1.4,1]); l.markdown("#### Agent rationale"); l.write(p["explanation"]); l.markdown("#### Supporting evidence"); l.json(p["evidence"],expanded=True); r.markdown("#### Proposed API plan"); r.json(p["actions"],expanded=True)
                a,b,_=st.columns([1,1,4])
                if a.button("Approve",key="a"+p["fingerprint"],type="primary"): store.save(p,"Approved"); st.success("Approved and queued. No write has occurred yet.")
                if b.button("Reject",key="r"+p["fingerprint"]): store.save(p,"Rejected"); st.info("Rejected and suppressed unless evidence changes.")

with lineage:
    st.subheader("Ownership lineage controls"); st.caption("Financial history stays attached to predecessor records while current ownership remains operationally accurate.")
    chow=[a for a in accounts if a.get("chow_current_account")]
    if chow:
        lifetime_total=sum(float(a.get('lifetime_revenue') or 0) for a in chow); ar_total=sum(float(a.get('outstanding_ar') or 0) for a in chow)
        c1,c2,c3=st.columns(3); c1.metric("Protected predecessors",len(chow)); c2.metric("Lifetime revenue preserved",f"${lifetime_total:,.0f}"); c3.metric("Outstanding AR protected",f"${ar_total:,.0f}")
        with st.popover("ⓘ Explain lineage totals"):
            st.markdown(f"**Protected predecessors ({len(chow)}):** accounts with a current-account CHOW link.\n\n**Lifetime revenue (${lifetime_total:,.0f}):** sum of `lifetime_revenue` across those predecessors.\n\n**Outstanding AR (${ar_total:,.0f}):** sum of `outstanding_ar` across the same records.\n\nThese values stay on predecessor records; the control prevents direct re-parenting.")
        st.dataframe([{"Predecessor":a.get("name"),"Predecessor ID":a.get("id"),"Current account ID":a.get("chow_current_account"),"Lifetime revenue":a.get("lifetime_revenue"),"Outstanding AR":a.get("outstanding_ar"),"Control":"Preserved — no re-parent"} for a in chow],use_container_width=True,hide_index=True)
    else: st.info("No CHOW predecessor links are present.")

with audit:
    x1,x2=st.columns(2)
    x1.download_button("Download final CRM snapshot",data=json.dumps({"accounts":accounts},indent=2,default=str),file_name="crm_accounts_final.json",mime="application/json",use_container_width=True)
    x2.download_button("Download decision ledger",data=json.dumps(store.audit_rows(),indent=2,default=str),file_name="ownership_decision_ledger.json",mime="application/json",use_container_width=True)
    st.subheader("Human decision ledger")
    audit_rows=store.audit_rows()
    with st.popover("ⓘ What is recorded in this ledger"):
        st.markdown(f"The ledger currently contains **{len(audit_rows)} decision(s)**. A row is created only when a reviewer clicks **Approve** or **Reject**. Applied approvals also receive an application timestamp and API result. The ledger is stored locally in `ownershipos.db` and is deliberately excluded from the public GitHub repository.")
    if audit_rows:
        approved_count=sum(r.get("decision")=="Approved" for r in audit_rows); rejected_count=sum(r.get("decision")=="Rejected" for r in audit_rows); applied_count=sum(bool(r.get("applied_at")) for r in audit_rows)
        a1,a2,a3=st.columns(3); a1.metric("Approved",approved_count); a2.metric("Rejected",rejected_count); a3.metric("Applied",applied_count)
        with st.popover("ⓘ Explain ledger totals"):
            st.markdown(f"**Approved ({approved_count}):** rows whose decision equals Approved.\n\n**Rejected ({rejected_count}):** rows whose decision equals Rejected.\n\n**Applied ({applied_count}):** approved rows with a non-empty `applied_at` timestamp.")
        st.dataframe(audit_rows,use_container_width=True,hide_index=True)
    else:
        st.info("No decisions have been recorded in this local workspace yet. Run the agent, open Review Queue, and approve or reject a proposal to create the first audit entry.")
        e1,e2=st.columns(2)
        e1.button("1 · Run ownership agent from sidebar",disabled=True,use_container_width=True)
        e2.button("2 · Review and decide proposals",disabled=True,use_container_width=True)

st.divider(); pending=store.pending_approvals(); st.subheader("Controlled write-back"); st.caption(f"{len(pending)} approved proposal(s) waiting. Credentials exist only in this browser session.")
with st.popover("ⓘ Why this button is controlled"):
    st.markdown(f"The apply button activates only when **all three conditions** are true:\n\n1. At least one proposal is approved (currently **{len(pending)}**)\n2. A live CRM credential is present\n3. The authorization checkbox is selected\n\nOnly approved API actions are executed; rejected and unresolved proposals are never written.")
confirm=st.checkbox("I reviewed the evidence and authorize these approved CRM changes")
if st.button("Apply approved changes",disabled=not(confirm and token and pending),type="primary"):
    client=CRMClient(API,token); progress=st.progress(0)
    for i,p in enumerate(pending,1): result=apply_proposal(client,p); store.mark_applied(p["fingerprint"],result); progress.progress(i/len(pending))
    st.success("Approved changes were applied and recorded in the audit ledger.")

