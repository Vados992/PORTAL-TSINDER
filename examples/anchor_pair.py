"""Run: python examples/anchor_pair.py (after installing the package).

Real HMAC operations over two explicitly simulated records. Ephemeral secrets
are generated locally and never printed or written into experiment evidence.
"""
import json
import secrets
from portal_tsinder.anchors import Anchor, AnchorRegistry, sign

keys = {name: secrets.token_bytes(32) for name in ("A", "B")}
registry = AnchorRegistry(keys)
for name, x in (("A", 0.0), ("B", 10.0)):
    record = Anchor(name, "SIM-TOPOLOGY", "LAB", 100, 200, 1, 1, (x, 0, 0))
    registry.accept(sign(record, keys[name]), now_s=101)
print(json.dumps(registry.route("A", "B", now_s=102), indent=2))
