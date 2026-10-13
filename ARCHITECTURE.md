# LAD Architecture

![LAD architecture diagram](docs/architecture.png)

## The layer model

```
┌─────────────────────────────────────────────────────────────┐
│  OWNERS — declare interests, objectives, permissions        │
├─────────────────────────────────────────────────────────────┤
│  AGENTS & APPS — reason, plan, propose actions              │
├─────────────────────────────────────────────────────────────┤
│  LAD — the trust layer                                      │
│    · Ledger: signed, hash-chained record of every action    │
│    · Approved: owner-set policy gates, checked pre-action   │
│    · Deterministic: declared feeds, budgets, boundaries     │
├─────────────────────────────────────────────────────────────┤
│  PROTOCOLS — MCP (tools) · A2A (agents) · UCP (commerce)    │
├─────────────────────────────────────────────────────────────┤
│  THE WORLD — tools, merchants, other agents, services       │
└─────────────────────────────────────────────────────────────┘
```

Agents sit *above* the layer: they reason probabilistically and propose
actions. The world sits *below* it: tools, merchants, and other agents
reached through the ecosystem's protocols. LAD sits between the two and
answers three questions about every action, deterministically:

1. **May this happen?** — the approval gate checks the owner's policy for
   this agent, this action type, this cost.
2. **Did it happen exactly as recorded?** — the ledger entry is written
   with the action, chained to the previous entry's hash, and signed.
3. **Can someone else check?** — the chain verifies independently of the
   system that produced it.

## The three components

### Ledger

An append-only sequence of entries. Each entry carries the agent, the
action, a summary of inputs and output, the cost, the authorization behind
it, and the hash of the previous entry. The entry's own hash is
`SHA256(prev_hash + canonical(entry fields))`, and the entry is signed with
`HMAC-SHA256(account_key, entry.hash)`. Editing or deleting any entry
breaks every hash after it.

### Approved

A policy table the owner controls: per agent, per action type, one of
*always ask*, *ask above a limit*, *auto within policy*, or *never*.
"Always ask" holds the action until the owner approves or denies it in one
tap. Approval and denial are themselves ledger entries.

### Deterministic boundaries

The non-model constraints: the owner's declared feed (sources and topics
the network may surface — no engagement algorithm), declared objectives
(what agents work on between instructions), budgets and rate limits, and
the recording rules themselves. Same declarations, same behavior, every
run.

## Where the protocols fit

LAD is complementary to the agent protocol stack, never a replacement:

- **MCP** carries model↔tool traffic. Under LAD, each tool call passes the
  gate and lands in the ledger.
- **A2A** carries agent↔agent traffic. Under LAD, a foreign agent's
  request is an action like any other: gated, recorded, attributable.
- **UCP** carries agent↔merchant commerce. Under LAD, a purchase is a
  consequential action: policy-checked against the owner's limits before
  it executes, receipt in the ledger after.

## The reference implementation

[Double-Oh](https://double-oh.com) implements the layer today:

- Agents are created from one sentence and run objectives and scheduled
  work on their own.
- Every agent action is written to the owner's audit ledger, with the
  model, provider, and routing reason for each step.
- Owners set approval policies per agent; consequential actions wait for
  a one-tap decision.
- The feed is declared by the owner — news desks they chose, no
  algorithmic ranking.
- The Shop runs agent-to-agent and agent-to-business commerce at 0%
  platform transaction fees, every sale a ledger entry.

See [reference/](reference/) for a minimal code-level illustration of the
ledger and the gate.
