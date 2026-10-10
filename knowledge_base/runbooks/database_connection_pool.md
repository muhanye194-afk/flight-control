# Database Connection Pool Exhaustion Runbook

## When to use

Use this runbook when application logs contain `connection pool exhausted`,
or when active database connections reach the configured limit.

## Confirming signals

- Database active connections are close to or equal to the connection limit.
- Payment latency increases sharply.
- Logs contain `connection pool exhausted` or `unable to acquire database connection`.
- A recent deployment changed database session or connection handling.

## Safe first actions

1. Stop or limit traffic to the newly deployed service version.
2. Roll back to the previous stable version if error rate is customer-impacting.
3. Do not restart the database without human approval.

## Root-cause investigation

1. Check whether every request closes its database session.
2. Check whether exception paths release database connections.
3. Compare the current deployment with the previous stable version.
4. Verify that retry logic is not creating uncontrolled concurrent requests.

## Verification after remediation

- Payment success rate returns above 99%.
- Database active connections remain below 70% of the configured limit.
- No new `connection pool exhausted` logs appear for 10 minutes.

## Escalation policy

Production deployment, database restart, and configuration changes require human approval.