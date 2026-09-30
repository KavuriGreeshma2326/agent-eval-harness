import unittest

from coupons import CouponBook


class CouponTests(unittest.TestCase):
    def test_new_book_is_empty(self):
        self.assertEqual(CouponBook().count(), 0)

    def test_store_and_lookup(self):
        book = CouponBook()
        book.add("save10")
        self.assertTrue(book.has("SAVE10"))
        self.assertEqual(book.count(), 1)

    def test_unknown_code_not_found(self):
        self.assertFalse(CouponBook().has("FREESHIP"))


if __name__ == "__main__":
    unittest.main()
