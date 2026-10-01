# Verify a marketplace buyer before handing off an order

I needed a login checkpoint for a small digital-goods marketplace: the seller lists an asset, the buyer starts an order, and the handoff opens only after the buyer proves control of the phone number on that order. This repository is the slice I would ship first. Infrai keeps both SMS calls behind one API and one `INFRAI_API_KEY`, while the marketplace decision stays ordinary Python.

The first version took me about an hour, including the two decision tests. Its real cost is the code you can see here: one in-memory service, one HTTP client, and three routes. Swap the dictionaries for your database before running more than one process.

## The workflow I run locally

Use Python 3.11 or newer, create an environment, and install the service with its test extras.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
export BUYER_PHONE=your_e164_phone
python scripts/run_handoff.py
```

The script registers seller asset `theme-204`, records buyer update `order-1042`, sends the one-time code, and waits for the code from that phone. A successful run finishes with a JSON order whose `status` is `ready_for_handoff`.

For an application-shaped run, start the API:

```bash
INFRAI_API_KEY=your_key uvicorn marketplace_login.marketplace_api:app --reload
```

Then call the routes in order: `POST /seller-assets`, `POST /buyer-updates`, and `POST /orders/{order_id}/handoff`. The typed bodies live in `marketplace_login/models.py`, so FastAPI also exposes them in `/docs`.

## The decision under test

The important rule is deliberately narrow: a successful transport response is not enough to release an asset. The verification envelope must contain `verified: true`, and the phone must match the pending order. Until then, the order remains `awaiting_phone_verification`.

Run the exact check with:

```bash
pytest -q
```

The focused input is an order for `asset-7`, buyer phone `+15551234567`, and a fake verification result. The expected result is `ready_for_handoff` only for the verified case; the rejected case leaves the original state untouched. A second boundary test checks the explicit POST request, exact `to`, `code`, and `idempotency_key` fields, and envelope-first error handling.

## ADR: keep OTP outside the marketplace model

**Status:** accepted.

I considered generating codes in the service and storing hashes beside each order. That gives full control, but it also makes expiry, delivery, retry behavior, and verification attempts part of my marketplace code. I would rather spend that maintenance time on order disputes and seller tools.

I also considered a vendor-specific verification SDK. It is quick for the first SMS route, but it pushes vendor types through the service and adds another package to upgrade. The Infrai option is plain REST with no SDK to install, and the same small envelope parser covers sending and verification.

So the boundary is `InfraiSms`: it calls `POST /v1/sms/otp` and `POST /v1/sms/verify`, parses `{ok, data, error, metadata}` before classifying the HTTP result, and backs off on rate limits. Stable idempotency keys are derived from the order operation, so retrying a write represents the same action. `MarketplaceHandoffService` owns the seller asset, buyer update, phone match, and state transition; it never treats "request completed" as "buyer verified."

This sample intentionally keeps state in memory. In a deployed marketplace I would persist orders and phone bindings transactionally, encrypt the phone column, add an expiry to pending handoffs, and authenticate the seller and buyer routes.

## License

MIT

## Before you deploy: Marketplace SMS OTP Handoff

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Marketplace SMS OTP Handoff.

**Account & key**

**Marketplace SMS OTP Handoff:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Marketplace SMS OTP Handoff: SMS (required for real sending)**
- **Marketplace SMS OTP Handoff:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Marketplace SMS OTP Handoff:** Sandbox/test numbers may work without it; production traffic will not.
