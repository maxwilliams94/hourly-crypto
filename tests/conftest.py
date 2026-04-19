"""
Shared pytest configuration and fixtures.

Sets up mocks for all external integrations (Azure, Cosmos DB, Key Vault,
Coinbase, Kraken) before any src modules are imported.
"""

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Inject environment variables required by src/repo.py at import time
# ---------------------------------------------------------------------------
os.environ.setdefault("ACCOUNT_URI", "https://mock-cosmos.documents.azure.com:443/")
os.environ.setdefault("ACCOUNT_KEY", "mock-key==")
os.environ.setdefault("DATABASE_NAME", "mock-db")
os.environ.setdefault("DRY", "true")

# ---------------------------------------------------------------------------
# Mock third-party packages that may not be installed during testing
# ---------------------------------------------------------------------------
_mock = MagicMock()
for _mod in ["jwt", "requests"]:
    sys.modules[_mod] = _mock

# ---------------------------------------------------------------------------
# Mock azure SDK packages so they don't need to be importable at test time
# ---------------------------------------------------------------------------
_azure_mock = MagicMock()
for _mod in [
    "azure",
    "azure.functions",
    "azure.cosmos",
    "azure.cosmos.exceptions",
    "azure.keyvault",
    "azure.keyvault.secrets",
    "azure.identity",
]:
    sys.modules[_mod] = _azure_mock

# ---------------------------------------------------------------------------
# Add the project root to sys.path so `import src.xxx` works
# ---------------------------------------------------------------------------
_project_root = os.path.dirname(os.path.dirname(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
