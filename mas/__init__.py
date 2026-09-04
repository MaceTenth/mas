"""mas — the environment for multi-agent work.

Five boxes:  board (durable, leased)  ·  workers (disposable, in compartments)
             gate (verifies, never trusts)  ·  orchestrator (restartable, supervised)
             log + views (append-only truth, per-reader views)
"""
__version__ = "0.1.0"
