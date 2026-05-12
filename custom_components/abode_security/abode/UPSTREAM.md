# Vendored `jaraco.abode` Fork

Tracking: [#62](https://github.com/molant/abode-security/issues/62)
Spec: [features/abode-fork-modernization/README.md](../../../features/abode-fork-modernization/README.md)

## Lineage

| Field | Value |
|-------|-------|
| Upstream | https://github.com/jaraco/jaraco.abode |
| Fork commit (this repo) | `aee5d16386c8747191d52fd2197c0e5dc40d4522` |
| Fork date | 2025-12-01 |
| Local commits modifying this directory | 23 |

## Intentional divergence

These changes are deliberate and must not be reverted by a sync:

- `cli.py`, `__main__.py` removed — no command-line interface in HA-integration context.
- `keyring`-based credential persistence removed — HA owns config storage.
- Synchronous HTTP (`requests`) replaced with `aiohttp.ClientSession`.
- (Phase 3, future) `lomond` WebSocket transport replaced with `aiohttp.ClientWebSocketResponse`; SocketIO daemon thread folded into the HA event loop.

## Sync policy

This fork is hard-diverged from upstream. We do **not** run a scheduled
upstream sync, a quarterly diff review, or any automation against this
directory.

**Exception**: if a CVE is filed against `jaraco.abode` and our fork is
affected, do a one-time targeted backport. Note it in this file under a
"Backport history" section. Otherwise, treat upstream as a reference, not
a source.

## Dynamic discovery surface

`devices/base.py` calls `pkg.import_all()` which walks the `devices/`
package and triggers concrete `Device` subclass registration via
`_ancestry.iter_subclasses`. **Removing a device module without first
checking the audit log will silently disable that device type.** Phase 1
of the fork-modernization spec adds a log line capturing the registered
class list; see that log before any module deletion.

`Unknown(Device)` is a fallback class defined in `base.py`. The audit
log filters it out (only modules other than `base` are logged); `base.py`
is never a delete candidate.
