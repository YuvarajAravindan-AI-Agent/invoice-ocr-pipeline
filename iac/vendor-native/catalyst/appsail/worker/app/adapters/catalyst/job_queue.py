"""ExtractionQueue implemented against Catalyst Job Scheduling.

Grounded against the actual installed zcatalyst-sdk==1.1.0 source
(zcatalyst_sdk/job_scheduling/{__init__.py,_job.py,_types.py}), not
docs or web search — those led to a wrong method name
(`job_scheduling.jobpool(...)`, which doesn't exist) that only surfaced
as a real AttributeError once deployed and tested via /debug. Verified
facts from the SDK source:
  - Jobs are submitted via `job_scheduling.JOB.submit_job(job_meta)`,
    not a `.jobpool(name).submit_job(...)` chain.
  - The AppSail target field is `target_id` (the service's numeric ID,
    e.g. 68186000000015038) — there is no `target_name` field in the
    ICatalystAppSailJob TypedDict, despite docs suggesting one exists.
  - `job_config`'s retry-count field is spelled `number_of_retires`
    (sic) in the SDK's own TypedDict, not `number_of_retries`.
  - `jobpool_name` goes directly in job_meta, not through a separate
    jobpool-lookup call.

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
    def __init__(self, catalyst_app) -> None:
        # catalyst_app must come from a per-request zcatalyst_sdk.initialize(req=...)
        # call — see object_store.py's module docstring for why.
        self._job_scheduling = catalyst_app.job_scheduling()
        # Job Pool names are alphanumeric only (no hyphens/underscores) —
        # confirmed by the console's own validation, not assumed. Pool
        # created manually in the console as "invoiceextractionjobs",
        # type AppSail — there's no CLI/SDK call in this codebase that
        # creates it, so if this pool is ever deleted it must be
        # recreated by hand before this adapter will work again.
        self._jobpool_name = "invoiceextractionjobs"

    def enqueue(self, invoice_id: UUID) -> None:
        # WORKER_APPSAIL_ID is read here, not in __init__ — the worker
        # service constructs this same adapter (its ProcessExtractionJobUseCase
        # needs an ExtractionQueue port) but never calls enqueue(), and
        # doesn't have this env var set (only the api service does, see
        # README). Reading it eagerly in __init__ crashed every /process
        # request with a KeyError before this fix, confirmed via the
        # worker's own application logs.
        worker_target_id = os.environ["WORKER_APPSAIL_ID"]
        self._job_scheduling.JOB.submit_job(
            {
                # job_name has a hard 20-char limit and must be
                # alphanumeric/underscore only (both confirmed via real
                # CatalystAPIErrors, not docs — no hyphens allowed; the
                # full invoice_id doesn't fit either, it's carried in
                # request_body instead, this is just a human-readable
                # label).
                "job_name": f"inv{invoice_id.hex[:12]}",
                "jobpool_name": self._jobpool_name,
                "target_type": "AppSail",
                "target_id": worker_target_id,
                "request_method": "POST",
                "url": "/process",
                "headers": {"Content-Type": "application/json"},
                "request_body": json.dumps({"invoice_id": str(invoice_id)}),
                "job_config": {
                    # Low retry count on purpose — see module docstring.
                    # Covers transient delivery failure (e.g. the worker
                    # container is mid-restart), not extraction failure.
                    "number_of_retires": 2,  # sic — matches the SDK's own (typo'd) field name
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
