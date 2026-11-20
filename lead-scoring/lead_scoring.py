"""
Lead scoring tool: explainable fit + intent scoring for Kayaan Shield prospects.

- discover(): pulls ACTIVE broker authorities from FMCSA's public Socrata dataset
  (data.transportation.gov, "Carrier - All With History", id 6eyk-hxee). Public,
  keyless, us-pd license. No scraping, no private data.
- score(): 100-point explainable score. Every point carries a reason string so a
  founder can see exactly why an account was picked.
- buyer(): likely economic buyer by company size.
- The demo at the bottom runs on CLEARLY LABELED MOCK RECORDS (fictional companies).

Run:  python3 lead_scoring.py            (mock demo, no network)
      python3 lead_scoring.py --live 25  (pull 25 real active broker rows from FMCSA)
"""
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date

FMCSA_AUTH = "https://data.transportation.gov/resource/6eyk-hxee.json"
SUPPORTED_TMS = {"mcleod", "powerbroker", "turvo", "revenova", "alvys", "ascend", "aljex",
                 "mercurygate", "rose rocket", "tailwind"}
HIGH_THEFT_STATES = {"CA", "TX", "IL", "GA", "FL", "NJ", "TN", "PA"}  # assumption: tune with CargoNet data
TARGET_ROLES = ("carrier sales", "track and trace", "track & trace", "carrier compliance",
                "carrier relations", "check call")


def discover(limit=25, state=None):
    """Active broker authorities from FMCSA public data (Socrata SoQL)."""
    where = "broker_stat='A'" + (f" AND bus_state_code='{state}'" if state else "")
    q = urllib.parse.urlencode({"$where": where, "$limit": limit,
                                "$select": "docket_number,dot_number,legal_name,dba_name,"
                                           "bus_city,bus_state_code,common_stat,bond_file"})
    with urllib.request.urlopen(f"{FMCSA_AUTH}?{q}", timeout=60) as r:
        return json.load(r)


@dataclass
class Account:
    name: str
    mc: str
    state: str
    authority_years: float
    employees: int | None
    tms_mentions: list = field(default_factory=list)
    modes: list = field(default_factory=list)          # e.g. ["dry van", "reefer"]
    lanes_into: list = field(default_factory=list)     # destination states
    job_posts_30d: list = field(default_factory=list)  # titles from licensed job data
    theft_mention_90d: bool = False                    # public post/news naming them as victim or impersonated
    renewal_month: int | None = None                   # only via insurance-agent partner, with consent
    site_visits_14d: int = 0                           # first-party analytics on the pilot/readout page
    status: str = "A"
    mock: bool = True


def score(a: Account, today=date(2026, 11, 20)):
    reasons, fit, intent = [], 0, 0
    # Hard disqualifiers
    if a.status != "A":
        return 0, 0, ["DQ: authority not active"]
    if a.employees is not None and (a.employees < 5 or a.employees > 500):
        return 0, 0, [f"DQ: {a.employees} staff is outside 5 to 500"]
    # FIT (max 50)
    if 2 <= a.authority_years <= 15:
        fit += 10; reasons.append(f"+10 fit: authority {a.authority_years:g} yrs (established, not legacy)")
    elif 1 <= a.authority_years < 2:
        fit += 5; reasons.append(f"+5 fit: authority {a.authority_years:g} yrs (young)")
    if a.employees and 10 <= a.employees <= 75:
        fit += 15; reasons.append(f"+15 fit: {a.employees} staff, core ICP band")
    elif a.employees and 76 <= a.employees <= 200:
        fit += 8; reasons.append(f"+8 fit: {a.employees} staff, upper band")
    tms = [t for t in a.tms_mentions if t.lower() in SUPPORTED_TMS]
    if tms:
        fit += 10; reasons.append(f"+10 fit: supported TMS detected ({', '.join(tms)})")
    elif not a.tms_mentions:
        fit += 4; reasons.append("+4 fit: TMS unknown (confirm on call)")
    if any(m in ("dry van", "reefer", "power only") for m in a.modes):
        fit += 10; reasons.append("+10 fit: FTL van/reefer/power only, high theft exposure")
    if a.state in HIGH_THEFT_STATES or set(a.lanes_into) & HIGH_THEFT_STATES:
        fit += 5; reasons.append("+5 fit: operates in or into high-theft states")
    # INTENT (max 50)
    hits = [j for j in a.job_posts_30d if any(r in j.lower() for r in TARGET_ROLES)]
    if hits:
        intent += 15; reasons.append(f"+15 intent: hiring '{hits[0]}' (check-call load growing)")
    if a.theft_mention_90d:
        intent += 15; reasons.append("+15 intent: public theft or impersonation mention in 90 days")
    if a.renewal_month:
        months_out = (a.renewal_month - today.month) % 12
        if months_out <= 3:
            intent += 10; reasons.append(f"+10 intent: insurance renewal in {months_out} mo (agent partner)")
    if a.site_visits_14d >= 2:
        intent += 10; reasons.append(f"+10 intent: {a.site_visits_14d} visits to pilot/readout page")
    elif a.site_visits_14d == 1:
        intent += 5; reasons.append("+5 intent: 1 visit to pilot/readout page")
    return min(fit, 50), min(intent, 50), reasons


def buyer(a: Account):
    n = a.employees or 0
    if n < 25:
        return "Owner / President", "Ops lead or senior carrier rep"
    if n <= 75:
        return "COO / VP Operations", "Carrier compliance or carrier relations lead"
    return "VP Carrier Procurement + Head of Risk", "Director of Carrier Relations"


def angle(a: Account, reasons):
    text = " ".join(reasons)
    if "impersonation mention" in text:
        return "You were just hit or impersonated. Show what a sealed per-load trail would have flagged."
    if "renewal in" in text:
        return "Renewal in under 90 days. Walk in with a documented carrier-selection process."
    if "intent: hiring" in text:
        return "Before the next check-call hire, automate the calls and keep the audit file."
    return "Post-Montgomery readout on 10 recent carriers."


MOCK = [  # ALL FICTIONAL. Do not treat as real companies.
    Account("Prairie Line Logistics (MOCK)", "MC-000001", "IL", 6, 22, ["McLeod PowerBroker"],
            ["dry van"], ["CA", "TX", "GA"], ["Carrier Sales Rep, track and trace experience"],
            site_visits_14d=1),
    Account("Gulf Bend Freight (MOCK)", "MC-000002", "TX", 9, 48, ["Turvo"], ["reefer"], ["FL"],
            [], theft_mention_90d=True, renewal_month=1),
    Account("Copper Mesa Transport Brokers (MOCK)", "MC-000003", "AZ", 3, 14, [], ["flatbed"], ["NM"],
            ["Track and Trace Coordinator"]),
    Account("Harborview 3PL Group (MOCK)", "MC-000004", "NJ", 18, 140, ["MercuryGate"],
            ["dry van", "LTL"], ["PA"], [], renewal_month=2),
    Account("Two Rivers Brokerage (MOCK)", "MC-000005", "OH", 0.6, 3, [], ["dry van"], [], []),
]

if __name__ == "__main__":
    if "--live" in sys.argv:
        n = int(sys.argv[sys.argv.index("--live") + 1])
        rows = discover(limit=n)
        print(f"Pulled {len(rows)} active broker authorities from FMCSA (public data):")
        for r in rows[:n]:
            print(" ", r.get("docket_number"), "|", r.get("legal_name"), "|", r.get("bus_city"), r.get("bus_state_code"))
        sys.exit()
    out = []
    for a in MOCK:
        f, i, why = score(a)
        b, champ = buyer(a)
        out.append({"account": a.name, "mc": a.mc, "score": f + i, "fit": f, "intent": i,
                    "buyer": b, "champion": champ, "angle": angle(a, why), "reasons": why})
    out.sort(key=lambda r: -r["score"])
    for r in out:
        print(f"\n{r['score']:>3}  {r['account']}  (fit {r['fit']}, intent {r['intent']})")
        print(f"     buyer: {r['buyer']}  |  champion: {r['champion']}")
        print(f"     angle: {r['angle']}")
        for x in r["reasons"]:
            print("       ", x)
    json.dump(out, open("mock_scored_accounts.json", "w"), indent=2)
