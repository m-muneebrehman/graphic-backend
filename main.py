"""
Grabpic — Intelligent Identity & Retrieval Engine
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import close_pool, init_db
from app.models import HealthResponse
from app.routes import auth, images, ingest


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations on startup; close pool on shutdown."""
    print("[grabpic] Initialising database …")
    try:
        init_db()
        print("[grabpic] Ready.")
    except Exception as e:
        # Don't crash the server if DB is unreachable at boot.
        # The landing page and /health will still work; API routes
        # will return 500 with a clear message until DB becomes available.
        print(f"[grabpic] WARNING: DB init failed — {e}")
        print("[grabpic] Server starting without DB. Set DATABASE_URL env var.")
    yield
    print("[grabpic] Shutting down …")
    close_pool()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Grabpic API",
    description=(
        "Intelligent Identity & Retrieval Engine. "
        "Uses facial recognition to group event photos and provides "
        "a **Selfie-as-a-Key** retrieval system."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(ingest.router)
app.include_router(auth.router)
app.include_router(images.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"], summary="Health check")
def health():
    """Return service health status."""
    return HealthResponse()


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Grabpic — Intelligent Identity & Retrieval Engine</title>
  <meta name="description" content="Grabpic: AI-powered facial recognition API for large-scale event photography. Selfie-as-a-Key retrieval system." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: #080c14;
      --surface: #0d1424;
      --surface2: #111827;
      --border: rgba(99,179,237,0.12);
      --accent: #63b3ed;
      --accent2: #9f7aea;
      --accent3: #68d391;
      --accent4: #f6ad55;
      --text: #e2e8f0;
      --muted: #718096;
      --code-bg: #0a0f1a;
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
    }

    /* ── Animated background ── */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      background:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(99,179,237,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(159,122,234,0.06) 0%, transparent 60%);
      pointer-events: none;
      z-index: 0;
    }

    .wrap { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 0 24px; }

    /* ── Nav ── */
    nav {
      display: flex; align-items: center; justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px);
      position: sticky; top: 0; z-index: 100;
      background: rgba(8,12,20,0.8);
    }
    .logo { font-size: 1.2rem; font-weight: 700; letter-spacing: -0.5px; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 8px; }
    .nav-links a {
      color: var(--muted); text-decoration: none; font-size: 0.85rem;
      padding: 6px 14px; border-radius: 6px;
      border: 1px solid transparent;
      transition: all 0.2s;
    }
    .nav-links a:hover { color: var(--text); border-color: var(--border); }
    .nav-links a.btn {
      background: var(--accent); color: #000; font-weight: 600;
      border-color: var(--accent);
    }
    .nav-links a.btn:hover { opacity: 0.85; }

    /* ── Hero ── */
    .hero {
      text-align: center;
      padding: 96px 0 72px;
    }
    .badge {
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba(99,179,237,0.1);
      border: 1px solid rgba(99,179,237,0.25);
      border-radius: 999px;
      padding: 6px 16px;
      font-size: 0.78rem; font-weight: 500; color: var(--accent);
      margin-bottom: 28px;
      animation: fadeUp 0.6s ease both;
    }
    .badge::before { content: '●'; font-size: 0.5rem; }

    h1 {
      font-size: clamp(2.4rem, 6vw, 4.2rem);
      font-weight: 800;
      letter-spacing: -2px;
      line-height: 1.05;
      animation: fadeUp 0.6s 0.1s ease both;
    }
    h1 .hl { color: var(--accent); }
    h1 .hl2 { color: var(--accent2); }

    .hero-sub {
      margin: 24px auto 0;
      max-width: 600px;
      color: var(--muted);
      font-size: 1.1rem;
      line-height: 1.65;
      animation: fadeUp 0.6s 0.2s ease both;
    }

    .hero-ctas {
      display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
      margin-top: 40px;
      animation: fadeUp 0.6s 0.3s ease both;
    }
    .cta {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 12px 28px; border-radius: 10px;
      font-size: 0.95rem; font-weight: 600;
      text-decoration: none; transition: all 0.2s;
    }
    .cta-primary { background: var(--accent); color: #000; }
    .cta-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(99,179,237,0.3); }
    .cta-secondary {
      background: transparent; color: var(--text);
      border: 1px solid var(--border);
    }
    .cta-secondary:hover { border-color: var(--accent); color: var(--accent); }

    /* ── Stats bar ── */
    .stats {
      display: flex; justify-content: center; gap: 48px; flex-wrap: wrap;
      padding: 40px 0;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      margin: 72px 0;
      animation: fadeUp 0.6s 0.4s ease both;
    }
    .stat-item { text-align: center; }
    .stat-num { font-size: 2rem; font-weight: 800; color: var(--accent); }
    .stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }

    /* ── How it works ── */
    .section-label {
      text-align: center;
      font-size: 0.75rem; font-weight: 600; letter-spacing: 3px;
      text-transform: uppercase; color: var(--accent);
      margin-bottom: 16px;
    }
    h2 {
      text-align: center;
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 700; letter-spacing: -1px;
      margin-bottom: 48px;
    }

    .steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 96px; }
    .step {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 32px;
      position: relative;
      transition: border-color 0.2s, transform 0.2s;
    }
    .step:hover { border-color: rgba(99,179,237,0.3); transform: translateY(-4px); }
    .step-num {
      font-size: 0.7rem; font-weight: 700; letter-spacing: 2px;
      color: var(--accent); margin-bottom: 16px;
      text-transform: uppercase;
    }
    .step h3 { font-size: 1.1rem; font-weight: 600; margin-bottom: 10px; }
    .step p { color: var(--muted); font-size: 0.9rem; line-height: 1.6; }
    .step-icon {
      font-size: 2rem; margin-bottom: 20px;
      display: inline-block;
    }

    /* ── API Endpoints ── */
    .endpoints { display: flex; flex-direction: column; gap: 24px; margin-bottom: 96px; }
    .endpoint {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      transition: border-color 0.2s;
    }
    .endpoint:hover { border-color: rgba(99,179,237,0.25); }

    .ep-header {
      display: flex; align-items: center; gap: 16px;
      padding: 20px 28px;
      cursor: pointer;
      user-select: none;
    }
    .method {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem; font-weight: 700;
      padding: 4px 10px; border-radius: 6px;
      min-width: 52px; text-align: center;
    }
    .GET  { background: rgba(104,211,145,0.15); color: var(--accent3); }
    .POST { background: rgba(246,173,85,0.15);  color: var(--accent4); }

    .ep-path {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.9rem; color: var(--text); font-weight: 500;
    }
    .ep-desc { color: var(--muted); font-size: 0.85rem; margin-left: auto; }

    .ep-body { padding: 0 28px 28px; border-top: 1px solid var(--border); }
    .ep-body p { color: var(--muted); font-size: 0.9rem; line-height: 1.65; padding: 16px 0 20px; }

    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media(max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

    .box {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }
    .box-label {
      padding: 8px 14px;
      background: rgba(255,255,255,0.03);
      border-bottom: 1px solid var(--border);
      font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px;
      text-transform: uppercase; color: var(--muted);
    }
    pre {
      padding: 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      line-height: 1.7;
      overflow-x: auto;
      color: #a8d8ff;
    }
    .kw { color: #f6ad55; }
    .str { color: #68d391; }
    .cmt { color: #4a5568; font-style: italic; }
    .key { color: #63b3ed; }
    .val { color: #fc8181; }

    .params-table { width: 100%; border-collapse: collapse; margin: 8px 0; }
    .params-table th {
      text-align: left; font-size: 0.72rem; font-weight: 600;
      color: var(--muted); padding: 8px 12px;
      border-bottom: 1px solid var(--border);
      text-transform: uppercase; letter-spacing: 1px;
    }
    .params-table td {
      padding: 10px 12px; font-size: 0.83rem;
      border-bottom: 1px solid rgba(99,179,237,0.06);
      vertical-align: top;
    }
    .params-table td:first-child {
      font-family: 'JetBrains Mono', monospace;
      color: var(--accent); font-size: 0.8rem;
    }
    .params-table td:nth-child(2) { color: var(--accent2); }
    .tag-req {
      font-size: 0.65rem; background: rgba(252,129,129,0.15);
      color: #fc8181; padding: 2px 7px; border-radius: 4px;
      font-weight: 600; margin-left: 6px;
    }
    .tag-opt {
      font-size: 0.65rem; background: rgba(99,179,237,0.1);
      color: var(--accent); padding: 2px 7px; border-radius: 4px;
      font-weight: 600; margin-left: 6px;
    }

    /* ── Footer ── */
    footer {
      text-align: center; padding: 48px 0;
      border-top: 1px solid var(--border);
      color: var(--muted); font-size: 0.85rem;
    }
    footer a { color: var(--accent); text-decoration: none; }

    /* ── Animations ── */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>

<nav>
  <div class="logo">grab<span>pic</span></div>
  <div class="nav-links">
    <a href="#how-it-works">How it works</a>
    <a href="#api">API</a>
    <a href="/docs" class="btn">Try it live →</a>
  </div>
</nav>

<div class="wrap">

  <!-- ── Hero ── -->
  <section class="hero">
    <div class="badge">Powered by InsightFace · ArcFace 512-d · pgvector HNSW</div>
    <h1>
      Find every photo<br/>
      with your <span class="hl">face</span> as<br/>
      the <span class="hl2">key</span>
    </h1>
    <p class="hero-sub">
      Grabpic is an intelligent image retrieval engine for large-scale events.
      Upload event photos, then let attendees find every picture of themselves
      with a single selfie — no accounts, no tags, no manual work.
    </p>
    <div class="hero-ctas">
      <a href="/docs" class="cta cta-primary">Interactive API Docs →</a>
      <a href="#api" class="cta cta-secondary">View Endpoints ↓</a>
    </div>
  </section>

  <!-- ── Stats ── -->
  <div class="stats">
    <div class="stat-item">
      <div class="stat-num">512-d</div>
      <div class="stat-label">ArcFace Embeddings</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">HNSW</div>
      <div class="stat-label">Vector Index (pgvector)</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">&lt;500ms</div>
      <div class="stat-label">Selfie Auth Response</div>
    </div>
    <div class="stat-item">
      <div class="stat-num">∞</div>
      <div class="stat-label">Photos Supported</div>
    </div>
  </div>

  <!-- ── How it works ── -->
  <section id="how-it-works">
    <div class="section-label">Workflow</div>
    <h2>Three steps, zero friction</h2>
    <div class="steps">
      <div class="step">
        <div class="step-icon">📁</div>
        <div class="step-num">Step 01</div>
        <h3>Ingest Photos</h3>
        <p>Drop event photos into the storage directory and call <code style="color:var(--accent4);font-family:'JetBrains Mono',monospace">POST /api/v1/ingest</code>. Grabpic detects every face, generates embeddings, and assigns unique grab_ids automatically.</p>
      </div>
      <div class="step">
        <div class="step-icon">🤳</div>
        <div class="step-num">Step 02</div>
        <h3>Authenticate by Selfie</h3>
        <p>Upload a selfie to <code style="color:var(--accent4);font-family:'JetBrains Mono',monospace">POST /api/v1/auth/selfie</code>. The engine matches your face against the database using cosine similarity and returns your personal grab_id.</p>
      </div>
      <div class="step">
        <div class="step-icon">🖼️</div>
        <div class="step-num">Step 03</div>
        <h3>Retrieve Your Photos</h3>
        <p>Call <code style="color:var(--accent4);font-family:'JetBrains Mono',monospace">GET /api/v1/images/{grab_id}</code> with your grab_id to get every event photo featuring you, paginated, with exact bounding box coordinates.</p>
      </div>
    </div>
  </section>

  <!-- ── API Reference ── -->
  <section id="api">
    <div class="section-label">API Reference</div>
    <h2>Endpoints</h2>
    <div class="endpoints">

      <!-- Health -->
      <div class="endpoint">
        <div class="ep-header">
          <span class="method GET">GET</span>
          <span class="ep-path">/health</span>
          <span class="ep-desc">Service status check</span>
        </div>
        <div class="ep-body">
          <p>Returns the current running status of the API. Use for uptime monitoring and load-balancer health probes. No parameters required.</p>
          <div class="two-col">
            <div class="box">
              <div class="box-label">cURL Request</div>
              <pre><span class="kw">curl</span> https://your-api.railway.app/health</pre>
            </div>
            <div class="box">
              <div class="box-label">Response 200</div>
              <pre>{
  <span class="key">"status"</span>: <span class="str">"ok"</span>,
  <span class="key">"version"</span>: <span class="str">"0.1.0"</span>
}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- Ingest -->
      <div class="endpoint">
        <div class="ep-header">
          <span class="method POST">POST</span>
          <span class="ep-path">/api/v1/ingest</span>
          <span class="ep-desc">Index all photos in storage</span>
        </div>
        <div class="ep-body">
          <p>Crawls the configured storage directory, detects faces in every image using InsightFace, assigns unique <code style="color:var(--accent)">grab_id</code>s, and persists all mappings. Already-indexed images are automatically skipped.</p>

          <table class="params-table">
            <thead><tr><th>Parameter</th><th>Type</th><th>Where</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td>path <span class="tag-opt">optional</span></td>
                <td>string</td>
                <td>query</td>
                <td>Sub-path inside storage dir to ingest (default: entire storage root)</td>
              </tr>
            </tbody>
          </table>

          <div class="two-col">
            <div class="box">
              <div class="box-label">cURL Request</div>
              <pre><span class="cmt"># Ingest everything</span>
<span class="kw">curl</span> -X POST \
  https://your-api.railway.app/api/v1/ingest

<span class="cmt"># Ingest a specific subfolder</span>
<span class="kw">curl</span> -X POST \
  "https://your-api.railway.app/api/v1/ingest\
?path=./storage/marathon-2026"</pre>
            </div>
            <div class="box">
              <div class="box-label">Response 200</div>
              <pre>{
  <span class="key">"images_processed"</span>: <span class="val">342</span>,
  <span class="key">"images_skipped"</span>:   <span class="val">12</span>,
  <span class="key">"faces_detected"</span>:  <span class="val">1087</span>,
  <span class="key">"new_faces_created"</span>: <span class="val">215</span>,
  <span class="key">"errors"</span>: []
}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- Selfie Auth -->
      <div class="endpoint">
        <div class="ep-header">
          <span class="method POST">POST</span>
          <span class="ep-path">/api/v1/auth/selfie</span>
          <span class="ep-desc">Identify by face upload</span>
        </div>
        <div class="ep-body">
          <p>Upload a photo containing your face. The system generates a 512-d ArcFace embedding, searches the database using cosine similarity, and returns your <code style="color:var(--accent)">grab_id</code> and confidence score. The image is processed in memory — never stored.</p>

          <table class="params-table">
            <thead><tr><th>Field</th><th>Type</th><th>Where</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td>file <span class="tag-req">required</span></td>
                <td>binary</td>
                <td>form-data</td>
                <td>Image file containing your face (JPEG, PNG, WEBP). One face should be clearly visible.</td>
              </tr>
            </tbody>
          </table>

          <div class="two-col">
            <div class="box">
              <div class="box-label">cURL Request</div>
              <pre><span class="kw">curl</span> -X POST \
  https://your-api.railway.app/api/v1/auth/selfie \
  -F <span class="str">"file=@/path/to/selfie.jpg"</span></pre>
            </div>
            <div class="box">
              <div class="box-label">Response — Match Found</div>
              <pre>{
  <span class="key">"matched"</span>:    <span class="val">true</span>,
  <span class="key">"grab_id"</span>:    <span class="str">"45e88d79-be4b-..."</span>,
  <span class="key">"confidence"</span>: <span class="val">0.9821</span>,
  <span class="key">"message"</span>:    <span class="str">"Identity verified."</span>
}

<span class="cmt">// No match found:</span>
{
  <span class="key">"matched"</span>:    <span class="val">false</span>,
  <span class="key">"grab_id"</span>:    <span class="val">null</span>,
  <span class="key">"confidence"</span>: <span class="val">null</span>,
  <span class="key">"message"</span>:    <span class="str">"No match found."</span>
}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- Retrieve Images -->
      <div class="endpoint">
        <div class="ep-header">
          <span class="method GET">GET</span>
          <span class="ep-path">/api/v1/images/{grab_id}</span>
          <span class="ep-desc">Fetch all photos for a person</span>
        </div>
        <div class="ep-body">
          <p>Returns a paginated list of every event photo in which the given person appears. Each image includes metadata and bounding box coordinates for every detected face in the frame.</p>

          <table class="params-table">
            <thead><tr><th>Parameter</th><th>Type</th><th>Where</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td>grab_id <span class="tag-req">required</span></td>
                <td>UUID</td>
                <td>path</td>
                <td>The person's unique identity UUID (from the selfie auth response)</td>
              </tr>
              <tr>
                <td>page <span class="tag-opt">optional</span></td>
                <td>integer</td>
                <td>query</td>
                <td>Page number, 1-indexed (default: 1)</td>
              </tr>
              <tr>
                <td>per_page <span class="tag-opt">optional</span></td>
                <td>integer</td>
                <td>query</td>
                <td>Items per page, max 100 (default: 20)</td>
              </tr>
            </tbody>
          </table>

          <div class="two-col">
            <div class="box">
              <div class="box-label">cURL Request</div>
              <pre><span class="kw">curl</span> \
  "https://your-api.railway.app/api/v1/\
images/45e88d79-be4b-455c-b22e-c9517aaf0bf7\
?page=1&per_page=20"</pre>
            </div>
            <div class="box">
              <div class="box-label">Response 200</div>
              <pre>{
  <span class="key">"grab_id"</span>:  <span class="str">"45e88d79-..."</span>,
  <span class="key">"page"</span>:     <span class="val">1</span>,
  <span class="key">"per_page"</span>: <span class="val">20</span>,
  <span class="key">"total"</span>:    <span class="val">34</span>,
  <span class="key">"images"</span>: [{
    <span class="key">"image_id"</span>:    <span class="str">"a1b2c3..."</span>,
    <span class="key">"file_name"</span>:   <span class="str">"finish_line.jpg"</span>,
    <span class="key">"width"</span>: <span class="val">4032</span>, <span class="key">"height"</span>: <span class="val">3024</span>,
    <span class="key">"ingested_at"</span>: <span class="str">"2026-04-18T..."</span>,
    <span class="key">"faces"</span>: [{
      <span class="key">"grab_id"</span>: <span class="str">"45e88d79-..."</span>,
      <span class="key">"bbox"</span>: {
        <span class="key">"x"</span>:<span class="val">425</span>, <span class="key">"y"</span>:<span class="val">294</span>,
        <span class="key">"w"</span>:<span class="val">188</span>, <span class="key">"h"</span>:<span class="val">261</span>
      }
    }]
  }]
}</pre>
            </div>
          </div>
        </div>
      </div>

    </div><!-- /endpoints -->
  </section>

</div><!-- /wrap -->

<footer>
  <p>
    Grabpic v0.1.0 &nbsp;·&nbsp;
    <a href="/docs">Swagger UI</a> &nbsp;·&nbsp;
    <a href="/redoc">ReDoc</a> &nbsp;·&nbsp;
    Built with FastAPI · InsightFace · pgvector
  </p>
</footer>

</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing():
    """Serve the API landing page."""
    return HTMLResponse(content=LANDING_HTML)
