# Grabpic — Deployment & Showcase Guide

## Your Options at a Glance

| Method | Cost | Effort | Share with others | Persistent storage |
|---|---|---|---|---|
| **A. Localhost + ngrok** | Free | 2 min | ✅ Public URL | ✅ Local disk |
| **B. Railway** | Free ($5 credit) | ~10 min | ✅ Permanent URL | ✅ Volume |
| **C. Render** | Free tier | ~15 min | ✅ Permanent URL | ⚠️ Ephemeral |
| **D. Fly.io** | Free tier | ~20 min | ✅ Permanent URL | ✅ Volume |

> **Database:** You already have Supabase (free tier) — works for all options above.

> **Biggest constraint:** InsightFace `buffalo_l` downloads ~300 MB of model weights on first run.
> This means **cold starts are slow** (1–3 min) on free tiers. After the first run the model is cached.

---

## Option A — Localhost + ngrok (Fastest, Right Now)

Run locally, get a public HTTPS URL anyone can call in 2 minutes.

### 1. Install ngrok

```bash
# Windows (via winget)
winget install ngrok.ngrok

# Or download from https://ngrok.com/download and extract to PATH
```

### 2. Make sure your server is running

```bash
uv run uvicorn main:app --port 8000
```

### 3. Start ngrok tunnel

```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:8000
```

That **public URL** works immediately. Share it — anyone can call:
- `https://abc123.ngrok-free.app/health`
- `https://abc123.ngrok-free.app/docs`  ← interactive Swagger UI
- `https://abc123.ngrok-free.app/api/v1/ingest`

> **Limit:** Free ngrok sessions expire after 8 hours. Signing up (free) gives unlimited hours.

---

## Option B — Railway (Recommended Free Cloud)

Railway gives $5 free credit/month — enough to run this API 24/7 for ~a week,
or sporadically for much longer.

### 1. Prerequisites

- GitHub account with your project pushed
- [railway.app](https://railway.app) account (sign in with GitHub)

### 2. Push to GitHub

```bash
cd e:\folder\graphic-backend
git init          # if not done
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/grabpic-backend.git
git push -u origin main
```

### 3. Deploy on Railway

1. Go to [railway.app/new](https://railway.app/new)
2. Click **"Deploy from GitHub repo"**
3. Select your `grabpic-backend` repository
4. Railway auto-detects Python — it will use the `Procfile` *(see file below)*

### 4. Set Environment Variables in Railway Dashboard

```
DATABASE_URL     = postgresql://postgres:Gmail.com123@db.xcbjvscvnilefhplbwxv.supabase.co:5432/postgres
IMAGE_STORAGE_PATH = ./storage
PORT             = 8000
FACE_MODEL       = buffalo_l
FACE_MATCH_TOLERANCE = 0.45
```

### 5. That's it

Railway gives you a URL like `https://grabpic-backend-production.up.railway.app`.

> **Model cache:** On Railway, add a persistent volume mounted at `/root/.insightface`
> so the model is not re-downloaded on every deploy.

---

## Option C — Render

Free tier, auto-deploys from GitHub. Spins down after 15 min of inactivity
(first request after sleep takes ~30 sec + model download time).

### Steps

1. Push to GitHub (same as Railway step 2)
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install uv && uv sync`
   - **Start command:** `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (same set as Railway above)
6. Deploy

---

## Option D — Fly.io

Most generous free tier (3 shared VMs, 3GB volume). Best for longer-running demos.

```bash
# Install flyctl
winget install Fly.io.flyctl

# Login
fly auth login

# Launch (from project directory)
fly launch --name grabpic-backend --region sin --no-deploy

# Set secrets
fly secrets set DATABASE_URL="postgresql://postgres:Gmail.com123@db.xcbjvscvnilefhplbwxv.supabase.co:5432/postgres"
fly secrets set FACE_MODEL="buffalo_l"
fly secrets set FACE_MATCH_TOLERANCE="0.45"
fly secrets set IMAGE_STORAGE_PATH="./storage"

# Create a volume for model cache + storage
fly volumes create grabpic_data --size 2 --region sin

# Deploy
fly deploy
```

---

## Testing the API Yourself (No Deployment Needed)

The server is already running locally at `http://localhost:8000`.

### Interactive Browser UI

Open: **http://localhost:8000/docs**

From the Swagger UI you can:
- Click **POST /api/v1/ingest** → **Try it out** → **Execute**
- Click **POST /api/v1/auth/selfie** → **Try it out** → upload any photo
- Click **GET /api/v1/images/{grab_id}** → paste a grab_id → Execute

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Ingest the demo images
curl -X POST "http://localhost:8000/api/v1/ingest?path=./storage/marathon-demo"

# Authenticate with a selfie (replace with any image path)
curl -X POST http://localhost:8000/api/v1/auth/selfie \
  -F "file=@storage/marathon-demo/alice_finish_line.png"

# Retrieve photos for a grab_id (replace UUID with one from auth response)
curl "http://localhost:8000/api/v1/images/45e88d79-be4b-455c-b22e-c9517aaf0bf7"
```

### Using the Python Demo Script

```bash
# Already set up — just run:
uv run python demo_test.py
```

### Using Postman / Insomnia / Bruno

Import this base URL: `http://localhost:8000`

Key requests to set up:
| Name | Method | URL | Body |
|---|---|---|---|
| Health | GET | `/health` | — |
| Ingest | POST | `/api/v1/ingest` | — |
| Selfie Auth | POST | `/api/v1/auth/selfie` | form-data: `file` = image |
| Get Images | GET | `/api/v1/images/{{grab_id}}` | — |

---

## Deployment Files

The files below are already in your project (created by this guide):
- `Procfile` — for Railway/Render
- `Dockerfile` — for any container platform
- `.dockerignore` — keeps image small

