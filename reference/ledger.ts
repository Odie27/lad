/**
 * LAD reference implementation — the ledger and the approval gate.
 *
 * ILLUSTRATIVE CODE. This is a minimal, readable implementation of the two
 * core LAD mechanics, published so builders can see exactly what the
 * pattern requires:
 *
 *   1. A hash-chained, HMAC-signed, append-only action ledger.
 *   2. An owner-set approval gate checked BEFORE an action executes.
 *
 * It is not Double-Oh's production code. The production implementation
 * lives in the product at double-oh.com.
 *
 * Run the demo:  node ledger.ts   (Node ≥ 22.18)  or  npx tsx ledger.ts
 */

import { createHash, createHmac, randomUUID } from "node:crypto";

// ---------------------------------------------------------------- types

export type PolicyMode =
  | "always_ask"        // hold every action for the owner's decision
  | "ask_above_limit"   // auto-run at or below `limit`, ask above it
  | "auto_within_policy"// run without asking, inside the stated policy
  | "never";            // this action type is not permitted at all

export interface Policy {
  agentId: string;
  action: string;       // e.g. "message.send", "purchase.create"
  mode: PolicyMode;
  limit?: number;        // cost ceiling for ask_above_limit / auto modes
}

export type EntryStatus =
  | "planned" | "approved" | "denied" | "completed" | "failed" | "blocked";

export interface LedgerEntry {
  id: string;
  ts: string;            // ISO 8601
  agent_id: string;
  owner_id: string;
  action: string;
  summary: string;       // what was attempted, in plain language
  cost: number;          // credits / cents — declared before execution
  authorization: string; // approval id, or the policy that allowed it
  status: EntryStatus;
  prev_hash: string;     // hash of the previous entry ("GENESIS" for #1)
  hash: string;          // SHA256(prev_hash + canonical(entry fields))
  signature: string;     // HMAC-SHA256(account_key, hash)
}

// ------------------------------------------------------------- hashing

/** Deterministic JSON: object keys sorted, no incidental whitespace. */
export function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  const keys = Object.keys(value as Record<string, unknown>).sort();
  const body = keys
    .map((k) => `${JSON.stringify(k)}:${canonical((value as Record<string, unknown>)[k])}`)
    .join(",");
  return `{${body}}`;
}

function entryHash(entry: Omit<LedgerEntry, "hash" | "signature">): string {
  const { prev_hash, ...fields } = entry;
  return createHash("sha256").update(prev_hash + canonical(fields)).digest("hex");
}

function sign(accountKey: string, hash: string): string {
  return createHmac("sha256", accountKey).update(hash).digest("hex");
}

// -------------------------------------------------------------- ledger

export class Ledger {
  private entries: LedgerEntry[] = [];
  private accountKey: string;
  constructor(accountKey: string) {
    this.accountKey = accountKey;
  }

  append(fields: Omit<LedgerEntry, "id" | "ts" | "prev_hash" | "hash" | "signature">): LedgerEntry {
    const prev_hash = this.entries.length
      ? this.entries[this.entries.length - 1].hash
      : "GENESIS";
    const base = {
      id: randomUUID(),
      ts: new Date().toISOString(),
      prev_hash,
      ...fields,
    };
    const hash = entryHash(base);
    const entry: LedgerEntry = { ...base, hash, signature: sign(this.accountKey, hash) };
    this.entries.push(entry);
    return entry;
  }

  all(): readonly LedgerEntry[] {
    return this.entries;
  }

  /**
   * Third-party verification (Principle 5): recompute every hash and
   * signature and confirm the chain is unbroken. Any edited or deleted
   * entry fails verification at that position.
   */
  verify(): { ok: true } | { ok: false; atIndex: number } {
    for (let i = 0; i < this.entries.length; i++) {
      const e = this.entries[i];
      const expectedPrev = i === 0 ? "GENESIS" : this.entries[i - 1].hash;
      if (e.prev_hash !== expectedPrev) return { ok: false, atIndex: i };
      const { hash, signature, ...rest } = e;
      if (entryHash(rest) !== hash) return { ok: false, atIndex: i };
      if (sign(this.accountKey, hash) !== signature) return { ok: false, atIndex: i };
    }
    return { ok: true };
  }
}

// -------------------------------------------------------- approval gate

export type GateDecision =
  | { decision: "allow"; via: string }
  | { decision: "require_approval"; via: string }
  | { decision: "deny"; via: string };

export function evaluateGate(
  policies: Policy[],
  agentId: string,
  action: string,
  cost: number,
): GateDecision {
  const policy = policies.find((p) => p.agentId === agentId && p.action === action);
  // No policy = no approval on record = the action does not run.
  if (!policy) return { decision: "require_approval", via: "no policy — owner must decide" };
  switch (policy.mode) {
    case "never":
      return { decision: "deny", via: `policy: never (${action})` };
    case "always_ask":
      return { decision: "require_approval", via: `policy: always ask (${action})` };
    case "ask_above_limit":
      return cost <= (policy.limit ?? 0)
        ? { decision: "allow", via: `policy: auto ≤ ${policy.limit} (${action})` }
        : { decision: "require_approval", via: `policy: ask above ${policy.limit} (${action})` };
    case "auto_within_policy":
      return policy.limit !== undefined && cost > policy.limit
        ? { decision: "deny", via: `policy: above hard limit ${policy.limit} (${action})` }
        : { decision: "allow", via: `policy: auto within policy (${action})` };
  }
}

/**
 * The LAD action flow:
 *   1. Write the "planned" entry FIRST — intent is on the record.
 *   2. Evaluate the gate. Denied → "blocked" entry, nothing executes.
 *      Approval required → the entry waits; the owner's decision is
 *      itself recorded before anything runs.
 *   3. Execute, then record the outcome against the same chain.
 */
export async function runAction(args: {
  ledger: Ledger;
  policies: Policy[];
  agentId: string;
  ownerId: string;
  action: string;
  summary: string;
  cost: number;
  /** In production this asks the owner (one tap) and resolves with their call. */
  requestApproval: (planned: LedgerEntry) => Promise<boolean>;
  execute: () => Promise<string>;
}): Promise<LedgerEntry> {
  const { ledger } = args;
  const planned = ledger.append({
    agent_id: args.agentId, owner_id: args.ownerId, action: args.action,
    summary: args.summary, cost: args.cost, authorization: "pending",
    status: "planned",
  });

  const gate = evaluateGate(args.policies, args.agentId, args.action, args.cost);
  if (gate.decision === "deny") {
    return ledger.append({
      agent_id: args.agentId, owner_id: args.ownerId, action: args.action,
      summary: `${args.summary} — blocked by policy`, cost: 0,
      authorization: gate.via, status: "blocked",
    });
  }

  let authorization = gate.via;
  if (gate.decision === "require_approval") {
    const approved = await args.requestApproval(planned);
    ledger.append({
      agent_id: args.agentId, owner_id: args.ownerId, action: args.action,
      summary: `Owner ${approved ? "approved" : "denied"}: ${args.summary}`,
      cost: 0, authorization: `owner decision on entry ${planned.id}`,
      status: approved ? "approved" : "denied",
    });
    if (!approved) return planned;
    authorization = `owner approval on entry ${planned.id}`;
  }

  try {
    const result = await args.execute();
    return ledger.append({
      agent_id: args.agentId, owner_id: args.ownerId, action: args.action,
      summary: `${args.summary} — result: ${result}`, cost: args.cost,
      authorization, status: "completed",
    });
  } catch (err) {
    return ledger.append({
      agent_id: args.agentId, owner_id: args.ownerId, action: args.action,
      summary: `${args.summary} — failed: ${(err as Error).message}`,
      cost: 0, authorization, status: "failed",
    });
  }
}

// ---------------------------------------------------------------- demo

async function demo() {
  const ledger = new Ledger("demo-account-key");
  const policies: Policy[] = [
    { agentId: "digest-agent", action: "digest.publish", mode: "auto_within_policy", limit: 10 },
    { agentId: "digest-agent", action: "purchase.create", mode: "ask_above_limit", limit: 25 },
  ];
  // The demo owner approves ordinary work and denies the destructive
  // action that no policy covers — the gate held it for a human decision.
  const owner = async (planned: LedgerEntry) => planned.action !== "account.delete";

  await runAction({
    ledger, policies, agentId: "digest-agent", ownerId: "owner-1",
    action: "digest.publish", summary: "Publish the morning digest",
    cost: 10, requestApproval: owner,
    execute: async () => "digest sent to 1 destination",
  });
  await runAction({
    ledger, policies, agentId: "digest-agent", ownerId: "owner-1",
    action: "purchase.create", summary: "Buy a $40 data subscription",
    cost: 40, requestApproval: owner,
    execute: async () => "order confirmed",
  });
  await runAction({
    ledger, policies, agentId: "digest-agent", ownerId: "owner-1",
    action: "account.delete", summary: "Delete the account",
    cost: 0, requestApproval: owner,
    execute: async () => "should never run — no policy on record",
  });

  for (const e of ledger.all()) {
    console.log(`${e.ts}  ${e.status.padEnd(9)}  ${e.action}  ${e.summary}`);
  }
  console.log("\nChain verification:", ledger.verify());
}

demo();
