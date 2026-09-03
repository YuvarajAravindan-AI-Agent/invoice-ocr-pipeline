"""ExtractionQueue implemented against Catalyst Job Scheduling.

Grounded against docs.catalyst.zoho.com/en/job-scheduling/help/
implementation/submit-jobs-using-jobs/ and
docs.catalyst.zoho.com/en/sdk/python/v1/job-scheduling/ (checked
2026-09-03).

IMPORTANT — this is a push queue, not a pull queue: submit_job with
target_type='AppSail' makes Catalyst issue an HTTP request directly to
the worker service. There is no SDK call that hands this adapter a
message to return from receive() — the "receive" happens when the
worker's own HTTP handler gets the request. See appsail/worker/main.py,
which constructs an ExtractionJobMessage from the request body and
calls ProcessExtractionJobUseCase.execute(message=...) directly,
bypassing receive() entirely (see the docstring on that use case for
why both delivery models are supported).

ack()/nack() are no-ops here, deliberately: our own domain status
(EXTRACTED/NEEDS_REVIEW/FAILED, tracked on the Invoice record) is the
real source of truth for whether a job succeeded, and Catalyst's
job_config retries are configured narrowly (see enqueue()) to only
cover delivery failures, not extraction failures — retrying a failed
extraction automatically isn't implemented yet and would need its own
decision (e.g. a distinct "requeue for retry" use case), not something
to bolt onto ack/nack silently.
"""

from __future__ import annotations

import json
import os
from uuid import UUID

from app.application.ports import ExtractionJobMessage
from app.domain.entities import Invoice  # noqa: F401 — kept for readers tracing the port's shape


class CatalystJobQueue:
    def __init__(self) -> None:
        import zcatalyst_sdk

        app = zcatalyst_sdk.initialize()
        job_scheduling = app.job_scheduling()
        self._jobpool = job_scheduling.jobpool(jobpool_name="invoice-extraction-jobs")
        self._worker_target_name = os.environ["CATALYST_WORKER_APPSAIL_NAME"]

    def enqueue(self, invoice_id: UUID) -> None:
        self._jobpool.submit_job(
            {
                "job_name": f"extract-invoice-{invoice_id}",
                "target_type": "AppSail",
                "target_name": self._worker_target_name,
                "request_method": "POST",
                "url": "/process",
                "headers": {"Content-Type": "application/json"},
                "request_body": json.dumps({"invoice_id": str(invoice_id)}),
                "job_config": {
                    # Low retry count on purpose — see module docstring.
                    # Covers transient delivery failure (e.g. the worker
                    # container is mid-restart), not extraction failure.
                    "number_of_retries": 2,
                    "retry_interval": 60 * 1000,
                },
            }
        )

    def receive(self) -> ExtractionJobMessage | None:
        raise NotImplementedError(
            "CatalystJobQueue is push-based — the worker's HTTP handler receives "
            "jobs directly, it never polls this method. See module docstring."
        )

    def ack(self, message: ExtractionJobMessage) -> None:
        pass

    def nack(self, message: ExtractionJobMessage) -> None:
        pass
