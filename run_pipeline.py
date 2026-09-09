"""Read-only scheduled scan. It creates a JSON report; humans decide in the app."""
import json, os
from datetime import datetime, timezone
from ownershipos.crm import CRMClient
from ownershipos.matcher import build_proposals, find_parent
from ownershipos.scraper import scrape_locations
from ownershipos.state import DecisionStore

BASE="https://analyst-assessment-production.up.railway.app"
token=os.environ["CRM_AUTHORIZATION"]
locations,warnings=scrape_locations(BASE)
accounts=CRMClient(BASE+"/api/v1",token).list_accounts()
parent=find_parent(accounts)
if not parent: raise SystemExit("Bellhaven parent not found; no changes made")
store=DecisionStore()
proposals=[p for p in build_proposals(locations,accounts,str(parent["id"])) if not store.decided(p["fingerprint"])]
report={"generated_at":datetime.now(timezone.utc).isoformat(),"warnings":warnings,"proposals":proposals}
with open("latest_scan.json","w",encoding="utf-8") as f: json.dump(report,f,indent=2)
print(f"Read-only scan complete: {len(proposals)} new proposals. No CRM writes performed.")
