# Security Policy

## Supported Versions

This is a custom Home Assistant integration distributed via HACS. Only the latest release on `main` receives security fixes. There are no separate release lines or LTS branches.

| Version | Supported |
| ------- | --------- |
| Latest release on `main` | Yes |
| Older releases | No — upgrade to the latest release |

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Report privately via GitHub Security Advisories:

- Open <https://github.com/molant/abode-security/security/advisories/new>
- Or: from the repository, click **Security** → **Advisories** → **Report a vulnerability**.

If GitHub's private reporting flow is unavailable to you, open a public issue that says only *"requesting a private channel to report a security issue"* — include no sensitive details — and a maintainer will follow up.

### What to include

- Affected version (commit SHA or release tag).
- Reproduction steps or proof-of-concept.
- Impact: what an attacker can read, modify, or do.
- Whether the issue is in the outer integration (`custom_components/abode_security/*.py`), the vendored library (`custom_components/abode_security/abode/`), the frontend (`frontend/`), or the websocket API.

## Response Targets

These are targets, not guarantees — this is a personal-time project.

| Severity | Acknowledge | Fix or workaround |
| -------- | ----------- | ----------------- |
| HIGH / CRITICAL | 7 days | 30 days |
| MEDIUM | 14 days | 60 days |
| LOW | 30 days | Best effort |

## Scope

### In scope

- The outer integration code under `custom_components/abode_security/` (excluding the vendored `abode/` subdirectory, addressed below).
- The frontend panel under `frontend/`.
- The websocket API exposed to Home Assistant (`websocket_api.py`).
- The action engine and any path that touches user-supplied configuration.
- Vulnerabilities in the vendored `custom_components/abode_security/abode/` fork of [`jaraco.abode`](https://github.com/jaraco/jaraco.abode) — see *Bundled and unmaintained dependencies* below.
- Vulnerabilities surfaced via the pinned `lomond` dependency, until it is replaced — see *Bundled and unmaintained dependencies* below.

### Out of scope

- Vulnerabilities in Home Assistant Core itself — report those upstream at <https://github.com/home-assistant/core/security>.
- Vulnerabilities in the Abode cloud service or its APIs — report those to [Abode](https://goabode.com/) directly.
- Issues that require a malicious Home Assistant administrator (admin already has full control of the host).
- Findings from automated scanners with no demonstrated impact (please attach a working proof-of-concept).

## Bundled and Unmaintained Dependencies

This integration ships with two upstream codebases that are unmaintained:

- **`custom_components/abode_security/abode/`** — a *vendored* fork of `jaraco.abode` with async modifications, checked into this repo. CVEs disclosed against upstream `jaraco.abode` are in scope here until [the fork is replaced](https://github.com/molant/abode-security/issues/62). The maintainer commits to evaluating each CVE against the vendored copy and either backporting a fix, applying a workaround, or documenting that the vendored copy is unaffected.
- **`lomond`** — a *pinned pip dependency* (declared in `pyproject.toml` and `manifest.json`), not vendored. Upstream's last release was in 2018. CVEs disclosed against `lomond` are in scope here until [it is replaced](https://github.com/molant/abode-security/issues/61). The maintainer commits to bumping or pinning around the affected version, applying a workaround in this integration, or documenting non-applicability.

## Disclosure

After a fix lands, a GitHub Security Advisory will be published with the reporter credited (unless the reporter requests anonymity).
