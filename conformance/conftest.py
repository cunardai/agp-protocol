"""
Pytest configuration for AGP conformance suite.

Pass the server URL via --base-url (default: http://localhost:8099).
Each test module receives a fresh AGPClient fixture.
"""
import pytest
import requests

from client import AGPClient


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        default="http://localhost:8099",
        help="Base URL of the AGP server under test",
    )


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session", autouse=True)
def check_server(base_url):
    """Abort early if server is unreachable."""
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:
        pytest.exit(f"AGP server not reachable at {base_url}: {e}", returncode=1)


@pytest.fixture
def c(base_url) -> AGPClient:
    return AGPClient(base_url)
