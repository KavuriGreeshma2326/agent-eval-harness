class CouponBook:
    """Stores coupon codes. Codes are case-insensitive."""

    codes = []

    def add(self, code):
        self.codes.append(code.upper())

    def has(self, code):
        return code.upper() in self.codes

    def count(self):
        return len(self.codes)
