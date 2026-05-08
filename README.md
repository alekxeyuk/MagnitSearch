# MagnitSearch

Small Python toolkit for collecting product data from Magnit's web API, storing it in a local SQLite database, generating static category pages, and uploading the generated site to S3-compatible object storage.

The current workflow is interactive and is driven from `main.py`.

## What It Does

- Imports product lists from Magnit's `/goods/search` endpoint for a selected category.
- Stores products and categories in `products.db` using Peewee models.
- Fetches detailed product data for already imported products, including ingredients, weight, nutrition data, and final-price flags.
- Generates static HTML pages in `output/`, sorted by effective price per kilogram.
- Optionally applies a promocode discount while generating HTML.
- Filters out products whose ingredients mention mechanical deboning.
- Uploads the generated `output/` folder to S3-compatible storage.

## Project Layout

| File | Purpose |
| --- | --- |
| `main.py` | Interactive entry point for import, detail refresh, HTML generation, and upload. |
| `models.py` | SQLite schema and Peewee helpers. |
| `categories.py` | Default categories, category slugging, and interactive category prompts. |
| `generate_index.py` | Static HTML generation for the category index and category pages. |
| `s3_upload.py` | Uploads generated files to S3-compatible object storage. |
| `products.db` | Local SQLite database created/updated by the scripts. |
| `output/` | Generated static site files. Ignored by Git. |
| `.aws/` | Local S3 credentials/config/params. Ignored by Git. |

## Requirements

- Python 3.10+
- Network access to `magnit.ru`
- Python packages:
  - `requests`
  - `peewee`
  - `jinja2`
  - `boto3`

There is no requirements file in the repository yet, so install the packages manually:

```bash
python -m venv venv
source venv/bin/activate
pip install requests peewee jinja2 boto3
```

On Windows PowerShell, activate the environment with:

```powershell
.\venv\Scripts\Activate.ps1
```

## Usage

Run the interactive menu:

```bash
python main.py
```

Available modes:

1. `parse data using /search`
   Imports products for a selected category and saves them to `products.db`.

2. `request item details for every item stored in db category`
   Refreshes detailed data for products already imported into a selected local category.

3. `generate category html files from local db`
   Builds static pages in `output/`. You will be prompted for a promocode discount percentage; enter `0` if no discount should be applied.

4. `upload output folder to s3 object storage`
   Uploads all files from `output/` to the configured S3-compatible bucket.

Typical run order:

```text
1. Import products for a category.
2. Refresh item details for that category.
3. Generate HTML files.
4. Upload output, if needed.
```

## Category Selection

`categories.py` contains built-in default categories:

```python
DEFAULT_CATEGORIES = [
    {'id': 64249, 'title': 'Колбасы и сосиски'},
]
```

When importing data, the script also offers categories already saved in the local database. Choose `0` in the prompt to enter a category ID and title manually.

## Generated Site

HTML generation writes files to `output/`:

- `output/index.html` lists all generated categories.
- `output/<category-slug>.html` lists products for one category.

Products are sorted by `weight_per_kg` ascending after any entered promocode discount is applied. Items marked as final price are not discounted.

## S3 Upload Configuration

`s3_upload.py` expects local AWS-style files under `.aws/`:

```text
.aws/config
.aws/credentials
.aws/params
```

Example `.aws/config`:

```ini
[default]
region = ru-central1
endpoint_url = https://storage.example.com
```

Example `.aws/credentials`:

```ini
[default]
aws_access_key_id = your-access-key
aws_secret_access_key = your-secret-key
```

`.aws/params` is created/updated by the upload script and stores the last used bucket and prefix:

```ini
[default]
bucket_name = your-bucket
prefix = optional/path
```

The `.aws/` directory is ignored by Git.

## Local Data And Git

The repository currently ignores:

- `venv/`
- `__pycache__/`
- `.vscode/`
- `output/`
- `.aws/`
- `products.db`

## Notes

- API headers, store code, store type, and catalog type are currently hardcoded in `main.py`.
- Prices are stored as integer minor units and formatted as rubles during HTML generation.
- `generate_index.py` contains the full HTML templates inline.
