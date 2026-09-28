"""Business logic, one module per domain.

Services take an `AsyncSession`, call `flush()` but never `commit()`,
raise `giftmanager.core.errors.DomainError` subclasses and never import FastAPI.
"""
