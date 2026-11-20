"""Domain model, one module per bounded context (ADR-0003).

Rules: no framework, database driver or HTTP client imports here; context
modules do not import each other and exchange identifiers and values only.
"""
