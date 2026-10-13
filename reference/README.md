# Reference code

Minimal, illustrative implementations of LAD's two core mechanics.

| File | What it shows |
|---|---|
| `ledger.ts` | The hash-chained, HMAC-signed action ledger (`SHA256(prev_hash + canonical(fields))`, `HMAC-SHA256(account_key, hash)`), third-party chain verification, the owner-policy approval gate (`always_ask` / `ask_above_limit` / `auto_within_policy` / `never`), and the full action flow: planned entry → gate → execution → outcome entry. |

Run the demo (TypeScript, Node ≥ 20):

```bash
npx tsx ledger.ts
```

The demo runs three actions through the gate — one auto-approved by
policy, one held for the owner because it exceeds its limit, and one with
no policy on record, which the gate holds for a human decision and the
owner denies — then verifies the chain.

This code is a teaching artifact for the pattern. It is **not** Double-Oh's
production implementation; the production system lives in the product at
[double-oh.com](https://double-oh.com). Ports to other languages are
welcome — see [CONTRIBUTING.md](../CONTRIBUTING.md).
