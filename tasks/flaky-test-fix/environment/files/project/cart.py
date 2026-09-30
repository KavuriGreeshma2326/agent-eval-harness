def new_cart(items=[]):
    """Create a cart. Pass a list of (name, price) tuples to start pre-filled."""
    return {"items": items}


def add_item(cart, name, price):
    cart["items"].append((name, price))


def item_count(cart):
    return len(cart["items"])


def total(cart):
    return round(sum(price for _, price in cart["items"]), 2)
