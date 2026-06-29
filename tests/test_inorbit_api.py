import pytest
import httpx
from pytest_httpx import HTTPXMock
from inorbit_edge_executor.inorbit import InOrbitAPI


def test_base_url_trailing_slash_stripped():
    """A trailing slash (as produced by str(pydantic.HttpUrl)) must not be kept."""
    assert InOrbitAPI(base_url="https://api.inorbit.ai/")._base_url == "https://api.inorbit.ai"
    assert InOrbitAPI(base_url="https://api.inorbit.ai")._base_url == "https://api.inorbit.ai"


@pytest.mark.asyncio
async def test_request_url_has_no_double_slash(httpx_mock: HTTPXMock):
    """Joining base_url + path must not produce '//' even with a trailing-slash base_url."""
    captured = {}

    def capture(request: httpx.Request):
        captured["url"] = str(request.url)
        return httpx.Response(status_code=200, json={})

    httpx_mock.add_callback(capture, is_reusable=True)

    api = InOrbitAPI(base_url="https://api.inorbit.ai/", api_key="secret")
    await api.post("robots/door-rs-1/actions", {"actionId": "open"})

    assert captured["url"] == "https://api.inorbit.ai/robots/door-rs-1/actions"
    assert "//robots" not in captured["url"]
