from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher


def _norm(value) -> str:
    value = str(value or "").lower().replace("&", " and ")
    directions = {"northwest":"nw", "northeast":"ne", "southwest":"sw", "southeast":"se",
                  "north":"n", "south":"s", "east":"e", "west":"w"}
    for word, short in directions.items():
        value = re.sub(rf"\b{word}\b", short, value)
    value = re.sub(r"\b(street|st|road|rd|avenue|ave|lane|ln|drive|dr|boulevard|blvd|pike|pk)\b", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def _money(value) -> float:
    try:
        return float(str(value or 0).replace("$", "").replace(",", ""))
    except ValueError:
        return 0.0


def score(location: dict, account: dict) -> tuple[float, dict]:
    name = round(100 * SequenceMatcher(None, _norm(location["name"]), _norm(account.get("name"))).ratio())
    address = 100 if _norm(location["address"]) == _norm(account.get("billing_street") or account.get("address") or account.get("street")) else 0
    city = 100 if _norm(location["city"]) == _norm(account.get("billing_city") or account.get("city")) else 0
    state = 100 if _norm(location["state"]) == _norm(account.get("billing_state") or account.get("state")) else 0
    zipcode = 100 if _norm(location["zip"]) == _norm(account.get("billing_zip") or account.get("zip") or account.get("postal_code")) else 0
    components = {"name": name, "address": address, "city": city, "state": state, "zip": zipcode}
    total = address * .45 + zipcode * .20 + city * .10 + state * .10 + name * .15
    return round(total, 1), components


def _fp(payload: dict) -> str:
    stable = {k: v for k, v in payload.items() if k not in {"fingerprint", "created_at"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str).encode()).hexdigest()[:20]


def _proposal(kind, risk, location, account, evidence, actions, explanation):
    p = {"kind": kind, "risk": risk, "location": location, "account": account,
         "evidence": evidence, "actions": actions, "explanation": explanation}
    p["fingerprint"] = _fp(p)
    return p


def find_parent(accounts: list[dict]) -> dict | None:
    candidates = [a for a in accounts if "bellhaven" in _norm(a.get("name")) and not a.get("parent_id")]
    return max(candidates, key=lambda a: len(str(a.get("name", ""))), default=None)


def _care_type(offerings: list[str]) -> str:
    joined = " ".join(offerings).lower()
    if "rehabilitation" in joined or "nursing" in joined: return "Skilled Nursing"
    if "memory" in joined: return "Memory Care"
    if "assisted" in joined: return "Assisted Living"
    return offerings[0] if offerings else ""


def build_proposals(locations: list[dict], accounts: list[dict], parent_id: str) -> list[dict]:
    parent = next((a for a in accounts if str(a.get("id")) == str(parent_id)), None)
    # Inactive duplicate records remain in the CRM for audit/history purposes,
    # but must never compete with live accounts on a later run.
    facility_accounts = [a for a in accounts
                         if str(a.get("id")) != str(parent_id)
                         and str(a.get("status") or "").lower() != "inactive"
                         and not a.get("duplicate_of_account")
                         # A predecessor with a CHOW link is a protected
                         # financial-history record, never a duplicate.
                         and not a.get("chow_current_account")]
    proposals, matched_ids = [], set()
    for loc in locations:
        ranked = sorted(((score(loc, a)[0], score(loc, a)[1], a) for a in facility_accounts),
                        reverse=True, key=lambda x: (x[0], str(x[2].get("parent_id")) == str(parent_id),
                                                     _money(x[2].get("lifetime_revenue"))))
        strong = [x for x in ranked if x[0] >= 80 or (x[1]["address"] == 100 and x[1]["zip"] == 100)
                  or (x[1]["name"] >= 90 and x[1]["city"] == 100 and x[1]["zip"] == 100)]
        if not strong:
            payload = {"name": loc["name"], "billing_street": loc["address"], "billing_city": loc["city"],
                       "billing_state": loc["state"], "billing_zip": loc["zip"], "care_type": _care_type(loc["care_offerings"]), "parent_id": parent_id,
                       "status": "Active", "note": f"Created from {loc['source_url']}"}
            proposals.append(_proposal("Missing CRM account", "Medium", loc, None,
                {"source": loc["source_url"], "best_score": ranked[0][0] if ranked else 0},
                [{"method": "POST", "payload": payload}], "Website location has no sufficiently strong CRM match."))
            continue
        best_score, components, acc = strong[0]
        matched_ids.add(str(acc.get("id")))
        duplicates = [x[2] for x in strong[1:] if x[1]["address"] == 100 and x[1]["zip"] == 100]
        for loser in duplicates:
            matched_ids.add(str(loser.get("id")))
            proposals.append(_proposal("Duplicate account", "High", loc, loser,
                {"survivor_id": acc.get("id"), "exact_address": True},
                [{"method": "PATCH", "account_id": loser.get("id"), "payload": {
                    "duplicate_of_account": acc.get("id"), "status": "Inactive",
                    "note": f"Duplicate of {acc.get('id')}; confirmed against {loc['source_url']}"}}],
                "Multiple CRM accounts share the website location's exact address."))
        changes = {}
        if _norm(acc.get("name")) != _norm(loc["name"]): changes["name"] = loc["name"]
        if _norm(acc.get("billing_street") or acc.get("address") or acc.get("street")) != _norm(loc["address"]): changes["billing_street"] = loc["address"]
        for source, target in (("city","billing_city"),("state","billing_state"),("zip","billing_zip")):
            if _norm(acc.get(target)) != _norm(loc[source]): changes[target] = loc[source]
        expected_care = _care_type(loc["care_offerings"])
        if expected_care and _norm(acc.get("care_type")) != _norm(expected_care): changes["care_type"] = expected_care
        wrong_parent = str(acc.get("parent_id") or "") != str(parent_id)
        if wrong_parent and _money(acc.get("lifetime_revenue")) > 0 and _money(acc.get("outstanding_ar")) > 0:
            new_payload = {"name": loc["name"], "billing_street": loc["address"], "billing_city": loc["city"],
                           "billing_state": loc["state"], "billing_zip": loc["zip"], "care_type": expected_care, "parent_id": parent_id,
                           "status": "Active", "note": f"Current ownership record; predecessor {acc.get('id')}"}
            proposals.append(_proposal("CHOW: preserve billing history", "Critical", loc, acc,
                {"match_score": best_score, "components": components, "lifetime_revenue": acc.get("lifetime_revenue"),
                 "outstanding_ar": acc.get("outstanding_ar"), "target_parent": parent and parent.get("name")},
                [{"method": "POST_THEN_CHOW", "old_account_id": acc.get("id"), "payload": new_payload}],
                "Wrong parent plus revenue history and outstanding AR triggers the mandatory CHOW safeguard."))
        else:
            if wrong_parent: changes["parent_id"] = parent_id
            if changes:
                changes["note"] = f"Reconciled from {loc['source_url']}"
                proposals.append(_proposal("Correct existing account", "High" if wrong_parent else "Low", loc, acc,
                    {"match_score": best_score, "components": components, "target_parent": parent and parent.get("name")},
                    [{"method": "PATCH", "account_id": acc.get("id"), "payload": changes}],
                    "Strong location match; CRM fields differ from current website evidence."))
    for acc in accounts:
        if str(acc.get("parent_id") or "") == str(parent_id) and str(acc.get("id")) not in matched_ids:
            # Previously resolved duplicates are intentionally preserved, not
            # reconsidered as facilities or former-ownership candidates.
            if str(acc.get("status") or "").lower() == "inactive" or acc.get("duplicate_of_account"):
                continue
            same_address = [other for other in facility_accounts
                            if str(other.get("id")) != str(acc.get("id"))
                            and _norm(other.get("billing_street")) == _norm(acc.get("billing_street"))
                            and _norm(other.get("billing_zip")) == _norm(acc.get("billing_zip"))]
            if same_address and _money(acc.get("lifetime_revenue")) > 0 and _money(acc.get("outstanding_ar")) > 0:
                current = max(same_address, key=lambda a: (a.get("status") == "Active", _money(a.get("lifetime_revenue"))))
                if str(acc.get("chow_current_account") or "") == str(current.get("id") or ""):
                    continue
                proposals.append(_proposal("CHOW: link preserved predecessor", "Critical", None, acc,
                    {"website_match": False, "same_address_current_account": current.get("id"),
                     "current_parent": current.get("parent_name"), "lifetime_revenue": acc.get("lifetime_revenue"),
                     "outstanding_ar": acc.get("outstanding_ar")},
                    [{"method": "PATCH", "account_id": acc.get("id"), "payload": {"chow_current_account": current.get("id")}}],
                    "Unlisted Bellhaven record shares its exact address with an active account under another parent. Revenue and AR require preserving the predecessor and linking it to the current account."))
                continue
            review_note = "Not found on current Bellhaven website; ownership requires investigation."
            if str(acc.get("status") or "").lower() != "needs review" or str(acc.get("note") or "") != review_note:
                proposals.append(_proposal("Former or unlisted Bellhaven account", "High", None, acc,
                    {"website_match": False}, [{"method": "PATCH", "account_id": acc.get("id"), "payload": {
                        "status": "Needs Review", "note": review_note}}],
                    "CRM child is absent from the website. Absence is not sufficient evidence for automatic deactivation."))
    return proposals


def apply_proposal(client, proposal: dict) -> dict:
    results = []
    for action in proposal["actions"]:
        if action["method"] == "POST": results.append(client.create_account(action["payload"]))
        elif action["method"] == "PATCH": results.append(client.update_account(str(action["account_id"]), action["payload"]))
        elif action["method"] == "POST_THEN_CHOW":
            created = client.create_account(action["payload"])
            new_id = created.get("id") or created.get("account", {}).get("id")
            if not new_id: raise RuntimeError("Create response did not contain a new account id; CHOW link was not attempted.")
            results.append(created)
            results.append(client.update_account(str(action["old_account_id"]), {"chow_current_account": new_id}))
        else: raise ValueError(f"Unknown action {action['method']}")
    return {"results": results}
