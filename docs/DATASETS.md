# Dataset and replay design

Phase 2 does not download or commit a public dataset. The acted-on environment remains
the local kind/OpenTelemetry Demo cluster; actionable faults must be injected by our
harness so their ground truth is known.

## Candidates

- **Los Alamos National Laboratory cyber datasets:** enterprise authentication and
  unified host/network events, including known red-team activity. Relevant for future
  background distributions, but large and subject to dataset-specific access and usage
  conditions. No source corpus is redistributed here.
- **Loghub:** public system-log collections including HDFS anomaly data. A small curated
  sample could provide replayable anomaly shapes after checking its individual license
  and attribution requirements. No sample is selected for V1.

Future replay may expose `Scenario(id, category, setup, inject, expected_observations,
allowed_remediations, success_condition, cleanup)`. Replay data informs observations only;
it never implies a historical incident happened in our sandbox or authorizes an action.
