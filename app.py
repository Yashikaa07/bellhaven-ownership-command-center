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
.stApp{background:linear-gradient(120deg,#e9faf3 0,#f5f8fb 24%,#f5f8fb 100%);color:#182235}.block-container{padding:1.45rem 2.1rem 3rem;max-width:1440px}
[data-testid="stHeader"]{background:#ffffffee;border-bottom:1px solid #e5e9ef;box-shadow:0 2px 12px #17334a08}[data-testid="stToolbar"]{right:1rem}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #e5e9ef;box-shadow:8px 0 30px #17453508}[data-testid="stSidebar"] *{color:#243247}[data-testid="stSidebar"]>div:first-child{padding-top:1.4rem}
h1,h2,h3{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em}p,div,label,button,input{font-family:'DM Sans',sans-serif}
.brand{display:flex;align-items:center;gap:11px;font:700 19px 'Space Grotesk';color:#123c32}.pulse{width:13px;height:13px;border-radius:50%;background:#12bf89;box-shadow:0 0 0 7px #12b98118}
.eyebrow{color:#09865f;font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;margin-top:5px}.hero{font:700 31px/1.08 'Space Grotesk';margin:5px 0 7px;color:#172033;white-space:normal}.sub{color:#6b778a;font-size:14px;margin-bottom:14px;max-width:920px}
.status{padding:13px 16px;border:1px solid #cfe8df;border-radius:12px;background:#f0faf6;color:#486258;margin:8px 0 18px}.status strong{color:#087a59}
.card{background:#ffffff;border:1px solid #e0e7ef;border-radius:12px;padding:16px 18px;min-height:100px;box-shadow:0 4px 15px #1c2b3d0b}.label{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#78869a;font-weight:700}.value{font:700 29px 'Space Grotesk';color:#18263b;margin:5px 0 2px}.note{font-size:11px;color:#8591a2}.good{color:#07966c}.amber{color:#b7791f}
.panel{background:#ffffff;border:1px solid #e0e5ec;border-radius:13px;padding:18px;margin-top:12px;box-shadow:0 5px 18px #17203309}.pt{font:600 15px 'Space Grotesk';color:#1b293d}.ps{font-size:11px;color:#8490a1;margin:3px 0 11px}.step{display:flex;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid #eef2f6}.num{width:25px;height:25px;border-radius:50%;background:#e5f8f0;color:#07865f;text-align:center;padding-top:3px;font-weight:700}.copy b{display:block;color:#26364b;font-size:12px}.copy span{color:#7a899b;font-size:11px}
.answer{background:#f1faf7;border-left:3px solid #12aa7d;border-radius:7px;padding:13px;color:#43556a;font-size:13px;line-height:1.5;margin-top:12px}
.guide{background:#f8fafc;border:1px solid #e3e9f1;border-radius:12px;padding:14px 16px;margin:10px 0 18px;color:#526277;font-size:13px}.guide b{color:#172033}.guide span{display:inline-block;background:#e8f7f2;color:#087a59;border-radius:20px;padding:4px 9px;margin:4px 5px 0 0;font-size:11px;font-weight:700}
.aihead{display:flex;align-items:center;gap:10px}.aibadge{background:#e3f8f0;color:#07865f;border-radius:20px;padding:4px 9px;font-size:10px;font-weight:700;letter-spacing:.08em}.privacy{background:#f7f9fc;border:1px solid #e6ebf2;border-radius:9px;padding:9px 11px;color:#738196;font-size:11px;margin-top:12px}
.brief{background:#ffffff;border:1px solid #dfe5ec;border-radius:13px;padding:17px 20px;color:#172033;margin:15px 0;box-shadow:0 5px 18px #17203309}.brief-title{font:600 15px 'Space Grotesk';margin-bottom:12px;color:#153f34}.brief-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:0}.brief-item{border-left:3px solid #21bd88;padding:3px 18px}.brief-item:nth-child(2){border-color:#7667f4}.brief-item:nth-child(3){border-color:#f2ae2e}.brief-item b{display:block;color:#607084;font-size:9px;text-transform:uppercase;letter-spacing:.12em;margin-bottom:5px}.brief-item span{font-size:12px;line-height:1.4;color:#29384c}
.section-kicker{color:#07865f;font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-top:18px}.empty-chart{height:220px;display:flex;align-items:center;justify-content:center;text-align:center;background:#f7fbf9;border:1px dashed #b8decf;border-radius:12px;color:#527065;font-size:13px}
div[data-testid="stPopover"]>button{font:700 28px 'Space Grotesk'!important;color:#0c7055!important;border:0!important;background:transparent!important;padding:0!important;min-height:36px!important;justify-content:flex-start!important}div[data-testid="stPopover"]>button:hover{color:#7657ed!important;transform:translateY(-1px)}
div[data-testid="stVerticalBlockBorderWrapper"]{background:#ffffff;border-color:#e0e5ec!important;border-radius:12px!important;box-shadow:0 4px 15px #1c2b3d0a}div[data-testid="stMetric"]{background:#ffffff;border:1px solid #e4eaf1;padding:13px;border-radius:11px}div[data-testid="stExpander"]{background:#ffffff;border:1px solid #e0e7ef;border-radius:11px}.stButton>button{border-radius:8px;font-weight:600;border:1px solid #ccd6e1;background:#ffffff;color:#176d59}.stButton>button:hover{border-color:#13a87d;color:#0b7659;background:#f2fbf7}.stButton>button[kind="primary"]{background:linear-gradient(90deg,#10a878,#18c692);color:#ffffff;border:0;box-shadow:0 5px 13px #10a87825}[data-testid="stAlert"]{border-radius:10px}button[data-baseweb="tab"]{color:#5e6d80!important;font-size:13px!important}button[data-baseweb="tab"][aria-selected="true"]{color:#087a59!important;font-weight:700!important}hr{border-color:#e4eaf1!important}
@media(max-width:900px){.block-container{padding:1rem}.brief-grid{grid-template-columns:1fr;gap:12px}.brief-item{padding:4px 12px}.hero{font-size:26px}}
</style>""", unsafe_allow_html=True)

store = DecisionStore()

def run_ownership_scan():
    with st.spinner("Agents are collecting and reconciling ownership evidence…"):
        locations, warnings = scrape_locations(BASE)
        if uploaded:
            raw = json.load(uploaded)
            accounts = raw if isinstance(raw, list) else next((raw[k] for k in ("accounts","items","results","data") if isinstance(raw.get(k), list)), [])
            accounts = [{**a, "id": a.get("id") or a.get("account_id") or a.get("accountId")} for a in accounts]
        elif token:
            accounts = CRMClient(API, token).list_accounts()
        else:
            st.error("Enter the CRM token or upload a snapshot.")
            return False
        parent = find_parent(accounts)
        if not parent:
            st.error("Bellhaven parent account was not identified.")
            return False
        proposals = [p for p in build_proposals(locations, accounts, str(parent["id"])) if not store.decided(p["fingerprint"])]
        st.session_state.update(locations=locations, accounts=accounts, parent=parent, proposals=proposals, warnings=warnings)
        return True

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
    run_ownership_scan()

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
def clickable_number(label,value,note,explanation):
    with st.container(border=True):
        st.markdown(f'<div class="label">{label}</div>',unsafe_allow_html=True)
        with st.popover(str(value)):
            st.markdown(explanation)
        st.markdown(f'<div class="note">{note}</div>',unsafe_allow_html=True)

for start in (0,3):
    for col,(label,value,note,cls) in zip(st.columns(3),cards[start:start+3]):
        with col:
            parts=kpi_explanations[label]
            clickable_number(label,value,note,f"**{parts[0]}**  \n{parts[1]}\n\n**{parts[2]}**  \n{parts[3]}\n\n**{parts[4]}**  \n{parts[5]}")

overview, review, lineage, audit = st.tabs(["Executive Dashboard",f"Review Queue ({len(proposals)})","Ownership Lineage","Audit & Export"])
with overview:
    top_risk = next((r for r in ("Critical","High","Medium","Low") if any(p["risk"]==r for p in proposals)), "None")
    decision_message = f"{len(proposals)} decisions need human review" if proposals else "No unresolved ownership decisions"
    st.markdown(f'''<div class="brief"><div class="brief-title">Executive briefing · What this run means</div><div class="brief-grid">
    <div class="brief-item"><b>What happened</b><span>{len(locations)} locations were reconciled against {len(accounts)} CRM records.</span></div>
    <div class="brief-item"><b>What needs attention</b><span>{decision_message}. Highest current risk: {top_risk}.</span></div>
    <div class="brief-item"><b>What is protected</b><span>{chow_links} financial lineage links and {duplicates} duplicate controls remain preserved.</span></div>
    </div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">Decision intelligence</div>',unsafe_allow_html=True)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown('<div class="panel"><div class="pt">Open decisions by risk</div><div class="ps">Where a reviewer should focus first</div>',unsafe_allow_html=True)
        risk_order=["Critical","High","Medium","Low"]
        risk_data=[{"Risk":r,"Decisions":sum(p["risk"]==r for p in proposals),"Order":i} for i,r in enumerate(risk_order)]
        if proposals:
            risk_pick=alt.selection_point(fields=["Risk"],name="risk_pick",on="click")
            risk_chart=alt.Chart(alt.Data(values=risk_data)).mark_bar(cornerRadiusEnd=5,size=28).encode(
                x=alt.X("Decisions:Q",title="Open decisions",axis=alt.Axis(tickMinStep=1)),
                y=alt.Y("Risk:N",sort=risk_order,title=None),
                color=alt.Color("Risk:N",scale=alt.Scale(domain=risk_order,range=["#dc4c4c","#ec8d3c","#e2b33c","#5c8fd6"]),legend=None),
                tooltip=["Risk:N","Decisions:Q"],
                opacity=alt.condition(risk_pick,alt.value(1),alt.value(.65))
            ).add_params(risk_pick).properties(height=220)
            risk_event=st.altair_chart(risk_chart,use_container_width=True,on_select="rerun",selection_mode="risk_pick",key="risk_chart")
            picked=risk_event.get("selection",{}).get("risk_pick",[]) if risk_event else []
            if picked:
                selected_risk=picked[0].get("Risk","Selected")
                selected_count=next((x["Decisions"] for x in risk_data if x["Risk"]==selected_risk),0)
                st.info(f"{selected_risk}: {selected_count} unresolved decision(s). These counts come directly from current proposal risk labels; Critical items are reviewed first because they may affect revenue or AR lineage.")
        else: st.markdown('<div class="empty-chart"><b>✓ No open risk</b><br>The reconciliation is complete.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with chart_right:
        st.markdown('<div class="panel"><div class="pt">CRM account composition</div><div class="ps">Operational state of the account universe</div>',unsafe_allow_html=True)
        statuses=Counter(str(a.get("status") or "Unknown").title() for a in accounts)
        status_data=[{"Status":k,"Accounts":v} for k,v in statuses.items()]
        status_pick=alt.selection_point(fields=["Status"],name="status_pick",on="click")
        donut=alt.Chart(alt.Data(values=status_data)).mark_arc(innerRadius=58,outerRadius=92).encode(
            theta=alt.Theta("Accounts:Q"),
            color=alt.Color("Status:N",scale=alt.Scale(range=["#11a579","#6f86a5","#efb34c","#d75b63","#8b6fc2"]),legend=alt.Legend(title=None,orient="bottom")),
            tooltip=["Status:N","Accounts:Q"],opacity=alt.condition(status_pick,alt.value(1),alt.value(.65))
        ).add_params(status_pick).properties(height=220)
        status_event=st.altair_chart(donut,use_container_width=True,on_select="rerun",selection_mode="status_pick",key="status_chart")
        status_selected=status_event.get("selection",{}).get("status_pick",[]) if status_event else []
        if status_selected:
            chosen=status_selected[0].get("Status","Selected"); chosen_count=statuses.get(chosen,0)
            st.info(f"{chosen}: {chosen_count} of {len(accounts)} CRM accounts. Each slice is calculated by grouping the loaded CRM records by their current status field.")
        st.markdown('</div>',unsafe_allow_html=True)
    visual_left,visual_right=st.columns(2)
    with visual_left:
        st.markdown('<div class="panel"><div class="pt">Reconciliation coverage</div><div class="ps">Website evidence compared with the CRM population</div>',unsafe_allow_html=True)
        coverage_data=[{"Population":"Website locations","Count":len(locations)},{"Population":"Active CRM accounts","Count":active},{"Population":"All CRM accounts","Count":len(accounts)}]
        coverage_pick=alt.selection_point(fields=["Population"],name="coverage_pick",on="click")
        coverage_chart=alt.Chart(alt.Data(values=coverage_data)).mark_bar(cornerRadiusTopLeft=6,cornerRadiusTopRight=6,size=52).encode(
            x=alt.X("Population:N",title=None,sort=["Website locations","Active CRM accounts","All CRM accounts"],axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Count:Q",title="Records",axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Population:N",scale=alt.Scale(range=["#16ba86","#6c63ee","#f3b229"]),legend=None),
            opacity=alt.condition(coverage_pick,alt.value(1),alt.value(.72)),tooltip=["Population:N","Count:Q"]
        ).add_params(coverage_pick).properties(height=220)
        coverage_event=st.altair_chart(coverage_chart,use_container_width=True,on_select="rerun",selection_mode="coverage_pick",key="coverage_chart")
        coverage_selected=coverage_event.get("selection",{}).get("coverage_pick",[]) if coverage_event else []
        if coverage_selected:
            population=coverage_selected[0].get("Population","Selected"); count=next((x["Count"] for x in coverage_data if x["Population"]==population),0)
            source={"Website locations":"live Bellhaven directory scraper","Active CRM accounts":"CRM records whose status is Active","All CRM accounts":"complete API or uploaded JSON response"}.get(population,"current scan")
            st.info(f"{population}: {count}. This value comes from the {source}.")
        st.markdown('</div>',unsafe_allow_html=True)
    with visual_right:
        st.markdown('<div class="panel"><div class="pt">Protected financial history</div><div class="ps">Value retained on CHOW predecessor records</div>',unsafe_allow_html=True)
        chow_accounts=[a for a in accounts if a.get("chow_current_account")]
        lifetime_value=sum(float(a.get("lifetime_revenue") or 0) for a in chow_accounts)
        ar_value=sum(float(a.get("outstanding_ar") or 0) for a in chow_accounts)
        finance_data=[{"Measure":"Lifetime revenue","Value":lifetime_value},{"Measure":"Outstanding AR","Value":ar_value}]
        finance_pick=alt.selection_point(fields=["Measure"],name="finance_pick",on="click")
        finance_chart=alt.Chart(alt.Data(values=finance_data)).mark_bar(cornerRadiusEnd=7,size=34).encode(
            x=alt.X("Value:Q",title="Protected value",axis=alt.Axis(format="$,.0f")),
            y=alt.Y("Measure:N",title=None,sort=["Lifetime revenue","Outstanding AR"]),
            color=alt.Color("Measure:N",scale=alt.Scale(range=["#7857e8","#17b886"]),legend=None),
            opacity=alt.condition(finance_pick,alt.value(1),alt.value(.72)),tooltip=["Measure:N",alt.Tooltip("Value:Q",format="$,.0f")]
        ).add_params(finance_pick).properties(height=220)
        finance_event=st.altair_chart(finance_chart,use_container_width=True,on_select="rerun",selection_mode="finance_pick",key="finance_chart")
        finance_selected=finance_event.get("selection",{}).get("finance_pick",[]) if finance_event else []
        if finance_selected:
            measure=finance_selected[0].get("Measure","Selected"); value=next((x["Value"] for x in finance_data if x["Measure"]==measure),0)
            st.info(f"{measure}: ${value:,.0f}, summed across {len(chow_accounts)} CRM predecessor record(s) containing a CHOW current-account link.")
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">How the system reached this answer</div>',unsafe_allow_html=True)
    left,mid,right=st.columns([1.1,1,1])
    with left:
        st.markdown('<div class="panel"><div class="pt">Agent run</div><div class="ps">Every stage produces inspectable evidence</div>',unsafe_allow_html=True)
        for n,title,copy in [(1,"Discover",f"Scraped {len(locations)} live communities"),(2,"Normalize","Standardized names, addresses and care types"),(3,"Resolve",f"Compared against {len(accounts)} CRM accounts"),(4,"Guard","Applied AR-aware CHOW and duplicate policies"),(5,"Escalate",f"Routed {len(proposals)} decisions to human review")]: st.markdown(f'<div class="step"><div class="num">{n}</div><div class="copy"><b>{title}</b><span>{copy}</span></div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with mid:
        st.markdown('<div class="panel"><div class="pt">Control posture</div><div class="ps">Current outcomes after policy enforcement</div>',unsafe_allow_html=True)
        clickable_number("CHOW-linked predecessors",chow_links,"Financial lineage links","Count of CRM records with a populated `chow_current_account` field.")
        clickable_number("Resolved duplicate records",duplicates,"Inactive duplicate controls","Count of Inactive CRM records with a populated `duplicate_of_account` field.")
        clickable_number("Ownership investigations",needs_review,"Records requiring investigation","Count of CRM records whose current status is `Needs Review`.")
        clickable_number("AR currently at risk",f"${protected:,.0f}","Open CHOW proposals only","Sum of `outstanding_ar` across currently unresolved CHOW proposals.")
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
        c1,c2,c3=st.columns(3)
        with c1: clickable_number("Protected predecessors",len(chow),"CHOW-linked accounts","Count of predecessor records with a populated `chow_current_account` link.")
        with c2: clickable_number("Lifetime revenue preserved",f"${lifetime_total:,.0f}","Financial history retained","Sum of `lifetime_revenue` across all CHOW-linked predecessor records.")
        with c3: clickable_number("Outstanding AR protected",f"${ar_total:,.0f}","Receivables retained","Sum of `outstanding_ar` across the same CHOW-linked predecessors.")
        st.dataframe([{"Predecessor":a.get("name"),"Predecessor ID":a.get("id"),"Current account ID":a.get("chow_current_account"),"Lifetime revenue":a.get("lifetime_revenue"),"Outstanding AR":a.get("outstanding_ar"),"Control":"Preserved — no re-parent"} for a in chow],use_container_width=True,hide_index=True)
    else: st.info("No CHOW predecessor links are present.")

with audit:
    x1,x2=st.columns(2)
    x1.download_button("Download final CRM snapshot",data=json.dumps({"accounts":accounts},indent=2,default=str),file_name="crm_accounts_final.json",mime="application/json",use_container_width=True)
    x2.download_button("Download decision ledger",data=json.dumps(store.audit_rows(),indent=2,default=str),file_name="ownership_decision_ledger.json",mime="application/json",use_container_width=True)
    st.subheader("Human decision ledger")
    audit_rows=store.audit_rows()
    if audit_rows:
        approved_count=sum(r.get("decision")=="Approved" for r in audit_rows); rejected_count=sum(r.get("decision")=="Rejected" for r in audit_rows); applied_count=sum(bool(r.get("applied_at")) for r in audit_rows)
        a1,a2,a3=st.columns(3)
        with a1: clickable_number("Approved",approved_count,"Human-approved proposals","Count of ledger rows whose `decision` field equals Approved.")
        with a2: clickable_number("Rejected",rejected_count,"Human-rejected proposals","Count of ledger rows whose `decision` field equals Rejected.")
        with a3: clickable_number("Applied",applied_count,"Completed CRM writes","Count of approved ledger rows containing an `applied_at` timestamp.")
        st.dataframe(audit_rows,use_container_width=True,hide_index=True)
    else:
        st.info("No decisions have been recorded in this local workspace yet. The ledger starts when a reviewer approves or rejects a proposal; an empty ledger does not mean the scan failed.")
        e1,e2,e3=st.columns(3)
        if e1.button("↻ Run a new scan",type="primary",use_container_width=True,key="audit_rescan"):
            if run_ownership_scan():
                st.success("Scan refreshed. Open Review Queue to inspect the latest decisions.")
                st.rerun()
        if e2.button("→ Review decisions",use_container_width=True,key="audit_review_help"):
            st.session_state.audit_review_hint=True
        e3.download_button("↓ Download current snapshot",data=json.dumps({"accounts":accounts},indent=2,default=str),file_name="crm_accounts_current.json",mime="application/json",use_container_width=True)
        if st.session_state.get("audit_review_hint"):
            if proposals: st.warning(f"Open the **Review Queue ({len(proposals)})** tab above. Start with Critical items, inspect the evidence, then click Approve or Reject.")
            else: st.success("There are currently zero decisions to review. Run a new scan after the CRM or website data changes.")

st.divider(); pending=store.pending_approvals(); st.subheader("Controlled write-back")
clickable_number("Approved proposals waiting",len(pending),"Credentials exist only in this browser session","Count of Approved ledger entries that do not yet have an `applied_at` timestamp. The Apply button also requires a live credential and the authorization checkbox.")
confirm=st.checkbox("I reviewed the evidence and authorize these approved CRM changes")
if st.button("Apply approved changes",disabled=not(confirm and token and pending),type="primary"):
    client=CRMClient(API,token); progress=st.progress(0)
    for i,p in enumerate(pending,1): result=apply_proposal(client,p); store.mark_applied(p["fingerprint"],result); progress.progress(i/len(pending))
    st.success("Approved changes were applied and recorded in the audit ledger.")

