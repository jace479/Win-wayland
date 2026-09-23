# NT-Plasma Bridge Protocol

This is the initial design for communication between the Windows host bridge
and the KDE/Linux desktop bridge. It defines control and lifecycle behavior
before choosing a transport or implementing window composition.

## Participants

### Host Bridge (Windows)

The host bridge runs as the trusted Windows-side process. It owns native
application launch, native window discovery, host input policy, lifecycle
monitoring, and recovery.

### Desktop Bridge (Linux)

The desktop bridge runs inside the Linux environment with KDE. It owns the
Plasma session, Linux application state, desktop actions, and the KDE-facing
window representation.

Neither participant should execute arbitrary commands received from the other.
Commands use typed operations and validated identifiers.

## Transport requirements

The first transport must support:

1. Bidirectional messages with request identifiers.
2. Explicit connection, authentication, and protocol-version negotiation.
3. Ordered lifecycle events and acknowledgement of state changes.
4. Bounded message sizes and timeouts.
5. Clean disconnect detection and restart without stale state.

The transport is intentionally undecided. Candidate transports are a local
authenticated named pipe, a Unix socket paired with a host endpoint, or a
small broker process. Network exposure is out of scope for the first design.

The initial prototype uses newline-delimited JSON with a 1 MiB frame limit.
Authentication uses a fresh challenge and an HMAC proof over an injected
shared secret. Production credential storage and local endpoint permissions
remain design gates.

## Message envelope

Every message has this logical shape:

```text
version       protocol version
id            unique request or event identifier
kind          request, response, event, or error
operation     typed operation name
payload       operation-specific data
deadline      optional expiration timestamp
```

Responses reference the request `id`. Events are replayable or carry enough
state for the receiver to request a snapshot after reconnecting.

## Initial operations

### Session lifecycle

- `hello`: negotiate protocol version and capabilities.
- `authenticate`: establish the local peer identity and session nonce.
- `desktop.ready`: KDE reports that its desktop surface is ready.
- `desktop.shutdown`: request an orderly desktop shutdown.
- `state.snapshot`: exchange current windows, monitors, focus, and launches.
- `bridge.ping`: verify liveness.

### Windows application control

- `app.list`: return allow-listed applications.
- `app.launch`: launch an application by registered identifier and arguments.
- `window.created`: report a native window eligible for integration.
- `window.updated`: report title, bounds, state, monitor, or DPI changes.
- `window.focus`: request focus for a known window identifier.
- `window.close`: request an orderly close for a known window identifier.

The host owns the application catalog. KDE receives stable identifiers, names,
categories, and display metadata for its Start Menu; executable paths and
launch policy remain host-side.

The Linux side represents an accepted native window as a foreign surface. Its
identity is immutable for the surface lifetime, host metadata describes its
size and monitor, frames are validated against their declared dimensions, and
pointer events carry the host window ID back to Windows. The Linux surface
never receives an arbitrary HWND or executable path.

The protocol adapter emits and consumes typed window lifecycle events around
that surface model. A future KDE/Wayland client can use the same events to
create its foreign surface, while pointer requests return through the host
with the stable window ID.

The `app.list` response combines host-owned Windows entries with Linux desktop
entries using the same metadata schema. Each entry identifies its `origin` as
`windows` or `linux`; KDE treats both as first-class menu entities and sends
the stable ID back to the bridge when launching. A catalog entry never needs
to expose its executable path to KDE.

Raw process creation, arbitrary executable paths, and unrestricted shell
commands are not protocol operations.

## Privilege model

Linux administration may use `sudo` inside Ubuntu, but sudo input and output
are never forwarded as an arbitrary Windows command channel. The elevated host
broker exposes only operations with an explicit policy. Ordinary operations
use the normal bridge capability; privileged host operations require a separate
negotiated capability and are logged by the host.

The first privileged operation is intentionally narrow: restarting the host
bridge. Adding another privileged operation requires a typed payload, an
allow-list entry, a failure policy, and a test that rejects shell forwarding.

### Shared integration

Clipboard, file exchange, audio, and notifications are separate capability
families. Each must be negotiated explicitly and can be disabled independently
when it is not available or trusted.

Identity uses the same rule: `identity.session` may return approved session
metadata, and `identity.sso-request` may return an approval handle. Passwords,
password prompts, and raw Windows access tokens are never bridge payloads.

## Lifecycle

1. Windows starts the Host Bridge after authentication.
2. Host Bridge starts or attaches to the Linux environment.
3. Desktop Bridge connects and completes `hello` and `authenticate`.
4. Both sides exchange `state.snapshot` before accepting interactive events.
5. Desktop Bridge sends `desktop.ready` after KDE is usable.
6. Host Bridge monitors heartbeats and process ownership.
7. On disconnect, Host Bridge stops accepting new integration requests,
   preserves native Windows applications, and enters recovery handling.

The prototype models these phases as `disconnected`, `connected`,
`authenticated`, `ready`, `recovering`, and `stopped`. Interactive operations
are permitted only in `ready`; reconnecting requires recovery followed by a
new connection, authentication, and readiness transition.

## Recovery rules

- A failed Desktop Bridge must not terminate native Windows applications.
- A failed Host Bridge must not allow stale Linux requests to relaunch apps.
- Reconnect requires a new authentication nonce and state snapshot.
- Duplicate requests must be safe to reject or safely repeat.
- The host must expose a recovery action that restores a usable Windows shell.

## First vertical slice

The first implementation should prove only this path:

1. Authenticated local connection.
2. Version and capability negotiation.
3. Host allow-list returns one harmless test application.
4. KDE requests that application by identifier.
5. Host reports process and window lifecycle events.
6. Disconnect stops new requests and records a recoverable error.

Window embedding, clipboard, and shell replacement come after this slice is
tested on a disposable environment.