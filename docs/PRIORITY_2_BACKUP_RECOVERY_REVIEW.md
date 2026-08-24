# Reflection Space — Priority 2 Backup & Recovery Review

## Scope

This review covers PostgreSQL recovery, Qdrant recovery, deployment rollback, and the privacy implications of backups.

## Current position

### PostgreSQL

Reflection Space does not operate its own backup job. PostgreSQL is hosted by Neon, and the repository's operator runbook records the current pilot configuration as Neon Free with a rolling 6-hour restore history. The runbook also records that no manual snapshots currently exist and that longer protection requires a higher plan and/or another backup strategy.

### Qdrant

Qdrant is not the system of record. PostgreSQL remains authoritative. Qdrant contains the semantic-search index and can be rebuilt from PostgreSQL. Loss of Qdrant therefore should not cause permanent loss of case records.

### Application rollback

The application is deployed from GitHub to Streamlit Community Cloud. A bad application deployment can therefore be rolled back by reverting the relevant Git commit and allowing the platform to redeploy.

## Recovery objectives

For permanent production, the following must be explicitly defined and tested:

- RPO (Recovery Point Objective): how much recently created data the organisation is willing to lose after a database failure.
- RTO (Recovery Time Objective): how long the service may be unavailable before recovery is considered unacceptable.

The current 6-hour database restore window may be adequate for a limited pilot, but it should not be treated as a permanent production recovery policy without explicit risk acceptance.

## Privacy implications

A database restore can restore information that users subsequently deleted. This is normal backup behaviour, but it must be reflected in the organisation's privacy/deletion policy.

The application currently uses a 48-hour deletion window before permanent purge. This is separate from provider backup retention. Deleting a case from the live database does not guarantee immediate removal from historical database backups.

## Required production controls

1. Establish a recovery window materially longer than the current 6 hours before permanent production use, either through a suitable Neon plan or an independently controlled backup strategy.
2. Define and document RPO and RTO.
3. Perform an actual restore test rather than relying on the provider's stated capability.
4. Verify that restored data includes the expected PostgreSQL tables and relationships.
5. Verify that Qdrant can be rebuilt from a restored PostgreSQL database.
6. Test the application after restoration, including login, case retrieval, reflection generation, semantic search, deletion and audit logging.
7. Document who is authorised to perform restoration and who can access restored sensitive data.
8. Document how a restore interacts with deletion requests and privacy obligations.
9. Keep application rollback and database rollback procedures separate: reverting application code does not undo database changes.
10. Establish a periodic recovery test schedule before permanent production.

## Current assessment

### Pilot

CONDITIONAL PASS. The documented 6-hour Neon restore history can be accepted only as an explicitly acknowledged pilot limitation.

### Permanent production

NOT YET READY. Longer recovery protection and a successful restore drill are required before signing off permanent production.

## Next action

Do not add product features yet. Establish the target RPO/RTO, select the database recovery tier/strategy, perform a restore drill, and record the result. Then proceed to Priority 3 adversarial privacy testing.
