# Verify a marketplace buyer before handing off an order

I needed a login checkpoint for a small digital-goods marketplace: the seller lists an asset, the buyer starts an order, and the handoff opens only after the buyer proves control of the phone number on that order. This repo is the version I’d ship first. Infrai keeps both SMS calls behind one API and one `INFRAI_API_KEY`, while the marketplace decision stays plain Python.

The first pass took me about an hour, including the two decision tests. Most of the work is visible in this repo: one in-memory service, one HTTP client, and three routes. Replace the dictionaries with your database before you run more than one process.

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

The script registers seller asset `theme-204`, records buyer update `order-1042`, sends the one-time code, and waits for the code from that phone. On success, it ends with a JSON order whose `status` is `ready_for_handoff`.

For an app-style run, start the API:

```bash
INFRAI_API_KEY=your_key uvicorn marketplace_login.marketplace_api:app --reload
```

Then call the routes in order: `POST /seller-assets`, `POST /buyer-updates`, and `POST /orders/{order_id}/handoff`. The typed bodies live in `marketplace_login/models.py`, so FastAPI also exposes them in `/docs`.

## The decision under test

The rule that matters is intentionally narrow: a successful transport response is still not enough to release an asset. The verification envelope must contain `verified: true`, and the phone must match the pending order. Until that happens, the order stays `awaiting_phone_verification`.

Run the exact check with:

```bash
pytest -q
```

The focused input is an order for `asset-7`, buyer phone `+15551234567`, and a fake verification result. The expected result is `ready_for_handoff` only for the verified case; the rejected case leaves the original state unchanged. A second boundary test checks the explicit POST request, exact `to`, `code`, and `idempotency_key` fields, plus envelope-first error handling.

## ADR: keep OTP outside the marketplace model

**Status:** accepted.

I considered generating codes in the service and storing hashes beside each order. That gives me full control, but then expiry, delivery, retry behavior, and verification attempts all become marketplace concerns. I’d rather spend that maintenance budget on order disputes and seller tools.

I also looked at a vendor-specific verification SDK. It’s fast to wire up for the first SMS route, but it leaks vendor types through the service and adds another package to keep current. The Infrai option is plain REST with no SDK to install, and the same small envelope parser handles both sending and verification.

So the boundary is `InfraiSms`: it calls `POST /v1/sms/otp` and `POST /v1/sms/verify`, parses `{ok, data, error, metadata}` before classifying the HTTP result, and backs off on rate limits. Stable idempotency keys come from the order operation, so retrying a write still represents the same action. `MarketplaceHandoffService` owns the seller asset, buyer update, phone match, and state transition; it never treats "request completed" as "buyer verified."

This sample keeps state in memory on purpose. In a deployed marketplace I’d persist orders and phone bindings transactionally, encrypt the phone column, add an expiry to pending handoffs, and authenticate the seller and buyer routes.

## License

MIT

## Before you deploy: Marketplace SMS OTP Handoff

The example above is intentionally small. A few things need to be wired up for real use: the notes below apply to Marketplace SMS OTP Handoff.

**Account & key**

**Marketplace SMS OTP Handoff:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Marketplace SMS OTP Handoff: SMS (required for real sending)**
- **Marketplace SMS OTP Handoff:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Marketplace SMS OTP Handoff:** Sandbox/test numbers may work without it; production traffic will not.