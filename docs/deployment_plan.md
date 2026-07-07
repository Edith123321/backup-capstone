# SAKA — Deployment Plan

Deployment strategy, tooling, environments, and verification evidence for the
SAKA RHD screening platform (backend API, React dashboard, ESP32 firmware).

## 1. Environments

| Environment | Backend | Frontend | Database | Purpose |
|-------------|---------|----------|----------|---------|
| **Local dev** | `flask run` / `gunicorn app:app` on `:5001` | `vite` dev server on `:5173`, `VITE_API_URL=http://localhost:5001` | SQLite `doctors.db` | Development + unit/integration tests |
| **Production** | Render Web Service (Gunicorn) | Render Static Site (Vite build) | SQLite on disk (`DATABASE_PATH`) | Gisozi pilot |
| **Device** | — | — | — | ESP32 firmware flashed via PlatformIO |

## 2. Toolchain

| Concern | Tool |
|---------|------|
| Backend runtime | Python 3.12, Flask 3, Gunicorn (`--workers 1 --threads 4`) |
| ML / DSP | NumPy, SciPy, scikit-learn 1.7.2 (pinned to the serialized model) |
| Frontend build | Node 18+, Vite, React 19, MUI |
| Firmware | PlatformIO, ESP32 Arduino core |
| Hosting / CI | Render (Blueprint `render.yaml`), GitHub |
| Reports | ReportLab (PDF) |

## 3. Backend deployment (Render Web Service)

Codified in [`render.yaml`](../render.yaml).

1. **Build:** `pip install -r requirements.txt` (from `rootDir: backend`).
2. **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`.
   - 1 worker + threads keeps memory within the free tier (the model + NumPy/SciPy/matplotlib load once per worker).
   - `--timeout 120` covers audio upload + feature extraction.
3. **Python pinned** via `backend/runtime.txt` (`python-3.12.7`) so the scikit-learn/scipy wheels resolve.
4. **Health check:** `GET /health` (Render `healthCheckPath`).
5. **Secrets** (Render dashboard, `sync:false`): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`. `SECRET_KEY` auto-generated.
6. **Session store:** `SESSION_FILE_DIR` points at a temp dir so Flask-Session cannot shadow the `flask_session` package on worker restart.

### Data persistence
The free tier filesystem is ephemeral (resets on cold start). `DATABASE_PATH`
lets the SQLite file live on a mounted disk (`render.yaml` `disk:` block, paid
instance) for durable storage. Alternative: migrate to Render Postgres.

## 4. Frontend deployment (Render Static Site)

1. **Build:** `npm ci && npm run build` → `dist/`.
2. **Publish:** `staticPublishPath: ./dist`.
3. **SPA routing:** `public/_redirects` + a `rewrite` route send all paths to `index.html`.
4. **Backend URL** baked at build time via `VITE_API_URL`.

## 5. Firmware deployment (ESP32)

1. Open `iot/` in PlatformIO; deps auto-install from `platformio.ini`.
2. Set Wi-Fi SSID/password in `iot/src/Config.h`.
3. `pio run -t upload` (entry `iot/src/Saka_Stethoscope.ino`).
4. Streams 4 kHz/16-bit PCG over BLE (service `4fafc201…`) and WebSocket.

## 6. Verification (done)

Deployment was verified end-to-end in a clean, Render-equivalent environment:

| Check | Result |
|-------|--------|
| `pip install -r requirements.txt` in a fresh venv | ✅ resolves, installs scikit-learn 1.7.2 |
| `gunicorn app:app` boot | ✅ `/health` healthy, all services loaded |
| Model load | ✅ `/screening/health` → `model_loaded: true`, 51 features |
| Real prediction through deployed path | ✅ `test.wav` → prediction + severity |
| PDF report generate + download | ✅ valid `%PDF-`, HTTP 200 |
| Frontend build | ✅ 288 modules, backend URL embedded, `_redirects` present |
| Unit + integration tests | ✅ 25 passing (see `tests/`) |

## 7. Rollback
Render keeps previous deploys; roll back via the dashboard. The DB file (on a
persistent disk) is unaffected by code redeploys.
