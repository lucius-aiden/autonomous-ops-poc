# AGENT-002 restart scenario research

AGENT-002 is not implemented or run. The existing reversible scale-to-zero
scenario is a genuine persistent fault, but its correct remediation is
`service.scale`, not restart. Using it for restart would conflate operational
correctness with the desired test result.

A technically defensible future scenario would require a real application-level
fault that leaves the deployment and pod present but makes the process unable to
serve readiness traffic, while Kubernetes does not automatically replace it.
The harness would need to inject that fault through a narrowly scoped,
reversible test mechanism inside the sandbox, verify the process remains
materially degraded, request `service.restart`, and remove/reset the injected
condition during cleanup. The mechanism must not be arbitrary shell access for
the agent and must expose ground truth only to the harness/evaluator.

No such mechanism is currently available in the existing provider/scenario
abstraction without adding an artificial failure or changing the application
itself. Therefore no restart scenario is claimed and no real AGENT-002 run was
performed.
