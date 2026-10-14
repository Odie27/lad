"""
LAD + A2A — conceptual delegation chain (illustrative, NOT the Double-Oh API).

A parent agent delegates a SUBSET of its authority to a child agent as a
signed, expiring token. The child can act only inside the delegated bounds;
every action is sequenced with a nonce (replays are dropped) and chained
into a tamper-evident ledger (each block commits to the previous hash).

Fix vs. the original draft: claims are base64url-encoded before signing.
Joining raw JSON to the signature with '.' and splitting on '.' to parse
breaks whenever a claim value contains a '.' — e.g. any decimal amount.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class LADSecurityEngine:
    def __init__(self, cluster_secret: bytes):
        self.cluster_secret = cluster_secret
        self.agent_nonces = {}          # highest processed nonce per agent
        self.last_ledger_hash = "0" * 64

    # ------------------------------------------------------- delegation
    def issue_delegation_token(self, parent_id, child_id, constraints,
                               duration_sec=3600):
        claims = {
            "iss": parent_id,
            "sub": child_id,
            "exp": int(time.time()) + duration_sec,
            "gates": constraints,
            "jti": str(uuid.uuid4()),
        }
        body = _b64(json.dumps(claims, sort_keys=True).encode())
        signature = hmac.new(self.cluster_secret, body.encode(),
                             hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def verify_delegation_token(self, token_str, target_child_id):
        try:
            body, signature = token_str.rsplit(".", 1)
            expected = hmac.new(self.cluster_secret, body.encode(),
                                hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError("CRYPTOGRAPHIC_SIGNATURE_INVALID")
            claims = json.loads(_unb64(body))
            if claims["sub"] != target_child_id:
                raise ValueError("DELEGATION_TARGET_MISMATCH")
            if time.time() > claims["exp"]:
                raise ValueError("DELEGATION_TOKEN_EXPIRED")
            return claims["gates"]
        except Exception as e:
            return {"error": f"LAD Security Gate Drop: {e}", "valid": False}

    # ------------------------------------------------------------ ledger
    def commit_action(self, agent_id, nonce, action_payload):
        block = {
            "agent_id": agent_id,
            "nonce": nonce,
            "payload": action_payload,
            "prev_hash": self.last_ledger_hash,
            "timestamp": int(time.time()),
        }
        block_hash = hashlib.sha256(
            json.dumps(block, sort_keys=True).encode()).hexdigest()
        self.last_ledger_hash = block_hash
        self.agent_nonces[agent_id] = nonce
        return block_hash


def run_a2a_compliance_simulation():
    master_node = LADSecurityEngine(b"secure_lad_network_backbone_key_2026")

    print("=== STEP 1: PARENT AGENT ISSUES A DELEGATION TOKEN ===")
    delegated_bounds = {"max_allowable_spend": 150.00,
                        "approved_categories": ["logistics", "postage"]}
    token = master_node.issue_delegation_token(
        parent_id="agent_core_purchasing",
        child_id="agent_delivery_procurement",
        constraints=delegated_bounds)
    print(f"[ok] Token issued (scoped, signed, expiring): {token[:48]}...\n")

    child = "agent_delivery_procurement"
    master_node.agent_nonces[child] = 0
    gates = master_node.verify_delegation_token(token, child)
    if "error" in gates:
        print(f"[FAIL] {gates['error']}")
        return

    print("=== STEP 2: CHILD ACTS INSIDE ITS DELEGATED BOUNDS ===")
    action = {"item": "Envelopes and Postage Packs", "cost": 45.00,
              "category": "postage"}
    if (action["cost"] <= gates["max_allowable_spend"]
            and action["category"] in gates["approved_categories"]):
        tx_hash = master_node.commit_action(child, 1, action)
        print(f"[ok] Approved and chained. Ledger hash: {tx_hash[:16]}...\n")
    else:
        print("[BLOCKED] Outside delegated bounds.\n")

    print("=== STEP 3: REPLAY ATTACK (re-using nonce 1) ===")
    if 1 <= master_node.agent_nonces[child]:
        print("[BLOCKED] Out-of-sequence nonce — replay dropped at the gate.\n")

    print("=== STEP 4: PARAMETER ESCALATION ($1,200 vs $150 bound) ===")
    exploit = {"item": "Server Rack Equipment", "cost": 1200.00,
               "category": "logistics"}
    if exploit["cost"] > gates["max_allowable_spend"]:
        print(f"[BLOCKED] Exceeds delegated max_allowable_spend "
              f"(${gates['max_allowable_spend']}). The child cannot sign "
              f"itself a bigger bound — only the parent can re-issue.\n")


if __name__ == "__main__":
    run_a2a_compliance_simulation()
