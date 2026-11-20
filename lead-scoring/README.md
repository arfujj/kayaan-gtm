# Lead scoring tool for Kayaan Shield

Scores freight brokerages on **fit** (are they the right kind of broker?) and **intent** (is now a good time?), out of 100. Every point comes with a plain-English reason, so you can see exactly why an account was picked.

Built by Arfaan Jeddy as part of a GTM plan for Kayaan. Not affiliated with Kayaan.

## What it does

1. **Finds brokers.** Pulls active broker authorities from FMCSA's public dataset on data.transportation.gov (25,081 active as of Nov 20, 2026). Public, keyless, no scraping.
2. **Scores each one** on size, authority age, TMS, freight type, high-theft lanes, hiring, theft or impersonation news, insurance renewal timing and engagement.
3. **Rules out** brokers that are inactive, too small (under 5 staff) or too large (over 500).
4. **Names the buyer** (owner, COO or VP Ops) and suggests the best opening angle.

## Run it

```bash
python3 lead_scoring.py            # score the example accounts (fictional, no network)
python3 lead_scoring.py --live 25  # pull 25 real active brokers from FMCSA's public data
```

Python 3.10+, standard library only.

## Example output (fictional accounts)

```
 75  Gulf Bend Freight (MOCK)  (fit 50, intent 25)
     buyer: COO / VP Operations
     angle: You were just hit or impersonated. Show what a sealed per-load trail would have flagged.
        +15 intent: public theft or impersonation mention in 90 days
        +10 intent: insurance renewal in 2 mo (agent partner)
        ...
```

The example accounts in `mock_scored_accounts.json` are invented for illustration. Hiring, theft and renewal signals come from licensed or partner sources in production; this version takes them as inputs.
