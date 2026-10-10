# Postmortem: Payment Connection Pool Outage

## Incident summary

On 2026-06-15, Payment Service success rate dropped from 99.9% to 61%.
Customers experienced payment failures and high latency for 18 minutes.

## Root cause

A new Payment Service release introduced a database session leak.
Database connections were not released when payment validation raised an exception.
The connection pool reached its limit and new payment requests timed out.

## Evidence observed

- Database active connections reached 500 / 500.
- Payment p95 latency increased above 4 seconds.
- Logs contained `connection pool exhausted`.
- The incident started five minutes after a new deployment.

## Actions taken

1. Traffic was shifted back to the previous stable Payment Service version.
2. Payment success rate recovered above 99%.
3. The session cleanup logic was fixed in a staging environment.
4. The fix was deployed through a canary release after human approval.

## Lessons learned

- Every database session must be released in success and exception paths.
- Connection-pool usage must be monitored with alerts below the hard limit.
- Deployment rollback must remain fast and require an auditable approval record.