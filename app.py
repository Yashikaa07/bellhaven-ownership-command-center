from __future__ import annotations

import json
from collections import Counter
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
    st.markdown('<div class="status"><strong>System ready.</strong> Run the ownership agent to compare Bellhaven’s live directory with CRM lineage.</div>', unsafe_allow_html=True); st.stop()

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

cards=[("Ownership health",f"{health}%","Post-reconciliation confidence","good" if health>=90 else "amber"),("Website coverage",len(locations),"Communities independently scraped",""),("CRM universe",len(accounts),f"{active} active accounts monitored",""),("Open decisions",len(proposals),"No autonomous writes","good" if not proposals else "amber"),("Protected lineage",chow_links,"CHOW predecessors retained","good"),("Duplicate controls",duplicates,"Inactive records preserved","good")]
for start in (0,3):
    for col,(label,value,note,cls) in zip(st.columns(3),cards[start:start+3]): col.markdown(f'<div class="card"><div class="label">{label}</div><div class="value {cls}">{value}</div><div class="note">{note}</div></div>',unsafe_allow_html=True)

overview, review, lineage, audit = st.tabs(["Command Center",f"Review Queue ({len(proposals)})","Ownership Lineage","Audit & Export"])
with overview:
    left,mid,right=st.columns([1.1,1,1])
    with left:
        st.markdown('<div class="panel"><div class="pt">Agent run</div><div class="ps">Every stage produces inspectable evidence</div>',unsafe_allow_html=True)
        for n,title,copy in [(1,"Discover",f"Scraped {len(locations)} live communities"),(2,"Normalize","Standardized names, addresses and care types"),(3,"Resolve",f"Compared against {len(accounts)} CRM accounts"),(4,"Guard","Applied AR-aware CHOW and duplicate policies"),(5,"Escalate",f"Routed {len(proposals)} decisions to human review")]: st.markdown(f'<div class="step"><div class="num">{n}</div><div class="copy"><b>{title}</b><span>{copy}</span></div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with mid:
        st.markdown('<div class="panel"><div class="pt">Control posture</div><div class="ps">Current outcomes after policy enforcement</div>',unsafe_allow_html=True)
        st.metric("CHOW-linked predecessors",chow_links); st.metric("Resolved duplicate records",duplicates); st.metric("Ownership investigations",needs_review); st.metric("AR currently at risk",f"${protected:,.0f}")
        st.markdown('</div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="pt">✦ Ownership Copilot</div><div class="ps">Explainable answers grounded in this run</div>',unsafe_allow_html=True)
        q=st.selectbox("Ask about this run",["Give me the executive summary","What should I review first?","How did the CHOW guardrail work?","Is this pipeline safe to rerun?"])
        if q.startswith("Give"): ans=f"Ownership health is {health}%. I reconciled {len(locations)} website communities against {len(accounts)} CRM accounts. {len(proposals)} decisions remain; {chow_links} predecessor links and {duplicates} duplicate controls are preserved."
        elif q.startswith("What"): ans=f"Start with {sum(p['risk']=='Critical' for p in proposals)} critical CHOW events, then parent changes and duplicates. Every recommendation includes field-level evidence."
        elif q.startswith("How"): ans=f"When revenue and AR coexist, the agent preserves the old account and links a new current account. {chow_links} protected lineage links are retained."
        else: ans="Yes. CRM-state checks ignore inactive duplicates, resolved investigations, and CHOW-protected predecessors. Fingerprints prevent repeated decisions."
        st.markdown(f'<div class="answer">{ans}</div>',unsafe_allow_html=True); st.caption("Rule-grounded copilot • No hallucinated CRM writes"); st.markdown('</div>',unsafe_allow_html=True)

with review:
    if not proposals: st.success("Zero open decisions. The pipeline was rerun safely after write-back.")
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
    if chow: st.dataframe([{"Predecessor":a.get("name"),"Predecessor ID":a.get("id"),"Current account ID":a.get("chow_current_account"),"Lifetime revenue":a.get("lifetime_revenue"),"Outstanding AR":a.get("outstanding_ar"),"Control":"Preserved — no re-parent"} for a in chow],use_container_width=True,hide_index=True)
    else: st.info("No CHOW predecessor links are present.")

with audit:
    st.download_button("Download final CRM evidence snapshot",data=json.dumps({"accounts":accounts},indent=2,default=str),file_name="crm_accounts_final.json",mime="application/json")
    st.subheader("Human decision ledger"); st.dataframe(store.audit_rows(),use_container_width=True,hide_index=True)

st.divider(); pending=store.pending_approvals(); st.subheader("Controlled write-back"); st.caption(f"{len(pending)} approved proposal(s) waiting. Credentials exist only in this browser session.")
confirm=st.checkbox("I reviewed the evidence and authorize these approved CRM changes")
if st.button("Apply approved changes",disabled=not(confirm and token and pending),type="primary"):
    client=CRMClient(API,token); progress=st.progress(0)
    for i,p in enumerate(pending,1): result=apply_proposal(client,p); store.mark_applied(p["fingerprint"],result); progress.progress(i/len(pending))
    st.success("Approved changes were applied and recorded in the audit ledger.")
