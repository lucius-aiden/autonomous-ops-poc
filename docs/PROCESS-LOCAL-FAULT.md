# Process-local wedge scenario

The dedicated `process-state-demo` workload models a worker/runtime wedge in
process-local memory. The privileged scenario harness reaches a localhost-only
test endpoint through `kubectl exec`; the autonomous tool registry has no exec,
injection, or reset capability.

The endpoint flips an in-memory flag. While wedged, `/health` returns 503 and
`/api/data` returns 500, while the process and pod remain running. There are no
Kubernetes readiness/liveness probes by design, so desired and ready replicas
remain `1`; the application-level signal is the real HTTP response and error
log. A replacement process starts with the module initialized cleanly, so the
fault does not reinject after `service.restart`.

The first deterministic validation exposed a stale-pod observation in the
ad-hoc runner after rollout restart; the deployment itself replaced the pod
successfully. The harness now resolves the current pod for each localhost
check, making cleanup idempotent across pod identity changes.

This is representative of a stuck worker or poisoned in-memory runtime state,
but it is intentionally a small test-only service rather than a modification
to the upstream OpenTelemetry Demo image. No autonomous experiment has been
run against it.
