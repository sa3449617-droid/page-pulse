"""Page Pulse — FastAPI Application.

Exposes:
    GET  /       — serves the frontend HTML page
    POST /audit — audits a URL and returns a JSON report
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

from parser import audit_url, AuditError, InvalidURLError, TimeoutError, NonHTMLError, FetchError

app = FastAPI(
    title="Page Pulse",
    description="Audit any URL — HTTP status, response time, meta data, and more.",
    version="1.0.0",
)


class AuditRequest(BaseModel):
    url: str


class AuditResponse(BaseModel):
    url: str
    status_code: int
    response_time_ms: int
    page_title: str | None = None
    meta_description: str | None = None
    h1_count: int
    images_missing_alt: int
    word_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend HTML page."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>Page Pulse</h1><p>Frontend not found.</p>",
        status_code=200,
    )


@app.post(
    "/audit",
    response_model=AuditResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def audit_endpoint(request: AuditRequest, http_request: Request):
    """Audit a URL and return a structured JSON report.

    Accepts a JSON body with a `url` field. Returns the audit report
    or a descriptive error.
    """
    try:
        report = await audit_url(request.url)
        return AuditResponse(**report)
    except InvalidURLError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_URL", "detail": str(e)},
        )
    except TimeoutError as e:
        return JSONResponse(
            status_code=504,
            content={"error": "TIMEOUT", "detail": str(e)},
        )
    except NonHTMLError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "NON_HTML_RESPONSE", "detail": str(e)},
        )
    except FetchError as e:
        return JSONResponse(
            status_code=502,
            content={"error": "FETCH_ERROR", "detail": str(e)},
        )
    except AuditError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "AUDIT_ERROR", "detail": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
