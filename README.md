# Page Pulse

A lightweight web tool that audits any URL and returns a structured report: HTTP status, response time, page title, meta description, heading count, image accessibility, and word count.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sa3449617-droid/page-pulse)

Built for the **Digital Heroes Internship Programme** — Software Development (SDE) qualification task.

---

## One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sa3449617-droid/page-pulse)

1. Click the button above
2. Connect your GitHub account (if not already connected)
3. Render auto-detects `render.yaml` — just confirm and deploy
4. Your live URL will be: `https://page-pulse.onrender.com`

**Alternative — manual deploy:**
- **Render:** New Web Service → connect GitHub repo → start command `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Railway:** Deploy from GitHub — auto-detects Python/FastAPI
- **Docker:** Build the included `Dockerfile` and deploy anywhere

---

## Setup

### Prerequisites
- Python 3.11+
- pip

### Install

```bash
git clone https://github.com/sa3449617-droid/page-pulse
cd page-pulse

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
uvicorn main:app --reload
```

Open http://localhost:8000 in your browser. Enter a URL and click **Audit**.

### Run Tests

```bash
pytest tests/ -v
```

---

## API Contract

### `POST /audit`

Audit a URL and receive a structured JSON report.

**Request Body:**

```json
{
  "url": "https://example.com"
}
```

**Success Response (200):**

```json
{
  "url": "https://example.com",
  "status_code": 200,
  "response_time_ms": 134,
  "page_title": "Example Domain",
  "meta_description": null,
  "h1_count": 1,
  "images_missing_alt": 0,
  "word_count": 28
}
```

| Field | Type | Description |
|---|---|---|
| `url` | string | Normalised URL (after redirects) |
| `status_code` | int | HTTP response status code |
| `response_time_ms` | int | Total response time in milliseconds |
| `page_title` | string | Content of the `<title>` tag, or `null` if absent |
| `meta_description` | string | Content of `<meta name="description">`, or `null` |
| `h1_count` | int | Number of `<h1>` elements on the page |
| `images_missing_alt` | int | Count of `<img>` tags without a meaningful `alt` attribute |
| `word_count` | int | Approximate number of visible words on the page |

**Error Responses:**

| Status | Error Key | When |
|---|---|---|
| 400 | `INVALID_URL` | The provided URL is empty or syntactically invalid |
| 400 | `NON_HTML_RESPONSE` | The URL returned non-HTML content (PDF, image, etc.) |
| 502 | `FETCH_ERROR` | The request failed (DNS lookup failure, connection refused, etc.) |
| 504 | `TIMEOUT` | The request took longer than 15 seconds |

All error responses follow this shape:

```json
{
  "error": "ERROR_KEY",
  "detail": "Human-readable explanation of what went wrong."
}
```

### `GET /`

Serves the frontend HTML page with an input field and rendered report.

---

## Design Decisions

### 1. Async HTTP with httpx instead of requests

The tool makes at least one network call per audit. Using `httpx.AsyncClient` lets the server handle concurrent audits without blocking the event loop — important because the typical use case involves a user testing several URLs in quick succession. The `requests` library would block the server process on each call, which harms throughput even under moderate load.

**Trade-off:** Async code is slightly more complex to write and test (requires `pytest-asyncio`). For a single-endpoint tool like this, the ergonomic cost is small, and the throughput benefit is immediate.

### 2. BeautifulSoup over regex for HTML parsing

HTML is notoriously irregular — tags nest, attributes are optional, self-closing tags vary, and real-world pages routinely serve malformed markup. A regex-based approach would require maintaining a fragile set of patterns that break on the next edge case. BeautifulSoup (with the `html.parser` backend) builds a proper parse tree and handles every HTML variant we have tested, including missing `alt` attributes, uppercase tags, and empty `<h1>` elements.

**Trade-off:** BeautifulSoup is slower than a tightly written regex for a single, simple extraction. But correctness matters more than microseconds for an audit tool that will be called at most a few times per user session.

### 3. Explicit exception hierarchy for error reporting

Rather than returning a generic `{"error": "something went wrong"}`, the parser defines four distinct exception classes (`InvalidURLError`, `TimeoutError`, `NonHTMLError`, `FetchError`), each mapped to a specific HTTP status code in the API layer. This makes three things easier:

- **Client code** can handle each failure mode differently (e.g. show the user a different message for a timeout vs. an invalid URL).
- **Testing** is cleaner — we can assert that a specific exception is raised with `pytest.raises`.
- **Maintenance** — adding a new error mode means adding one exception class and one `except` clause, without touching error-handling logic elsewhere.

**Trade-off:** More code up front (four exception classes instead of one). For a small tool this is fine; for a larger service the pattern scales well because each error class carries its own context.

---

## AI Use Disclosure

I used Claude (via the Clusy notebook agent) to scaffold the initial project structure, generate the parser logic, API routes, frontend HTML, test suite, and this README. After each generation I reviewed the output and made the following changes:

- **Patched URL validation** to handle `localhost:port` and IP addresses correctly (the initial version rejected `http://localhost:8000` because it checked for a dot in the full netloc including the port).
- **Replaced unstable test targets** — the initial tests used `httpbin.org` which returned 503/504 errors; I switched all integration tests to `example.com` and `python.org` which are stable.
- **Refined error messages** to be more specific and user-facing rather than exposing internal exception text.
- **Made all design decisions myself** — the choice of async httpx, BeautifulSoup, and the exception hierarchy are my own reasoning based on the trade-offs described above.

---

## Assumptions

1. **Role selection:** The task kit contains 16 roles. I completed Role 03 (Software Development / SDE) as it aligns with my application.
2. **"Approximate word count":** I strip `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, and `<aside>` tags before counting words, since these are not visible page content. The count is approximate by design.
3. **"Images missing alt text":** I count `<img>` tags where the `alt` attribute is absent OR empty/whitespace-only. An `alt=""` (intentionally empty for decorative images) is counted as missing since the brief does not distinguish decorative from informative images.
4. **Timeout threshold:** I set a 15-second timeout for HTTP requests. This is generous enough for slow pages but prevents the server from hanging indefinitely.
5. **Non-HTML detection:** I check the `Content-Type` header for `text/html` or `application/xhtml`. Pages served without a proper Content-Type but containing HTML will be rejected — this is a deliberate strictness choice to avoid parsing binary content.

---

## Self-Critique: What I'd Change With Another Day

If I had one more day on this task, I would:

1. **Add concurrent multi-URL auditing** — the backend currently audits one URL per request. With async httpx already in place, supporting a batch endpoint (`POST /audit/batch` accepting an array of URLs) would be ~20 lines of code and let users audit multiple pages in parallel. This is the most practical improvement since the async foundation is already laid.

2. **Add a simple response-size check** — some pages return very large HTML (500KB+). I'd add a soft warning in the report when the page exceeds 1MB, letting the user know the word count might be approximate due to truncation. The `MAX_BODY_BYTES` constant is already defined in `parser.py` but not used — I'd wire it in.

3. **Include a "last fetched" timestamp in the report** — useful for users who audit the same URL multiple times to track changes over time. This is a single field addition.

These are small, contained changes that improve the tool's utility without adding architectural complexity.

---

## Project Structure

```
page-pulse/
├── Dockerfile          # Containerised deployment option
├── render.yaml         # Render Blueprint (one-click deploy)
├── __init__.py
├── main.py             # FastAPI application (routes, error handling)
├── parser.py           # Core URL audit logic (validation, fetching, parsing)
├── requirements.txt    # Python dependencies
├── .gitignore
├── static/
│   └── index.html      # Frontend single-page app
├── tests/
│   ├── __init__.py
│   └── test_parser.py  # 20 tests (unit + integration + error handling)
└── README.md
```

---

## Live Build Requirement

This tool was built for the **Digital Heroes Training Task**. The credit line is displayed in the footer of the frontend page.

Built for [Digital Heroes](https://digitalheroesco.com) Training Task.
