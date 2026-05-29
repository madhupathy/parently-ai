# Gmail / Drive OAuth Scope Risk Memo

Date: 2026-05-29
Status: **DECISION (2026-05-29): Option #1 — invite-only beta with manually-added Google test users.**

The "Google hasn't verified this app" / "Advanced → Continue" screen is therefore expected behaviour for every new user until either (a) we add them under Test users in Google Cloud Console, and (b) they click through the warning once. The in-app integration cards and dashboard empty state now mention this so users aren't surprised.

This stays valid until we have ~$2k MRR or pivot to a non-restricted-scope architecture (option #2 below).

## TL;DR

Parently currently requests two **Google "restricted" OAuth scopes**:

| Scope | Where requested | Google policy class |
|---|---|---|
| `https://www.googleapis.com/auth/gmail.readonly` | `apps/web/auth.ts:16`, `apps/web/components/integration-cards.tsx:185`, `apps/web/app/settings/page.tsx:910`, `apps/backend/services/integration_state.py:10`, `apps/backend/services/connectors/classdojo.py:30`, `apps/backend/services/gmail.py:29` | **Restricted** |
| `https://www.googleapis.com/auth/drive.readonly` | `apps/web/auth.ts:16`, `apps/web/components/integration-cards.tsx:186`, `apps/web/app/settings/page.tsx:911`, `apps/backend/services/integration_state.py:11` | **Restricted** |

Restricted scopes require Google OAuth verification **plus** an annual third-party security assessment (CASA Tier 2 or 3) to be usable by anyone outside a manually-allowlisted test list of up to 100 users. CASA assessment fees from Google-approved assessors run roughly **$15 000 – $75 000 per year** depending on data classes handled. There is no non-restricted scope that returns the body of arbitrary Gmail messages.

This is a **business/legal decision**, not a code issue. Below are the realistic paths forward.

---

## Why these scopes are restricted

Google classifies any scope that returns the body or headers of arbitrary user mail as a "Restricted Scope" under the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy#additional_requirements_for_specific_api_scopes). Same applies to broad Drive read.

Without verification and CASA, your OAuth consent screen is locked to **publishing status: testing** with a hard cap of 100 manually-listed test users and a forced "unverified app" warning screen.

---

## Options ranked by practicality for a single-developer SaaS

### 1. Stay in Testing mode (cheapest, most limited)

- Up to 100 test users you add manually in the Google Cloud console.
- No CASA, no verification, no annual fee.
- "App not verified" warning on first sign-in (you can self-acknowledge).
- **Use case fit**: friends/family beta, paying $0.

### 2. Gmail forward-to-our-domain (no OAuth at all)

- User creates a Gmail filter that forwards school-related senders to `<user-token>@in.parently-ai.com`.
- We receive via SES/Mailgun/Postmark inbound, parse the email, attach to the right child.
- **No OAuth scope is needed.** No CASA, no verification.
- Trade-off: setup is more friction (user must configure forwarding once), and we only see what the filter forwards.
- This is how Superhuman, [Hey.com](https://hey.com), and most "email assistant" tools that haven't done CASA operate.
- **Estimated build effort: ~1 week** to spin up an inbound endpoint + forwarding-setup wizard.

### 3. Gmail Add-on (narrow, low-cost path)

- App runs inside the Gmail UI as a side panel; uses `gmail.addons.current.message.readonly` which is **non-restricted**.
- Trade-off: the app no longer runs at parently-ai.com — it runs in the user's Gmail. UX is very different from current Parently.
- Doesn't help with Drive at all.

### 4. CASA Tier 2 (the "do it properly" path)

- Required if you stay on `gmail.readonly` for general public users.
- Annual cost ~$15k–$25k for the assessor + your remediation time.
- Requires: pen test, secure SDLC docs, key management process, incident response runbook, data retention controls, vendor risk reviews.
- Realistic only once Parently has paying revenue to support it.

### 5. Drop Drive entirely

Regardless of which Gmail path you pick, consider dropping `drive.readonly` outright. The school-PDF use case it supports could be served by:
- Upload-from-device (we already have `apps/web/app/api/uploads/pdf/route.ts`).
- Forwarded attachments via path #2.

This removes one of the two restricted scopes immediately and shrinks future CASA scope.

---

## Recommended sequencing

1. **Now**: drop `drive.readonly` from the OAuth request. Re-route the school-PDF flow through the existing uploads endpoint. (~1 day work.)
2. **Before public launch**: pick between #1 (testing-only beta), #2 (forward-to-inbox), or #3 (Gmail Add-on). All three are CASA-free.
3. **When MRR > ~$2k/mo**: re-evaluate CASA for the full `gmail.readonly` experience.

Concretely, I'd recommend option #2 (forward-to-inbox) as the launch path: it preserves the current UX shape on parently-ai.com and avoids CASA indefinitely. Option #1 is fine as a holdover for a private beta.

---

## What I am NOT recommending

- **Hiding the scope or splitting it across multiple apps.** Google explicitly forbids "scope laundering" and will revoke API access. Several apps have been kicked off the platform for this.
- **Asking users to bypass the unverified-app warning at scale.** Fine for a 50-user beta; reputation-destroying for a public launch.

---

## Files that need code changes once a path is picked

If you pick **#5 + #1** (drop Drive, beta-only) — this is the smallest change:
- `apps/web/auth.ts` — remove `drive.readonly` from the scope string.
- `apps/web/components/integration-cards.tsx` — remove the Drive scope branch.
- `apps/web/app/settings/page.tsx` — same.
- `apps/backend/services/integration_state.py` — remove `DRIVE_SCOPE` references where it gates connector readiness.
- `apps/backend/services/drive_ingest.py` — keep code but stop calling it from the digest pipeline.
- `deployment.md` — note Drive is no longer a connected scope.

If you pick **#2** (forward-to-inbox) — bigger build, separate design doc needed.

---

## References

- Google API Services User Data Policy: https://developers.google.com/terms/api-services-user-data-policy
- Restricted-scope app verification FAQ: https://support.google.com/cloud/answer/13463073
- CASA scopes/tiers (App Defense Alliance): https://appdefensealliance.dev/casa
- Gmail Add-ons scope documentation: https://developers.google.com/workspace/add-ons/concepts/workspace-add-on-authorization
