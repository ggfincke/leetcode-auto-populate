# leetcode-auto-populate

Script to automatically populate LeetCode problem lists via GraphQL + Playwright.

## What it does

- Takes a list of LeetCode problem titles.
- Uses the public GraphQL API to resolve titles → slugs.
- Uses Playwright to open LeetCode in a real browser and add those problems to a target list.
- Logs which problems were found / skipped.

## Requirements

- Python 3.10+
- `pip` + `virtualenv` (optional but recommended)
- Playwright + browser binaries

Install deps:

```bash
pip install -r requirements.txt
playwright install
If you’re using python -m venv venv, activate that first.
```

## Setup
Clone the repo:

```bash
git clone https://github.com/<your-username>/leetcode-auto-populate.git
cd leetcode-auto-populate
```

Create a .env (optional, if you want to store things like email/username):

```env
LEETCODE_USERNAME=your_email_or_username
```

Or just have the script prompt you interactively.

Make sure you can log in to LeetCode in a normal browser first (no extra captchas / weird auth).

## Usage
Basic pattern (adjust to whatever args your script uses):

```bash
python main.py \
  --titles-file titles.txt \
  --list-name "NeetCode - Arrays & Hashing"
```

Example `titles.txt`:

```text
Two Sum
Group Anagrams
Product of Array Except Self
Word Ladder
```

Typical flags you might expose:

--titles-file – path to a newline-separated list of problem titles.

--list-name – exact name of the LeetCode list to populate (must already exist).

--dry-run – resolve slugs and print what would be added, but don’t open the browser.

--headless – run Playwright without opening a visible browser window.

(Adjust this section to match the actual CLI in `main.py`.)

## How it works (high level)
### GraphQL search
For each title, call LeetCode’s public GraphQL endpoint to find the best-matching titleSlug.

### Browser automation
Use Playwright to:

- Log in to LeetCode.
- Open each problem’s page.
- Use the “Add to List” UI to add it to the specified list.

### Reporting
Print a summary of:

- Titles successfully added
- Titles not found / ambiguous
- Any errors (network, login, etc.)

## Notes / Caveats
This is best-effort automation. If LeetCode changes their UI, selectors may need updates.

GraphQL search is fuzzy; if a title is weird or misspelled, it might not resolve cleanly.

Don’t hammer the API or the site; there’s a small delay between actions to be polite.

## License
MIT
