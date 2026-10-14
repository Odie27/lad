# LAD — Conceptual Examples

These examples illustrate how the LAD pattern (see [PRINCIPLES.md](../PRINCIPLES.md)
and [ARCHITECTURE.md](../ARCHITECTURE.md)) constrains an agent's actions in
practice: an owner-set policy, a gate checked **before** an action executes,
and a hash-chained ledger entry written for every outcome.

**What these are:** small, self-contained teaching implementations of the
pattern's mechanics — deny-dominance approvals, scoped delegation, replay
protection, tamper-evident chaining.

**What these are not:** they are *not* the Double-Oh API. Double-Oh's public
API and webhooks serve the platform's own agents and connected agents; there
is no published `lad_auth_token` MCP field or intent-envelope endpoint, and
LAD's formal specification arrives in Phase 4, with adoption. Where an
example invents a wire format (a token, a policy file), it is showing the
*shape* of the mechanism, not documenting a live interface.

## Files

- `lad_policy.example.json` — an illustrative owner policy: declared input
  feeds, approval constraints (caps, co-sign threshold, allowed currencies,
  restricted vendors), and compliance switches. In the reference
  implementation these policies are set per agent in the product; the file
  shows the same rules in one readable place.
- `lad_mcp_flow.py` — an agent routes a tool call through the gate before
  dispatching it to a mock MCP tool server. The server verifies the ledger
  receipt token against the issuing engine (presence alone is not
  verification), enforces the policy with deny-dominance, and *holds* —
  rather than rejects — actions that need a human co-sign.
- `lad_a2a_delegation.py` — agent-to-agent delegation: a parent issues a
  scoped, signed, expiring token to a child; the child's actions are checked
  against the delegated bounds, sequenced with nonces (replay attempts are
  dropped), and chained into a tamper-evident ledger.

## Corrections applied to the original drafts

1. Delegation tokens now encode claims as base64url before signing. The
   original draft joined raw JSON and a signature with `.` and split on `.`
   to parse — any decimal inside the claims (e.g. `150.0`) broke the parse.
2. The mock MCP server now verifies the receipt token cryptographically
   against the issuing engine instead of accepting any non-empty string.
3. Actions above the co-sign threshold are returned as `HELD` (awaiting an
   owner decision, itself a ledger entry) instead of being rejected — an
   approval gate holds consequential actions; it only denies what policy
   says may never happen.
