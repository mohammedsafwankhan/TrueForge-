# Deploying TrueForge to Netlify (30-Second Guide)

Your repository **[https://github.com/mohammedsafwankhan/TrueForge-.git](https://github.com/mohammedsafwankhan/TrueForge-.git)** is now fully configured for Netlify via [`netlify.toml`](./netlify.toml).

---

## 1-Click Netlify Deployment via Git

1. Log in to **[app.netlify.com](https://app.netlify.com/)**.
2. Click **Add new site** -> **Import an existing project**.
3. Select **GitHub** and choose your repository: **`mohammedsafwankhan/TrueForge-`**.
4. Netlify will automatically detect [`netlify.toml`](./netlify.toml):
   - **Branch:** `main`
   - **Publish directory:** `frontend`
5. Click **Deploy TrueForge** (or **Deploy site**).

---

## How It Works on Netlify

* **Global Edge CDN:** Serves the Stranger Builds full-stack portal (`frontend/index.html`), vector SVG Cyber Phantom animations, character switcher, and cards with sub-millisecond edge latency worldwide.
* **Transparent API Proxying:** Netlify automatically proxies `/api/*`, `/health`, and `/agent-info` to your deployed backend (`https://trueforge-stranger-builds.onrender.com`), eliminating CORS errors completely.
