import pytest
from agp import AGPClient


def pytest_addoption(parser):
    parser.addoption("--base-url", default="http://localhost:8099",
                     help="Base URL of the AGP server under test")


@pytest.fixture(scope="session")
def client(request):
    url = request.config.getoption("--base-url")
    with AGPClient(url) as c:
        yield c
