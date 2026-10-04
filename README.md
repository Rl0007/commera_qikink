# Commera Qikink

Sends your Commera store orders to [Qikink](https://qikink.com), which prints and ships them for you.

- A paid order goes to Qikink by itself. You send a cash on delivery (COD) order with **Send to Qikink**.
- Each Qikink line is bought from Qikink with a drop-ship Purchase Order.
- Every hour the app reads each open order's status from Qikink. When Qikink ships, the order gets its
  courier, AWB and tracking link, and the shopper sees them. When Qikink delivers, the Purchase Order is
  marked delivered.
- Checkout refuses a cart that holds a Qikink product without a Qikink SKU.

## Install

Commera must be on the site first.

```bash
cd ~/frappe-bench
bench get-app https://github.com/Rl0007/commera_qikink
bench --site your.site install-app commera_qikink
bench build --app commera_qikink
bench restart
```

## Set up

1. Create a Supplier for Qikink in ERPNext, and a buying Price List with a buying price for each Qikink
   product variant. The Purchase Order uses these prices.
2. In the Commera dashboard, open **Settings > Installed apps > Qikink** and fill in:
   - **Client ID** and **Client Secret**: from your Qikink dashboard (Integration > Custom API).
   - **Sandbox**: keep it on while you test against Qikink's sandbox.
   - **Supplier**: the Qikink supplier.
   - **Buying Price List**: the price list from step 1.
3. Open a product and click **More actions > Set Qikink SKUs**. You enter one SKU for each variant
   (colour and size), because one Qikink SKU is one model, colour and size. A product without variants
   takes one SKU. For each SKU, choose how Qikink reads it:
   - **Plain off**: the SKU of your own design on Qikink's **My Products** page.
   - **Plain on**: a blank catalog SKU, such as `MVnHs-Wh-S`. Qikink ships it without a print.

   Saving also marks each mapped variant as delivered by the supplier, with Qikink as its default
   supplier. The product's **Qikink** card shows how many variants are mapped.

## How orders flow

1. **Paid orders.** When Commera marks an order paid, the app sends it to Qikink. The Qikink order number is
   the digits of the order name: `SAL-ORD-2026-00062` becomes `202600062`. A name that gives more than 15
   digits is refused, never cut short.
2. **COD orders.** Submit the order first. Then click **More actions > Send to Qikink** on the order. Qikink's
   courier collects the cash.
3. **Purchase Order.** Right after Qikink accepts the order, the app makes and submits a drop-ship Purchase
   Order to your Qikink supplier. If a buying price is missing, the order stays with Qikink and the app
   logs an Error Log. Add the price, then click **Send to Qikink** again to make the Purchase Order.
4. **Status.** An hourly job reads the status of every open order. **More actions > Refresh Qikink status**
   on an order reads it at once, and **Sync now** on the **Qikink orders** page reads all open orders.

An order is never sent twice. If a send fails halfway, the next attempt first looks for the order on Qikink
and uses it when it is there.

The **Qikink orders** page in the sidebar lists every order sent to Qikink, with its Qikink number and
status, Purchase Order, shipment status and the date it was sent. The **Qikink** card on an order shows the
same details for that order.

## Limits

- Cancellations and returns are not synced. Qikink has no cancel API; cancel on Qikink's dashboard and in
  ERPNext yourself. A submitted Purchase Order stops the Sales Order from being cancelled until you cancel
  the Purchase Order.
- Qikink's sandbox answers `order/list` with 404, so the app reads status with the older order endpoint. It
  pages through your newest 200 Qikink orders; an older open order is not found.
- Paying Qikink from your wallet, and the Purchase Invoice for it, are manual.
- Qikink has no webhooks, so a status reaches Commera within an hour, or when you refresh.

## Development

```bash
cd ~/frappe-bench/apps/commera_qikink
yarn dev
```

`yarn dev` rebuilds the dashboard extensions under `commera/` each time you save. Reload `/commera` to see
the change. `commera/README.md` lists what each folder adds.

Run the tests on a site with `allow_tests` on:

```bash
bench --site your.site run-tests --app commera_qikink
```

The tests use the real database and never call Qikink. They need one order already sent to Qikink and one
item with a Qikink SKU on the site.

## License

MIT
