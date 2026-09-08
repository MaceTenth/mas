# Recovery lab

This repository starts empty on purpose. Demo 6 asks a deterministic fleet of
unreliable workers to produce artifacts while the MAS environment injects:

- a dead orchestrator lease with partial work left in its old compartment;
- a confident but incorrect result;
- a worker process crash;
- a worker that exceeds its time budget;
- a healthy worker that runs longer than the lease while heartbeats renew it;
- an irrecoverable item that must trip the circuit breaker.

The first worker dynamically creates the rest of the board. The final observer
reads `.mas/board.db` and writes `result/recovery.md`, proving each recovery
claim from the event log rather than from a worker's narration.
