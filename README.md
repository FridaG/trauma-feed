Here's a comprehensive README for your repository:

```markdown
# Trauma Literature RSS Feed

A custom, self-updating RSS feed that aggregates recent trauma medicine literature from PubMed. It monitors core trauma journals in full and filters high-impact general/emergency medicine journals for trauma-relevant articles using keyword matching.

The system consists of three components:

1. **Python script** — queries PubMed via E-utilities API, filters articles by keyword, and generates a structured JSON file
2. **GitHub Actions** — runs the script on a schedule and publishes the JSON to GitHub Pages
3. **Cloudflare Worker** — serves a dynamic web interface for filtering articles and generates personalised RSS feed URLs

## Features

- **Two-tier journal monitoring**: Core trauma journals (every article captured) and high-impact general journals (trauma-relevant articles only)
- **Keyword-based filtering** with topic categorisation (e.g. Thoracic, TBI, Paediatric, Vascular)
- **Match strength scoring**: "Strong" matches (keyword in title) vs "weak" matches (keyword in abstract only)
- **Interactive web interface** with real-time filtering by topic, keyword, journal, and free text
- **Spelling equivalence**: Automatically expands Australian/British and American English variants (e.g. haemorrhage ↔ hemorrhage)
- **Full abstracts** included in the RSS feed
- **Excludes** comments, letters, errata, and (optionally) editorials
- **Mobile-friendly** — designed to be consumed via any RSS reader app

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   GitHub Actions     │     │  GitHub Pages     │     │  Cloudflare Worker  │
│   (scheduled cron)   │────▶│  articles.json    │◀────│  (web UI + RSS)     │
│   generate_feed.py   │     │  feed.xml         │     │  worker.js          │
└─────────────────────┘     └──────────────────┘     └─────────────────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │  RSS Reader App │
                                                     │  (phone/desktop)│
                                                     └─────────────────┘
```

GitHub Pages also hosts a static `feed.xml` (unfiltered) as a fallback. The Cloudflare Worker provides the dynamic, filterable feed.

## Deployment Guide

### Prerequisites

- A GitHub account
- A [Cloudflare account](https://dash.cloudflare.com/sign-up) (free tier is sufficient)
- An [NCBI API key](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/) (optional but recommended — increases rate limit from 3 to 10 requests/second)

### Step 1: Fork or Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/trauma-feed.git
cd trauma-feed
```

### Step 2: Configure GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions**, and add:

| Secret Name | Description | Required |
|---|---|---|
| `NCBI_API_KEY` | Your NCBI E-utilities API key | Recommended |
| `NCBI_EMAIL` | Your email address (required by NCBI usage policy) | Yes |

### Step 3: Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. The workflow will automatically deploy `articles.json` and `feed.xml` to GitHub Pages

### Step 4: Run the Workflow

The workflow runs automatically on a schedule (see `.github/workflows/`), but you can trigger it manually:

1. Go to the **Actions** tab
2. Select the workflow
3. Click **Run workflow**

After completion, verify the output at:
```
https://YOUR_USERNAME.github.io/trauma-feed/articles.json
```

### Step 5: Deploy the Cloudflare Worker

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Go to **Workers & Pages** → **Create application** → **Create Worker**
3. Name your worker (e.g. `trauma-feed`)
4. Click **Deploy**, then **Edit code**
5. Replace the default code with the contents of `worker.js`
6. **Important**: Update the `ARTICLES_URL` constant at the top of `worker.js` to point to your GitHub Pages URL:
   ```javascript
   const ARTICLES_URL = "https://YOUR_USERNAME.github.io/trauma-feed/articles.json";
   ```
7. Also update the `JSON_URL` variable inside the `getWebInterface()` function to match
8. Click **Save and deploy**

Your worker will be available at `https://your-worker-name.your-subdomain.workers.dev`.

#### Custom Domain (Optional)

To use a custom domain:
1. In the Cloudflare dashboard, go to your worker → **Settings** → **Triggers**
2. Add a custom route or domain

### Step 6: Subscribe in Your RSS Reader

1. Visit your Cloudflare Worker URL in a browser
2. Use the web interface to configure your desired filters
3. Copy the generated RSS feed URL from the green URL box at the top
4. Add this URL to your RSS reader app (e.g. NetNewsWire, Feedly, Inoreader, Reeder)

## Configuration

### Adjusting the Lookback Window

By default, the script searches for articles published in the last 28 days. To change this, edit `generate_feed.py` and modify the `LOOKBACK_DAYS` variable:

```python
LOOKBACK_DAYS = 28  # Change to desired number of days
```

A shorter window reduces the number of articles but may miss papers with delayed indexing. A longer window increases coverage but also increases API calls and feed size.

### Adjusting the Schedule

Edit the cron schedule in `.github/workflows/generate_feed.yml`:

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # Runs daily at 06:00 UTC
```

Useful cron patterns:

| Schedule | Cron Expression |
|---|---|
| Every 12 hours | `0 */12 * * *` |
| Daily at 6 AM UTC | `0 6 * * *` |
| Twice daily (6 AM and 6 PM UTC) | `0 6,18 * * *` |
| Every Monday and Thursday | `0 6 * * 1,4` |

### Adding or Removing Journals

Journals are defined in `generate_feed.py` in two dictionaries:

```python
CORE_JOURNALS = {
    "Journal Name": "ISSN-XXXX",
    # All articles from these journals are captured
}

FILTERED_JOURNALS = {
    "Journal Name": "ISSN-XXXX",
    # Only articles matching trauma keywords are captured
}
```

**To add a journal:**
1. Find the journal's ISSN on [NLM Catalog](https://www.ncbi.nlm.nih.gov/nlm-catalog/)
2. Add it to the appropriate dictionary (core or filtered)
3. Commit and push — the next workflow run will include the new journal

**To remove a journal:**
Simply delete or comment out the corresponding line.

### Adding or Modifying Keywords

Keywords are defined in the `TRAUMA_KEYWORDS` dictionary in `generate_feed.py`, organised by topic:

```python
TRAUMA_KEYWORDS = {
    "Thoracic": [
        r"\bhaemothorax\b", r"\bhemothorax\b",
        r"\bpneumothorax\b", r"\brib fracture",
        # Add new keywords here
    ],
    "TBI": [
        r"\btraumatic brain injur",
        r"\bsubdural\b",
        # ...
    ],
    # Add new topic categories here
}
```

Keywords use Python regex patterns. Common patterns:

| Pattern | Meaning |
|---|---|
| `r"\bkeyword\b"` | Exact word match |
| `r"\bkeyword"` | Word starts with "keyword" (captures plurals, etc.) |
| `r"keyword"` | Substring match anywhere |
| <code>r"\b(word1&#124;word2)\b"</code> | Match either word |

**Note:** When adding keywords with Australian/British spelling, add both variants (e.g. `haemorrhage` and `hemorrhage`). Also add the pair to the `SPELLING_PAIRS` lists in both `generate_feed.py` and `worker.js` to enable spelling-aware free-text search.

### Excluding Article Types

The script excludes comments, letters, and errata by default via PubMed publication type filters. To modify these exclusions, edit the `EXCLUDE_PUB_TYPES` list in `generate_feed.py`:

```python
EXCLUDE_PUB_TYPES = [
    "Comment", "Letter", "Published Erratum",
    "Editorial",  # Uncomment to exclude editorials
]
```

## How It Works

### Article Matching

1. **Core journals**: All articles are included regardless of content (tagged as `tier: core`)
2. **Filtered journals**: Articles are included only if their title or abstract matches at least one trauma keyword (tagged as `tier: filtered`)

### Match Strength

Each keyword match is classified as:
- **Strong**: Keyword appears in the article title — high likelihood of relevance
- **Weak**: Keyword appears only in the abstract — may be tangentially related

The web interface and RSS feed both indicate match strength, allowing you to prioritise strong matches.

### Topic Assignment

Each article is assigned to one or more topics based on which keyword categories matched. For example, an article matching "rib fracture" and "pneumothorax" would be tagged with the "Thoracic" topic.

### Feed Generation Pipeline

```
PubMed E-utilities API
        │
        ▼
  Fetch articles from each journal (last 28 days)
        │
        ▼
  For filtered journals: test title + abstract against keyword regexes
        │
        ▼
  Deduplicate by PMID
        │
        ▼
  Generate articles.json (with metadata, topics, keyword matches)
        │
        ▼
  Generate feed.xml (static, unfiltered RSS)
        │
        ▼
  Deploy to GitHub Pages
        │
        ▼
  Cloudflare Worker reads articles.json
        │
        ▼
  User applies filters via web UI → custom RSS URL generated
```

## Web Interface

The Cloudflare Worker serves an interactive web page at its root URL with the following features:

- **Topic chips**: Click to include a topic (all its keywords), right-click to exclude
- **Keyword chips**: Fine-tune which specific keywords within a topic are active
- **Journal chips**: Filter to specific journals (star icon = core trauma journal)
- **Match strength toggle**: Hide weak matches to see only high-confidence results
- **Free-text search**: Search titles and abstracts with automatic spelling variant expansion
- **Sort controls**: Sort keywords and journals by match count or alphabetically
- **Show all**: Toggle visibility of keywords/journals with zero matches in the current dataset
- **Dynamic RSS URL**: Updates in real time as you adjust filters — click to copy

### Chip Interaction

| Action | Effect |
|---|---|
| Left-click (topic) | Include all keywords in that topic |
| Right-click (topic) | Exclude all articles in that topic |
| Left-click (keyword) | Toggle individual keyword inclusion |
| Right-click (keyword) | Exclude articles matching that keyword |
| Left-click (journal) | Filter to that journal |

A **dashed border** on a topic chip indicates partial customisation — some of its child keywords have been individually overridden.

## RSS Feed URL Parameters

The feed endpoint (`/feed.xml`) accepts the following query parameters for direct URL construction:

| Parameter | Description | Example |
|---|---|---|
| `topics` | Comma-separated topic names to include | `topics=Thoracic,TBI` |
| `keywords` | Comma-separated keywords to include | `keywords=pneumothorax,rib fracture` |
| `journals` | Comma-separated journal name substrings | `journals=J Trauma,Injury` |
| `exclude` | Comma-separated topics to exclude | `exclude=Burns` |
| `exclude_kw` | Comma-separated keywords to exclude | `exclude_kw=burn,thermal` |
| `strength` | Set to `strong` to hide weak matches | `strength=strong` |
| `tier` | Filter by journal tier (`core` or `filtered`) | `tier=core` |
| `q` | Free-text search (spelling variants auto-expanded) | `q=REBOA` |

Parameters can be combined:
```
/feed.xml?topics=Thoracic,Vascular&strength=strong&journals=J Trauma
```

## NCBI API Usage Policy

This project complies with [NCBI E-utilities usage guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/):

- Requests are rate-limited with appropriate delays between API calls
- An email address and API key are provided with each request
- The tool is used for personal, non-commercial literature monitoring
- No bulk data redistribution — only bibliographic metadata is cached

## Troubleshooting

| Issue | Solution |
|---|---|
| Worker page stuck on "Loading" | Check browser console (F12) for errors. Ensure `articles.json` URL is correct and accessible. |
| No articles appearing | Run the GitHub Actions workflow manually. Check the workflow logs for API errors. |
| Missing journal | Verify the ISSN is correct via [NLM Catalog](https://www.ncbi.nlm.nih.gov/nlm-catalog/). Some journals may not be indexed in PubMed. |
| Too many irrelevant results | Review keyword patterns — broad substring matches may need `\b` word boundaries. Consider moving keywords to more specific topics. |
| Spelling search not working | Ensure the spelling pair is listed in both `generate_feed.py` and the `SPELLING_PAIRS` array in `worker.js`. |
| GitHub Pages 404 | Ensure GitHub Pages is configured to deploy from GitHub Actions (not a branch). Check the workflow completed successfully. |
| Rate limit errors from NCBI | Add or verify your `NCBI_API_KEY` secret. Increase `time.sleep()` delays in the script if needed. |

## File Structure

```
trauma-feed/
├── .github/
│   └── workflows/
│       └── generate_feed.yml    # GitHub Actions workflow
├── generate_feed.py             # PubMed query and article processing script
├── worker.js                    # Cloudflare Worker (web UI + RSS endpoint)
├── requirements.txt             # Python dependencies
└── README.md
```

Output files (generated, hosted on GitHub Pages):
```
├── articles.json                # Structured article data with metadata
└── feed.xml                     # Static unfiltered RSS feed
```

## Licence

This project is provided for personal, non-commercial use. PubMed data is sourced from the [NCBI E-utilities API](https://www.ncbi.nlm.nih.gov/books/NBK25501/) and is subject to NCBI's terms of use.
```

---

This README covers:

- **What it does** and the architecture
- **Full deployment walkthrough** (GitHub, Cloudflare, RSS reader)
- **All configuration options** (lookback window, schedule, journals, keywords, exclusions)
- **How the matching/scoring works** under the hood
- **Web interface documentation** with interaction patterns
- **Direct RSS URL parameter reference** for power users
- **NCBI compliance** statement
- **Troubleshooting** table for common issues
- **File structure** overview
