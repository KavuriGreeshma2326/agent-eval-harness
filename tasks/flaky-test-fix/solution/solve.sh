#!/bin/bash
# Two sources of shared state leak between tests:
# 1. new_cart(items=[]) uses a mutable default argument, so every default cart shares one list.
# 2. CouponBook.codes is a class attribute, so every CouponBook instance shares one list.
cd /app/project
python3 - <<'PY'
from pathlib import Path

cart = Path("cart.py")
cart.write_text(cart.read_text().replace(
    'def new_cart(items=[]):\n    """Create a cart. Pass a list of (name, price) tuples to start pre-filled."""\n    return {"items": items}',
    'def new_cart(items=None):\n    """Create a cart. Pass a list of (name, price) tuples to start pre-filled."""\n    return {"items": list(items) if items is not None else []}',
))

coupons = Path("coupons.py")
coupons.write_text(coupons.read_text().replace(
    "    codes = []\n\n    def add",
    "    def __init__(self):\n        self.codes = []\n\n    def add",
))
PY
python3 -m unittest -q
