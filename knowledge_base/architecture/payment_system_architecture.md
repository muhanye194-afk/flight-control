# Payment System Architecture

## Request path

A customer payment request follows this path:

1. Client sends `POST /payments`.
2. API Gateway routes the request to Payment Service.
3. Payment Service validates the payment and creates a payment record.
4. Payment Service acquires a database connection.
5. Database stores the payment record.
6. Payment Service calls the external payment provider.
7. Payment Service returns the final payment result to the client.

## Service dependencies

| Service | Depends on | Failure impact |
|---|---|---|
| API Gateway | Payment Service | Customers cannot start payments |
| Payment Service | Database, External Payment Provider | Payments may fail or become slow |
| Database | Connection Pool | Payment Service cannot store or read payment data |
| External Payment Provider | Internet connection | Payment authorization may time out |

## Critical services

- Payment Service is customer-facing and is classified as P1.
- Database connection pool exhaustion can affect all payment requests.
- External Payment Provider failures should not cause database connection exhaustion.

## Safe recovery sequence

1. Confirm whether the failure is in Payment Service, Database, or External Provider.
2. Limit traffic or roll back the latest Payment Service version if customer impact is high.
3. Verify database connection count before restarting any service.
4. Do not restart the database without human approval.
5. Verify payment success rate and latency after remediation.