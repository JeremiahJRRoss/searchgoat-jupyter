# Testing searchgoat-jupyter on Mac (and Linux)

This guide walks you through testing searchgoat-jupyter using the automated setup script.

---

## Part 1: Find Your Cribl Credentials

Before running the setup, gather these four pieces of information from Cribl Cloud.

### Step 1: Log into Cribl Cloud

Go to [https://cribl.cloud](https://cribl.cloud) and sign in.

### Step 2: Get Your Organization ID and Workspace

Look at the URL in your browser. It follows this pattern:

```
https://main-myorg123.cribl.cloud/...
       ^^^^  ^^^^^^^^^^
       │     │
       │     └── This is your ORG_ID
       └──────── This is your WORKSPACE
```

**Example:** If your URL is `https://main-abc123xyz.cribl.cloud/`, then:
- `CRIBL_WORKSPACE` = `main`
- `CRIBL_ORG_ID` = `abc123xyz`

### Step 3: Create API Credentials

1. Click the **gear icon** (⚙️) in the top-right → **Organization Settings**
2. Select **Access Management** → **API Credentials**
3. Click **+ Add Credentials**
4. Give it a name (e.g., "searchgoat-dev")
5. Select appropriate permissions (at minimum: **Search Read**)
6. Click **Create**

**⚠️ Important:** Copy the **Client Secret** immediately — you won't be able to see it again!

You now have:
- `CRIBL_CLIENT_ID` = The Client ID shown
- `CRIBL_CLIENT_SECRET` = The secret you just copied

### Step 4: Find a Dataset Name

You need at least one dataset to query.

1. In Cribl Cloud, go to **Search** (left sidebar)
2. Look at the **Datasets** panel on the left
3. Note the name of any dataset (e.g., `cribl_internal_logs`, `main`, etc.)

---

## Part 2: Run the Setup Script

### Step 1: Download/Clone the Repository

```bash
# Option A: Clone with git
git clone https://github.com/hackish-pub/searchgoat.git
cd searchgoat

# Option B: Or extract from zip
unzip searchgoat-v0.1.0.zip
cd searchgoat
```

### Step 2: Run Setup

```bash
cd notebooks
./setup.sh
```

The script will:
1. Check your Python version (requires 3.10+)
2. Create a virtual environment
3. Install searchgoat and Jupyter
4. Prompt you for each credential
5. Save credentials securely to `.env`
6. Launch Jupyter Notebook

### Step 3: Enter Your Credentials

When prompted, enter the values you gathered in Part 1:

```
Enter CRIBL_CLIENT_ID: <paste your client ID>
Enter CRIBL_CLIENT_SECRET: <paste your secret - it won't show>
Enter CRIBL_ORG_ID: <your org ID from the URL>
Enter CRIBL_WORKSPACE: <your workspace from the URL>
```

### Step 4: Test in Jupyter

Once Jupyter opens:
1. Open `test_searchgoat.ipynb`
2. Run the cells in order (Shift+Enter)
3. When you reach Step 3, edit `DATASET` to match a real dataset from your Cribl Search

---

## Part 3: Troubleshooting

### "Permission denied" when running setup.sh

```bash
chmod +x setup.sh
./setup.sh
```

### "Python not found" or version too old

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

### Credentials error in notebook

If Step 2 fails with "Field required" errors:
1. Check that you're running Jupyter from the `workspace/` directory
2. Verify `.env` exists: `ls -la notebooks/workspace/.env`
3. Re-run `./setup.sh` to re-enter credentials

### "AuthenticationError: 401"

Your credentials are wrong. Double-check:
- Client ID and Secret are correct (no extra spaces)
- The API credentials haven't been revoked in Cribl Cloud
- The credentials have Search permissions

### "QuerySyntaxError"

The dataset name doesn't exist. Go back to Cribl Search UI and verify the exact dataset name.

---

## Part 4: Re-running Setup

Need to change credentials or start fresh? Just run the script again:

```bash
cd notebooks
./setup.sh
```

It will overwrite the existing environment and credentials.

---

## Part 5: Manual Activation (Advanced)

If you closed Jupyter and want to restart without running full setup:

```bash
cd searchgoat-jupyter/notebooks
source venv/bin/activate
cd workspace
jupyter notebook
```

---

## Summary

| What | Where |
|------|-------|
| Setup script | `notebooks/setup.sh` |
| Virtual environment | `notebooks/venv/` |
| Your credentials | `notebooks/workspace/.env` |
| Your notebooks | `notebooks/workspace/` |
| Test notebook | `notebooks/workspace/test_searchgoat.ipynb` |

Happy querying! 🐐
