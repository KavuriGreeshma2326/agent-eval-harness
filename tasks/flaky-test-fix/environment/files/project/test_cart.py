import unittest

from cart import add_item, item_count, new_cart, total


class CartTests(unittest.TestCase):
    def test_empty_cart_total(self):
        self.assertEqual(total(new_cart()), 0)

    def test_item_count_starts_at_zero(self):
        self.assertEqual(item_count(new_cart()), 0)

    def test_prefilled_cart(self):
        cart = new_cart([("mug", 7.5)])
        self.assertEqual(total(cart), 7.5)

    def test_total_after_adding(self):
        cart = new_cart()
        add_item(cart, "pen", 10.0)
        add_item(cart, "book", 20.0)
        self.assertEqual(total(cart), 30.0)
        self.assertEqual(item_count(cart), 2)


if __name__ == "__main__":
    unittest.main()
