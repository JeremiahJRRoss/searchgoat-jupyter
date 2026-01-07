# searchgoat-jupyter Notebooks

This directory contains everything you need to use searchgoat-jupyter in Jupyter notebooks.

## Quick Start

```bash
cd notebooks
./setup.sh
```

That's it. The script will:

1. ✅ Check your Python version
2. ✅ Create a virtual environment
3. ✅ Install searchgoat-jupyter and Jupyter
4. ✅ Prompt you for Cribl credentials
5. ✅ Save credentials to `.env`
6. ✅ Launch Jupyter

## Directory Structure

```
notebooks/
├── setup.sh              # Run this to get started
├── test_searchgoat.ipynb # Template notebook (copied to workspace)
├── venv/                 # Python environment (created by setup.sh)
└── workspace/            # Your notebooks and data go here
    ├── .env              # Your credentials (created by setup.sh)
    └── *.ipynb           # Your notebooks
```

## Finding Your Cribl Credentials

The setup script will ask for four values:

| Credential | Where to Find It |
|------------|------------------|
| `CRIBL_CLIENT_ID` | Cribl Cloud → ⚙️ → Organization Settings → API Credentials |
| `CRIBL_CLIENT_SECRET` | Generated when you create API credentials (save it!) |
| `CRIBL_ORG_ID` | Your URL: `https://{workspace}-{org_id}.cribl.cloud` |
| `CRIBL_WORKSPACE` | Your URL: `https://{workspace}-{org_id}.cribl.cloud` |

**Example:** If your URL is `https://main-abc123xyz.cribl.cloud/`:
- Workspace = `main`
- Org ID = `abc123xyz`

## Re-running Setup

If you need to change credentials or reinstall, just run `./setup.sh` again. It will overwrite the existing environment.

## Manual Activation

If Jupyter isn't running and you want to activate the environment manually:

```bash
cd notebooks
source venv/bin/activate
cd workspace
jupyter notebook
```

## Requirements

- macOS or Linux
- Python 3.10+
- Internet connection to Cribl Cloud
