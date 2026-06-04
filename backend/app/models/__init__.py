"""Import all SQLAlchemy models so every relationship string-reference is resolved.

SQLAlchemy resolves relationship("ClassName") lazily via the mapper registry.
If a model is used (queried) before all referenced classes are imported, the
mapper raises InvalidRequestError: '...' failed to locate a name.

Importing this package guarantees every model is registered before any
query runs — required by Celery workers and anywhere models are used.
"""

from app.models.user import User
from app.models.target import Target
from app.models.legal import NDAAcceptance, AuditLog
from app.models.scan import Scan

__all__ = ["User", "Target", "NDAAcceptance", "AuditLog", "Scan"]
