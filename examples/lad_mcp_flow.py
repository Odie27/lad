"""
LAD + MCP — conceptual flow (illustrative, NOT the Double-Oh API).

An agent may not call a tool directly. The action passes the gate first:
policy is checked, the outcome is written to the hash-chained ledger, and
only then is the tool invoked — carrying a receipt token the tool server
can verify against the issuing engine.

Mechanics shown:
  * Deny-dominance: any single rule violation blocks the action.
  * Hold, don't reject: an action needing a human co-sign is HELD for an
    owner decision (the hold is itself a ledger entry), not denied.
  * Verification is cryptographic: the mock tool server validates the
    receipt token's HMAC instead of accepting any non-empty string.
"""

import hashlib
import hmac
import json
import time
import uuid

ENGINE_SECRET = b"owner_defined_deterministic_key_101"  # demo only


# ---------------------------------------------------------------- ledger
class Ledger:
    """Append-only, hash-chained record (ARCHITECTURE.md: the entry hash is
    SHA256(prev_hash + canonical(entry fields)), signed with HMAC-SHA256)."""

    GENESIS = "0" * 64

    def __init__(self):
        self.entries = []

    def append(self, agent_id, action, detail, authorization):
        prev = self.entries[-1]["hash"] if self.entries else self.GENESIS
        entry = {
            "index": len(self.entries) + 1,
            "agent_id": agent_id,
            "action": action,
            "detail": detail,
            "authorization": authorization,
            "timestamp": int(time.time()),
            "prev_hash": prev,
        }
        canonical = json.dumps(entry, sort_keys=True)
        entry["hash"] = hashlib.sha256((prev + canonical).encode()).hexdigest()
        entry["signature"] = hmac.new(
            ENGINE_SECRET, entry["hash"].encode(), hashlib.sha256
        ).hexdigest()
        self.entries.append(entry)
        return entry


# ------------------------------------------------------------------- gate
class Gate:
    """Evaluates an intended action against the owner's policy."""

    def __init__(self, policy, ledger):
        self.policy = policy
        self.ledger = ledger

    def evaluate(self, agent_id, tool_name, args):
        gates = self.policy["deterministic_gates"]["approval_constraints"]
        amount = float(args.get("amount", 0))
        currency = args.get("currency", "USD")
        vendor = args.get("vendor", "")

        if currency not in gates["allowed_currencies"]:
            return self._record(agent_id, tool_name, args, "BLOCKED",
                                f"Unsupported currency: {currency}")
        if vendor in gates["restricted_vendors"]:
            return self._record(agent_id, tool_name, args, "BLOCKED",
                                f"Vendor '{vendor}' is restricted by policy.")
        if amount > gates["max_single_transaction_usd"]:
            return self._record(agent_id, tool_name, args, "BLOCKED",
                                f"${amount} exceeds the absolute cap of "
                                f"${gates['max_single_transaction_usd']}.")
        if amount > gates["requires_human_co_sign_above_usd"]:
            # Approval gates HOLD consequential actions for a decision;
            # they only deny what policy says may never happen.
            return self._record(agent_id, tool_name, args, "HELD",
                                f"Above the co-sign threshold of "
                                f"${gates['requires_human_co_sign_above_usd']} "
                                f"— awaiting owner decision.")
        return self._record(agent_id, tool_name, args, "APPROVED",
                            "Within policy.")

    def _record(self, agent_id, tool_name, args, outcome, reason):
        entry = self.ledger.append(
            agent_id, f"call_tool:{tool_name}", f"{args} -> {outcome}: {reason}",
            authorization="owner policy",
        )
        receipt = None
        if outcome == "APPROVED":
            # Receipt token: HMAC over the ledger entry hash, so a tool
            # server can verify the action really passed this gate.
            receipt = hmac.new(ENGINE_SECRET, entry["hash"].encode(),
                               hashlib.sha256).hexdigest()
        return {"outcome": outcome, "reason": reason,
                "ledger_index": entry["index"], "receipt_token": receipt}

    def verify_receipt(self, receipt_token, ledger_index):
        if not receipt_token or not (1 <= ledger_index <= len(self.ledger.entries)):
            return False
        expected = hmac.new(
            ENGINE_SECRET,
            self.ledger.entries[ledger_index - 1]["hash"].encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, receipt_token)


# ------------------------------------------------------- mock MCP tool host
def mock_mcp_server(request, gate):
    """A tool server that refuses to run anything the gate hasn't passed."""
    params = request.get("params", {})
    token = params.get("lad_auth_token")
    ledger_index = params.get("lad_ledger_index", 0)

    if not gate.verify_receipt(token, ledger_index):
        return {"jsonrpc": "2.0", "id": request.get("id"),
                "error": {"code": -32001,
                          "message": "LAD violation: missing or unverifiable "
                                     "ledger receipt token."}}
    args = params.get("arguments", {})
    return {"jsonrpc": "2.0", "id": request.get("id"),
            "result": {"status": "SUCCESS",
                       "message": f"Paid ${args['amount']} {args['currency']} "
                                  f"to {args['vendor']}."}}


# -------------------------------------------------------------------- demo
def execute_agent_action(gate, agent_id, tool_name, tool_args):
    print(f"[*] Gate check for {tool_name} {tool_args} ...")
    verdict = gate.evaluate(agent_id, tool_name, tool_args)
    print(f"    -> {verdict['outcome']}: {verdict['reason']} "
          f"(ledger #{verdict['ledger_index']})")
    if verdict["outcome"] != "APPROVED":
        return verdict
    request = {
        "jsonrpc": "2.0", "method": f"tools/{tool_name}", "id": str(uuid.uuid4()),
        "params": {"arguments": tool_args,
                   "lad_auth_token": verdict["receipt_token"],
                   "lad_ledger_index": verdict["ledger_index"]},
    }
    return mock_mcp_server(request, gate)


if __name__ == "__main__":
    with open("lad_policy.example.json") as f:
        policy = json.load(f)
    ledger = Ledger()
    gate = Gate(policy, ledger)
    agent = policy["policy_metadata"]["agent_id"]

    print("=== Scenario 1: above the absolute cap ($650 vs $500) ===")
    print(execute_agent_action(gate, agent, "execute_payment",
                               {"amount": 650, "currency": "USD", "vendor": "SupplierX"}))
    print("\n=== Scenario 2: needs a co-sign ($320 vs $250 threshold) ===")
    print(execute_agent_action(gate, agent, "execute_payment",
                               {"amount": 320, "currency": "USD", "vendor": "SupplierX"}))
    print("\n=== Scenario 3: compliant ($150, clean vendor) ===")
    print(execute_agent_action(gate, agent, "execute_payment",
                               {"amount": 150, "currency": "USD", "vendor": "SupplierX"}))
    print(f"\nLedger: {len(ledger.entries)} entries, chain head "
          f"{ledger.entries[-1]['hash'][:16]}…")
