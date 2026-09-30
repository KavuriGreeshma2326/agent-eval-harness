"""Hidden checks that the fix keeps the public behavior of cart.py and coupons.py."""
import sys

sys.path.insert(0, "/app/project")
from cart import add_item, item_count, new_cart, total
from coupons import CouponBook

a, b = new_cart(), new_cart()
add_item(a, "x", 1.25)
assert item_count(a) == 1 and item_count(b) == 0, "default carts must be independent"
assert total(new_cart([("mug", 7.5), ("tea", 2.25)])) == 9.75, "pre-filled carts must work"
c = new_cart()
add_item(c, "pen", 0.1)
add_item(c, "pad", 0.2)
assert total(c) == 0.3, "total must still round to 2 decimals"

one, two = CouponBook(), CouponBook()
one.add("save10")
assert one.has("SAVE10") and one.has("save10"), "codes must be case-insensitive"
assert one.count() == 1 and two.count() == 0, "coupon books must be independent"
print("behavior ok")
