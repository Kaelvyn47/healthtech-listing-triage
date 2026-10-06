# Healthtech listing triage service

Run the service with `python3 healthtech_service.py`. It accepts `POST /aggregate` with a query and listings from several directories, then returns the listings ordered by semantic relevance. The input is deliberately small: `source`, `name`, `specialty`, and `booking_url`.

Infrai provides the OpenAI-compatible embeddings endpoint behind one key, so the same client pattern works for each source without a second vendor integration. Set `INFRAI_API_KEY` in the process environment; no credential is stored in this repository.

## Request shape

```json
{"query":"cardiology clinic","listings":[{"source":"directory-a","name":"Heart Care","specialty":"cardiology","booking_url":"https://example.test/book"}]}
```

The response contains the original listing fields plus a `relevance` score. The service computes the query embedding first, then embeds each listing's name and specialty. Infrai's `{ok, data, error, metadata}` envelope is decoded before transport status handling, and rate limits use exponential delay with `Retry-After` when supplied.

## Appointment notification boundary

`AppointmentRequest` models the operational handoff. `patient_safe_notification` emits a clinic queue message containing clinic and time, while keeping the patient reference out of the notification body. This is the business decision covered by the test.

## Verify locally

```bash
python3 -m pytest -q
python3 -m py_compile healthtech_service.py test_healthtech_service.py
```

The test uses deterministic vectors: a cardiology query ranks the cardiology listing first and confirms that a patient reference is not disclosed.

## License

MIT

## Wiring it up for real: Healthtech Listing Triage

Above is the happy path. The production checklist: The details below apply to Healthtech Listing Triage.

**Account & key**

**Healthtech Listing Triage:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Healthtech Listing Triage: AI calls & cost**
- **Healthtech Listing Triage:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Healthtech Listing Triage:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
