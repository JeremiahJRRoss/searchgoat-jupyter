# searchgoat-jupyter User Manual

**Version 0.5** | For Python data practitioners working with Cribl Search

---

## What searchgoat Does

Every data analyst knows the feeling: you need data from Cribl Search, and you need it in a DataFrame. The path from query to analysis should be a straight line. Too often, it isn't.

searchgoat removes the detours. You write a Cribl query. You get a DataFrame. Everything in between—authentication, polling, pagination, format conversion—happens without your attention.

```python
from searchgoat_jupyter import SearchClient

client = SearchClient()
df = client.query('cribl dataset="firewall_logs" | limit 1000', earliest="-24h")
```

Three lines. Your data is ready for pandas, numpy, or whatever comes next.

---

## Before You Begin

searchgoat requires three things:

1. **Python 3.10 or later**
2. **Cribl Search access** with API credentials (client ID and secret)
3. **Your Cribl organization and workspace identifiers**

If you can run queries in the Cribl Search UI, you have what you need. The credentials come from your Cribl administrator or your organization's Cribl.Cloud settings.

---

## Installation

```bash
pip install searchgoat-jupyter
```

searchgoat-jupyter installs its dependencies automatically: httpx for network requests, pandas for DataFrames, pydantic for configuration, pyarrow for Parquet support, and nest_asyncio for Jupyter notebook compatibility.

---

## Configuration

searchgoat reads credentials from environment variables. This keeps secrets out of your code and notebooks.

Set these four variables:

```bash
export CRIBL_CLIENT_ID="your-client-id"
export CRIBL_CLIENT_SECRET="your-client-secret"
export CRIBL_ORG_ID="your-organization-id"
export CRIBL_WORKSPACE="your-workspace-name"
```

You can also use a `.env` file in your working directory:

```
CRIBL_CLIENT_ID=your-client-id
CRIBL_CLIENT_SECRET=your-client-secret
CRIBL_ORG_ID=your-organization-id
CRIBL_WORKSPACE=your-workspace-name
```

searchgoat loads `.env` files automatically. Your credentials never appear in version control, notebooks, or error messages.

### Finding Your Credentials

| Credential | Where to Find It |
|------------|------------------|
| Client ID | Cribl.Cloud → Organization Settings → API Credentials |
| Client Secret | Generated when you create the API credential (save it securely) |
| Organization ID | Cribl.Cloud URL: `https://{workspace}-{org_id}.cribl.cloud` |
| Workspace | Cribl.Cloud URL: `https://{workspace}-{org_id}.cribl.cloud` |

---

## Your First Query

With credentials configured, querying becomes a single method call:

```python
from searchgoat_jupyter import SearchClient

client = SearchClient()

df = client.query(
    'cribl dataset="web_access_logs" | limit 100',
    earliest="-1h",
    latest="now"
)

print(df.head())
```

The `query()` method handles the complete workflow: authenticating, submitting your search, waiting for completion, retrieving results, and converting them to a pandas DataFrame.

### Understanding the Parameters

**query** (required): A Cribl Search query string. The query must begin with the `cribl` operator and specify a dataset.

**earliest** (optional): The start of your time range. Accepts relative times like `"-1h"`, `"-7d"`, `"-30m"` or absolute timestamps. Defaults to `"-1h"`.

**latest** (optional): The end of your time range. Defaults to `"now"`.

---

## Working with Search Jobs

Sometimes you want more control. Perhaps your query runs for several minutes, or you want to check progress, or you plan to retrieve results multiple times. The job-based workflow gives you that control.

```python
from searchgoat_jupyter import SearchClient

client = SearchClient()

# Submit the search
job = client.submit(
    'cribl dataset="application_logs" | where level="ERROR"',
    earliest="-24h"
)

print(f"Job submitted: {job.id}")
print(f"Status: {job.status}")

# Wait for completion
job.wait()

print(f"Status: {job.status}")
print(f"Records found: {job.record_count}")

# Retrieve results
df = job.to_dataframe()
```

### Job States

A search job moves through these states:

| State | Meaning |
|-------|---------|
| `new` | Job accepted, not yet running |
| `running` | Search in progress |
| `completed` | Results ready for retrieval |
| `failed` | Search encountered an error |
| `canceled` | Search was stopped before completion |

The `wait()` method polls until the job reaches `completed` or `failed`. By default, it checks every 2 seconds and times out after 5 minutes. You can adjust both:

```python
job.wait(poll_interval=5, timeout=600)  # Check every 5s, wait up to 10 minutes
```

---

## Saving Results Locally

Analysis often happens in stages. You query once, then explore the data across multiple sessions. searchgoat lets you save results locally so you don't repeat expensive queries.

```python
# Save as Parquet (recommended for large datasets)
job.save("./data/error_logs.parquet")

# Save as CSV
job.save("./data/error_logs.csv")

# Later, load with pandas
import pandas as pd
df = pd.read_parquet("./data/error_logs.parquet")
```

Parquet preserves data types and compresses efficiently. A dataset that takes 500MB as CSV might take 50MB as Parquet—and load ten times faster.

The file format is determined by the extension you provide: `.parquet` for Parquet, `.csv` for CSV.

---

## Handling Large Result Sets

Cribl Search may return thousands or millions of records. searchgoat handles pagination automatically—you receive all results, regardless of how many API calls that requires.

For very large datasets, memory becomes a concern. The streaming interface lets you process records one at a time:

```python
async for record in client.stream(job.id):
    # Process each record without loading all into memory
    if record.get("severity") == "CRITICAL":
        alert(record)
```

Most analysis workflows don't need streaming. Start with `to_dataframe()`. If you encounter memory limits, streaming is available.

---

## Common Workflows

### Workflow 1: Quick Exploration

You want to see what's in a dataset. Sample a few records and examine the structure:

```python
from searchgoat_jupyter import SearchClient

client = SearchClient()
df = client.query('cribl dataset="network_flow" | limit 50', earliest="-1h")

# See what columns exist
print(df.columns.tolist())

# Examine data types
print(df.dtypes)

# Look at a few rows
print(df.head(10))
```

### Workflow 2: Filtered Analysis

You need specific records matching certain criteria. Cribl's query language handles filtering before data leaves the server:

```python
df = client.query(
    '''
    cribl dataset="authentication_logs"
    | where status="FAILED" AND source_ip != "10.0.0.0/8"
    | limit 10000
    ''',
    earliest="-7d"
)

# Now analyze with pandas
failures_by_user = df.groupby("username").size().sort_values(ascending=False)
print(failures_by_user.head(20))
```

### Workflow 3: Scheduled Data Pull

You run the same query daily and save results for trend analysis:

```python
from datetime import datetime
from searchgoat_jupyter import SearchClient

client = SearchClient()

today = datetime.now().strftime("%Y-%m-%d")

job = client.submit(
    'cribl dataset="sales_events" | stats count() by product_category',
    earliest="-24h"
)
job.wait()
job.save(f"./data/daily_sales_{today}.parquet")
```

### Workflow 4: Jupyter Notebook Integration

searchgoat works naturally in notebooks. Each cell can be a query:

```python
# Cell 1: Setup
from searchgoat_jupyter import SearchClient
import pandas as pd
import matplotlib.pyplot as plt

client = SearchClient()
```

```python
# Cell 2: Query
df = client.query(
    'cribl dataset="web_traffic" | stats count() by status_code',
    earliest="-24h"
)
df
```

```python
# Cell 3: Visualize
df.plot(kind="bar", x="status_code", y="count")
plt.title("HTTP Status Codes (Last 24 Hours)")
plt.show()
```

---

## Error Handling

searchgoat raises specific exceptions for different failure modes. Catching them lets you respond appropriately:

```python
from searchgoat_jupyter import SearchClient
from searchgoat.exceptions import (
    AuthenticationError,
    QuerySyntaxError,
    JobTimeoutError,
    RateLimitError
)

client = SearchClient()

try:
    df = client.query('cribl dataset="logs" | limit 100')
except AuthenticationError:
    print("Check your CRIBL_CLIENT_ID and CRIBL_CLIENT_SECRET")
except QuerySyntaxError as e:
    print(f"Invalid query: {e}")
except JobTimeoutError:
    print("Query took too long—try a shorter time range or add filters")
except RateLimitError as e:
    print(f"Slow down—retry after {e.retry_after} seconds")
```

### Exception Reference

| Exception | Cause | Typical Resolution |
|-----------|-------|-------------------|
| `AuthenticationError` | Invalid or expired credentials | Verify environment variables |
| `QuerySyntaxError` | Malformed Cribl query | Check query syntax in Cribl UI first |
| `JobTimeoutError` | Search didn't complete in time | Narrow time range, add filters, increase timeout |
| `JobFailedError` | Server-side search failure | Check Cribl Search logs |
| `RateLimitError` | Too many requests | Wait and retry (see `retry_after` attribute) |

---

## Query Writing Tips

searchgoat sends your query to Cribl Search exactly as written. A few patterns will serve you well:

**Always specify a dataset.** Every query starts with `cribl dataset="name"`.

**Filter early.** Conditions in `where` clauses reduce data before it leaves Cribl. This is faster and cheaper than filtering in pandas:

```python
# Good: filter server-side
df = client.query('cribl dataset="logs" | where level="ERROR" | limit 10000')

# Less efficient: filter client-side
df = client.query('cribl dataset="logs" | limit 100000')
df = df[df["level"] == "ERROR"]
```

**Use limit during exploration.** Until you know how much data matches your query, add `| limit 1000` to avoid surprises.

**Aggregate when possible.** If you need counts or statistics, let Cribl compute them:

```python
# Efficient: Cribl computes the aggregation
df = client.query('cribl dataset="access" | stats count() by endpoint')

# Less efficient: transfer all records, aggregate in pandas
df = client.query('cribl dataset="access"')
result = df.groupby("endpoint").size()
```

---

## Async Usage

searchgoat is async-first. The synchronous methods you've seen are convenience wrappers. If you're building pipelines or applications that benefit from concurrency, use the async interface directly:

```python
import asyncio
from searchgoat_jupyter import SearchClient

async def main():
    client = SearchClient()
    
    # Submit multiple queries concurrently
    jobs = await asyncio.gather(
        client.submit_async('cribl dataset="logs_a"', earliest="-1h"),
        client.submit_async('cribl dataset="logs_b"', earliest="-1h"),
        client.submit_async('cribl dataset="logs_c"', earliest="-1h"),
    )
    
    # Wait for all to complete
    await asyncio.gather(*[job.wait_async() for job in jobs])
    
    # Retrieve results
    dataframes = await asyncio.gather(*[job.to_dataframe_async() for job in jobs])
    
    return dataframes

dfs = asyncio.run(main())
```

For most interactive analysis, the sync interface is simpler. Async shines when you're querying multiple datasets or integrating searchgoat into larger async applications.

---

## What searchgoat Does Not Do (Yet)

Version 0.1 focuses on the core workflow: query → results → DataFrame. Some capabilities are planned for future releases:

**Not in v0.1:**
- Listing available datasets
- Schema discovery (what fields exist in a dataset)
- Query building helpers (constructing queries programmatically)
- Result caching
- Automatic retry with backoff (you handle RateLimitError)

If you need to discover datasets or explore schemas, use the Cribl Search UI, then bring your queries to searchgoat.

---

## Getting Help

**Something isn't working?** Check these first:

1. Can you run the same query in the Cribl Search UI?
2. Are your environment variables set in the current shell/notebook?
3. Is your time range reasonable? Very wide ranges may timeout.

**Found a bug?** Open an issue at [repository URL] with:
- Your Python version (`python --version`)
- Your searchgoat version (`pip show searchgoat`)
- The query that failed (sanitize any sensitive data)
- The full error traceback

**Want a feature?** Check the roadmap first—it might already be planned. If not, open an issue describing your use case.

---

## Quick Reference

### Installation
```bash
pip install searchgoat
```

### Environment Variables
```bash
CRIBL_CLIENT_ID      # Required
CRIBL_CLIENT_SECRET  # Required
CRIBL_ORG_ID         # Required
CRIBL_WORKSPACE      # Required
```

### Basic Usage
```python
from searchgoat_jupyter import SearchClient

client = SearchClient()
df = client.query('cribl dataset="name" | limit 1000', earliest="-24h")
```

### Job Workflow
```python
job = client.submit('cribl dataset="name"', earliest="-7d")
job.wait()
df = job.to_dataframe()
job.save("results.parquet")
```

### Exceptions
```python
from searchgoat_jupyter.exceptions import (
    AuthenticationError,
    QuerySyntaxError, 
    JobTimeoutError,
    JobFailedError,
    RateLimitError
)
```

---

## License

Apache 2.0

---

*searchgoat-jupyter is part of the hackish.pub project family.*
