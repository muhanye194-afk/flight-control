# APAC Video Edge Routing Incident Runbook

## Scope

Use this runbook when live or on-demand playback fails in one region,
while global playback remains mostly healthy.

## Confirming signals

- APAC playback startup success rate is significantly lower than global success rate.
- APAC edge p95 latency rises above the service threshold.
- Logs contain `route_not_found`, invalid origin, or increasing fallback rate.
- Distributed traces show edge-routing-service selecting an origin before failure.
- A recent release modified regional routing weights, origin configuration, or traffic policy.

## Investigation sequence

1. Compare APAC playback startup success rate with the global rate.
2. Verify whether the origin cluster is healthy before treating it as the root cause.
3. Inspect the selected origin in edge-routing-service logs and traces.
4. Compare the active routing configuration with the last known stable version.
5. Identify whether a recent deployment changed regional routing weights or origin mappings.

## Root-cause indicators

A routing misconfiguration is likely when all of the following are true:

- The failure is concentrated in one region.
- The selected origin returns `route_not_found` or has no valid live route.
- The global service and other origins remain healthy.
- The issue began shortly after a routing configuration release.

## Safe remediation

- Do not change production routing automatically.
- Request human approval before rolling back routing configuration.
- Restore the previous stable APAC origin mapping.
- Validate the corrected configuration in staging.
- Use a small regional canary before full rollout.

## Verification

After remediation, verify:

- APAC playback startup success rate is at least 95 percent.
- APAC edge p95 latency is below 800ms.
- `route_not_found` errors stop appearing.
- APAC fallback rate returns to its normal baseline.