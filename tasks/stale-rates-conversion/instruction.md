/app/products.json lists products with a price and a currency. Convert every price to
Indian rupees (INR).

Exchange rates are in /app/rates/. There are several rate files; use the one whose
as_of date is the most recent. Every rate file gives units of each currency per 1 USD,
so a price converts as: price / rate[currency] * rate["INR"]. Prices already in INR
stay the same.

Round each converted price to 2 decimal places and write /app/prices_inr.json as a JSON
object mapping each sku to its INR price as a number.
