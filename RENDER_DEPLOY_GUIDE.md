# Deploying TrueForge to Render.com (Step-by-Step Guide)

Your repository **[https://github.com/mohammedsafwankhan/TrueForge-.git](https://github.com/mohammedsafwankhan/TrueForge-.git)** is fully configured for Render with **one-click Blueprint deployment** and a unified production server (`run_production.py`).

---

## Option 1: Automatic 1-Click Blueprint Deploy (Recommended)

1. Go to **[dashboard.render.com](https://dashboard.render.com/)** and log in.
2. Click **New +** in the top-right corner, then select **Blueprint**.
3. Connect your GitHub account and select **`mohammedsafwankhan/TrueForge-`**.
4. Render will automatically detect the **`render.yaml`** file.
5. Click **Apply**.
6. Render will automatically:
   - Install dependencies from `requirements.txt`
   - Launch `python run_production.py`
   - Bind to `$PORT`
   - Verify health at `/health`
   - Deploy your live public website at `https://trueforge-stranger-builds.onrender.com`!

---

## Option 2: Manual Web Service Deploy

If you prefer to configure manually:

1. In the **Render Dashboard**, click **New +** -> **Web Service**.
2. Select your repository: `mohammedsafwankhan/TrueForge-`.
3. Configure the settings:
   - **Name:** `trueforge-agent`
   - **Region:** Any (e.g. `Oregon (US West)` or `Frankfurt (EU)`)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `python run_production.py`
   - **Instance Type:** `Free`
4. Expand **Advanced** -> **Health Check Path**:
   - Set to `/health`
5. Click **Create Web Service**.

---

## Optional: Environment Variables in Render Dashboard

If you have your own API keys, add them under the **Environment** tab:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ASI1_API_KEY` | Your live ASI-1 API key from `api.asi1.ai` | Optional (agent runs fallback intent parser if omitted) |
| `AGENTVERSE_API_KEY` | Optional Agentverse API key | Optional |
| `AGENTVERSE_MAILBOX_KEY` | Optional mailbox key | Optional |
| `AGENT_NETWORK` | Target network (`mainnet` or `testnet`) | `mainnet` |

---

## What Gets Deployed

When Render finishes deploying, your single public URL (e.g., `https://trueforge-stranger-builds.onrender.com`) serves:
* **The Complete Frontend UI (`/`):** Stranger Builds interactive command deck with Cyber Phantom Operative, character switcher, and live ACP chat.
* **The Autonomous Agent API (`/api/chat`, `/api/pay`):** Handles multi-agent requests and CosmPy micropayment verification.
* **Health Endpoint (`/health`):** Subsystem matrix and circuit breakers for Render monitoring.
