import os
import pytest

# Set required env vars before importing anything from api
os.environ.setdefault("PROXMOX_TOKEN_VALUE", "test-token")
os.environ.setdefault("TRUENAS_API_KEY", "test-key")
os.environ.setdefault("POSTGRES_DSN", "postgresql://user:pass@localhost/testdb")
os.environ.setdefault("PROXLAB_API_TOKEN", "test-api-token")
