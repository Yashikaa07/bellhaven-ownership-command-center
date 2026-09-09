# OwnershipOS · Bellhaven Ownership Radar

OwnershipOS turns facility/parent reconciliation into an explainable change-control workflow. It scrapes every Bellhaven location, identifies ownership events, applies the billing-safe CHOW rule, previews CRM mutations, and requires human approval before any write.

## Why this is more than fuzzy matching

- Address-led, explainable evidence instead of a black-box score
- Ownership event classification: rebrand, missing account, wrong parent, duplicate, former/unlisted, CHOW
- Financial safeguard: an account with lifetime revenue **and** outstanding AR is preserved; a new current account is created and the predecessor is linked through `chow_current_account`
- Blast-radius preview through explicit proposed API actions
- Durable decision ledger: unchanged approved/rejected proposals do not reappear
- Daily automation is read-only; humans remain responsible for mutations
- Executive command center with ownership-health, coverage, lineage, duplicate, and investigation KPIs
- Rule-grounded Ownership Copilot that explains the run without placing an LLM in the write path

## Run locally

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Paste the **complete value** expected in the API's `Authorization` header into the password field. It stays in the local Streamlit session and is never written to disk.

1. Click **Run ownership agent**.
2. Review the evidence and proposed API actions.
3. Approve or reject each proposal.
4. Review the number and types of pending actions.
5. Check the confirmation box and apply approved changes.
6. Rescan and inspect the CRM browser to verify the end state.

## Matching approach

Identity is primarily location-based because acquisitions often change names. Exact normalized street address and ZIP are strongest; city/state and name similarity provide supporting evidence. A record is accepted as a strong candidate at 80 points or when both normalized street and ZIP match exactly. Ambiguous absence is marked `Needs Review`, never automatically deactivated.

The UI exposes the component scores and source URL for every decision. No LLM participates in write logic.

## Safe reruns

Each proposal receives a fingerprint derived from its source evidence, target record, and intended actions. Approvals and rejections are stored in SQLite. CRM-state guards independently exclude resolved inactive duplicates, completed `Needs Review` investigations, and CHOW-linked predecessors. This second line of defense makes reruns safe even if the local ledger is unavailable.

## Product experience

The Streamlit interface is organized as an operating system rather than a raw review list:

- **Command Center:** executive health score, control posture, and a five-stage agent trace
- **Review Queue:** risk-prioritized evidence, rationale, API preview, and human approval
- **Ownership Lineage:** explicit predecessor-to-current CHOW mapping with protected financial fields
- **Audit & Export:** human decision ledger and downloadable final evidence snapshot
- **Ownership Copilot:** deterministic, evidence-grounded explanations of priority, CHOW policy, and rerun safety

## Daily schedule

`.github/workflows/daily.yml` runs the read-only scan daily at 11:17 UTC and uploads its report. Production credentials belong in the `CRM_AUTHORIZATION` repository secret. Scheduled automation deliberately does not approve or apply changes.

## AI usage

AI was used as an implementation accelerator and reviewer. Business rules, match weights, API actions, and final CRM decisions were independently inspected and tested. Deterministic logic—not an LLM—controls financially sensitive recommendations.

## What I would build next

- Historical snapshots to detect ownership changes over time rather than only current-state mismatches
- Secondary evidence sources and confidence calibration from reviewer feedback
- Transaction/rollback support for multi-step CHOW actions
- Slack review notifications and operational monitoring
- Role-based approvals for financially sensitive changes

## Walkthrough demo path

Show one clean match, one rebrand, one duplicate, one absent website record, and one CHOW case. Explain the evidence, preview the mutation, approve it, rescan, and demonstrate that the decided proposal does not return.
