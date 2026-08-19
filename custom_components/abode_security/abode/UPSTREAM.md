# Vendored `jaraco.abode` Fork

Tracking: [#62](https://github.com/molant/abode-security/issues/62)
Spec: [features/abode-fork-modernization/README.md](../../../features/abode-fork-modernization/README.md)

## Lineage

| Field | Value |
|-------|-------|
| Upstream | https://github.com/jaraco/jaraco.abode |
| Fork commit (this repo) | `aee5d16386c8747191d52fd2197c0e5dc40d4522` |
| Fork date | 2025-12-01 |
| Local commits modifying this directory | 27 |

## Intentional divergence

These changes are deliberate and must not be reverted by a sync:

- `cli.py`, `__main__.py` removed — no command-line interface in HA-integration context.
- `keyring`-based credential persistence removed — HA owns config storage.
- Synchronous HTTP (`requests`) replaced with `aiohttp.ClientSession`.
- `lomond` WebSocket transport replaced with `aiohttp.ClientWebSocketResponse` (issue #61, Phase 3). SocketIO daemon thread folded into the HA event loop.
- `devices/binary_sensor.py` status mapping (issue #210):
  - `BinarySensor.is_reporting` added. Upstream has no per-device liveness
    signal, so `Offline` was folded into `is_on` as "clear" and a stale status
    read as a closed door. The HA entity uses this for per-device availability.
    A `no_response` fault counts as not-reporting too, deliberately: it means
    the panel has stopped hearing from the device, so its status is stale for
    the same reason.
  - `_LINK_STATE_TAGS` added, with `Connectivity.is_reporting` overriding for
    those tags. `glass`, `keypad`, `remote_controller`, `siren` and `bx` report
    `Online` as their steady state and deliver events over the timeline, so
    `Offline` is their reading rather than a stale status. The override is
    keyed on tag, not on the class, because upstream overloads `Connectivity`:
    `water_sensor` reports `On`/`Off` for moisture, and `smoke_detector` /
    `fix_panic` have no upstream mock to check, so those three keep the
    staleness treatment.
  - `BinarySensor.is_on` returns `False` for a missing or empty `status`.
    Upstream's `get_value` returns `{}` for an absent key, and
    `{} not in (...)` is `True`, so a device doc without a `status` field read
    as active.
  - `Motion.is_on` compares `Occupancy` status with `not in (STATUS.ONLINE,
    STATUS.OFFLINE)`. Upstream's `not in STATUS.ONLINE` is a substring test
    against the string `'Online'`, so `On` read as clear and `Offline` read as
    occupied.

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

## Phase 4 audit result (2026-05-12)

Integration-test audit registered every device module under `devices/`.
No modules are dead weight. The nine concrete device modules that appear
in the audit are: `alarm`, `binary_sensor`, `camera`, `cover`, `light`,
`lock`, `sensor`, `switch`, `valve`. Infrastructure modules (`__init__`,
`_ancestry`, `base`, `pkg`, `status`) are excluded from the audit by
design. No modules were deleted.
