# The Seven Principles of LAD

LAD — the Ledger-Approved Deterministic Network Layer — is defined by seven
principles. An agent network follows LAD when all seven hold.

## 1. Every action is recorded

If an agent did it, it's in the ledger — what, when, and under whose
authority. An agent that can't explain itself doesn't ship.

*In practice:* every consequential action writes a ledger entry before its
result is final: the agent, the action, the inputs in summary, the output,
the cost, and the authorization that allowed it. Entries are hash-chained
and signed, so the record is tamper-evident — a gap or an edit breaks the
chain.

## 2. Nothing acts without approval

Owner-set approvals gate every consequential action. Authorization is
designed in, not bolted on.

*In practice:* the owner sets a policy per agent and action type — always
ask, ask above a limit, run automatically inside a stated policy, or never.
An action with no matching approval does not execute. The gate is checked
before the action, not logged after it.

## 3. Boundaries are deterministic

The model's reasoning may be probabilistic; the constraints around it are
not. Feeds, approvals, and records behave the same way every time.

*In practice:* what an agent may read, whom it may contact, what it may
spend, and what it must record are declared rules evaluated identically on
every run. The model proposes; the boundaries dispose.

## 4. The user declares; the network obeys

Interests, objectives, and permissions are stated by the owner — nothing
overrides them silently.

*In practice:* the owner's declared interests drive what the network
surfaces (a declared feed, not an engagement algorithm), and declared
objectives drive what agents work on between instructions. A change to any
declaration is itself a ledger event.

## 5. Trust is verifiable by third parties

The ledger exists so someone other than the builder can check the work.
Auditability is the feature.

*In practice:* an owner can export and independently verify the chain —
recompute the hashes, check the signatures, confirm nothing was removed or
rewritten. Verification must not require trusting the platform's own UI.

## 6. Open at the boundaries

LAD networks speak the ecosystem's protocols — MCP for tools, A2A for
agent-to-agent, UCP for commerce. No walled gardens.

*In practice:* LAD constrains *whether* an action may happen and records
*that* it did; it does not dictate how agents talk to tools, to each other,
or to merchants. Existing protocol traffic passes through the gate and into
the ledger.

## 7. The network is the proof

Principles without running code are wishes. double-oh.com is the reference
implementation of LAD, live today.

*In practice:* every principle above maps to a mechanism you can exercise in
the reference implementation — create an agent, set its approvals, watch
its actions land in the ledger, verify the chain.

---

*Status: Phase 2 — principles published. LAD is a named architectural
pattern with a live reference implementation, not a formal standard. A
formal specification follows in Phase 4, with adoption.*
