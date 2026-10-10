# Production Change Approval Policy

## Actions allowed without approval

The agent may perform the following read-only actions automatically:

- Read metrics, logs, traces, deployment history, and runbooks.
- Create an incident report and a remediation plan.
- Run tests in a local or staging environment.
- Recommend a rollback, but do not perform production rollback automatically.

## Actions requiring human approval

The agent must request human approval before performing:

- Production deployment or rollback.
- Changing production configuration.
- Restarting a production service.
- Scaling production infrastructure.
- Deleting, modifying, or migrating production data.
- Disabling monitoring, alerts, or safety controls.

## Forbidden actions

The agent must never:

- Delete a production database.
- Disable audit logging.
- Access credentials, secrets, or customer personal data.
- Bypass approval requirements.
- Execute commands outside its approved tool list.

## Approval record

Every approval request must include:

- Incident ID and severity.
- Expected customer impact.
- Evidence supporting the proposed action.
- Risk level and rollback plan.
- Name and time of the human approver.