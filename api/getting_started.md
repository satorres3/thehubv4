# Azure Functions Deployment Guide

_Last updated: February 14, 2025_

This document explains how to run and deploy the Python Azure Functions backend contained in the `api` directory of this repository. The backend is paired with a Vite-built frontend and is deployed together to Azure Static Web Apps (SWA).

## Project Structure
- **Function directories** – each HTTP-triggered endpoint lives in its own folder with an `__init__.py` file (e.g., `authLogin/`, `gemini/`, `graphProxy/`).
- **shared/** – reusable Python modules (`config.py`, `session.py`, `msal_client.py`, `utils.py`).
- **requirements.txt** – Python dependencies for the Function App.
- **local.settings.json** – local development settings (not committed to git).

## Running Locally
1. Navigate to the `api` folder and create a virtual environment:
   ```bash
   cd api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Populate `local.settings.json` with the required environment variables. See [../howtosetup.md](../howtosetup.md) for detailed guidance on obtaining Microsoft and Gemini credentials.
3. Start the Functions host:
   ```bash
   func start
   ```
   The API will listen on <http://localhost:7071>. The Vite dev server proxies `/api/*` calls to this port.

## Deploying to Azure Static Web Apps
1. **Build the frontend** (from the repository root):
   ```bash
   npm ci
   npm run build
   ```
2. **Create a service principal** and save its credentials as the GitHub secret `AZURE_CREDENTIALS`:
   ```bash
   az ad sp create-for-rbac --name thehubv4-sp --role Contributor \
     --scopes /subscriptions/<SUBSCRIPTION_ID> --sdk-auth
   ```
3. **Configure the GitHub Action** (already included in `.github/workflows/build-and-deploy.yml`): it logs in with `azure/login@v1` using `AZURE_CREDENTIALS`, installs backend dependencies with `pip install -r api/requirements.txt`, builds the frontend, and deploys via `Azure/static-web-apps-deploy@v1`.
4. **Run the workflow** by pushing to `main`. The action publishes both the `dist/` frontend and the Python Function App under `/api` to your SWA instance.

### Manual CLI Deployment (optional)
If you prefer deploying from your local machine:
```bash
az login --service-principal -u <client-id> -p <client-secret> --tenant <tenant-id>
az staticwebapp upload --name <app-name> --app-location . --api-location api --output-location dist
```

After deployment, set the same environment variables from `local.settings.json` in the SWA portal under **Configuration**.
