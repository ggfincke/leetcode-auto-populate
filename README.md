# leetcode-auto-populate

Automation script that takes a JSON config of list names -> LeetCode problem titles, resolves each title through LeetCode’s GraphQL API, and drives a real Chromium browser (Playwright) to add those problems to your custom lists.

## Features

- Deduplicates every title across all lists and resolves them to `titleSlug`s via GraphQL.
- Stores all resolved slugs in `resolved_slugs.json` for auditing.
- Uses a persistent Playwright profile so you stay logged in between runs.
- Creates missing custom lists on the fly and skips titles that are already present.
- Writes any problems that could not be added to `manual_fails.json` for manual follow-up.

## Requirements

- Python 3.10+
- `pip` (a virtualenv is recommended but optional)
- Playwright plus browser binaries (`playwright install chromium`)
- A LeetCode account you can log into via a normal browser session

## Installation

```bash
git clone https://github.com/<your-username>/leetcode-auto-populate.git
cd leetcode-auto-populate

# optional but recommended
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

## Configuration

Provide a JSON file that maps list names to arrays of human-readable problem titles. See `example_config.json` for a template:

```json
{
  "Blind 75": [
    "Two Sum",
    "Best Time to Buy and Sell Stock"
  ],
  "Dynamic Programming": [
    "Climbing Stairs",
    "House Robber"
  ]
}
```

Notes:

- Titles are matched case-insensitively, but spelling must match LeetCode’s titles.
- The loader enforces that every list maps to an array; any other structure raises an error.
- Each unique title is resolved once even if it appears in multiple lists.

## Running the script

```bash
python populate_lc_list.py path/to/your_config.json
```

What to expect:

1. The script validates the config, resolves all titles, and writes `resolved_slugs.json`.
2. Playwright launches Chromium using the persistent profile in `leetcode_profile/`.
3. When prompted (`press Enter to continue`), log into LeetCode in the opened browser (only needed once per profile) and hit Enter in the terminal.
4. For every list:
   - Missing lists are created automatically through the “Create a new list” dialog.
   - Already-added problems are detected via the checkbox state and skipped.
   - Failures (timeouts, selectors not found, slug lookup issues, etc.) are appended to `manual_fails.json`.

When the run finishes you’ll see a summary of any titles that still need manual attention. If there were no failures the script prints a 🎉 and removes the need for manual edits.

## Output files

- `resolved_slugs.json` – All titles with the slug that was used (or `null` if not found).
- `manual_fails.json` – Titles that could not be added automatically, with the reason.
- `leetcode_profile/` – Playwright user data directory so you stay logged in between runs.

## How it works

1. **GraphQL search** – Each title is sent to `https://leetcode.com/graphql` using the `questionList` query; the script prefers exact matches and falls back to the first result.
2. **Browser automation** – Playwright opens each problem URL, clicks the star/list icon, creates the list if missing, and toggles the checkbox for the specified list.
3. **Reporting** – Progress is printed to the terminal while JSON files capture successes and failures for later review.

## Tips & caveats

- Keep an eye on the terminal while the browser runs; if LeetCode changes their UI, selector tweaks may be required.
- There is a small delay between actions to avoid hammering the site, but you should still be courteous with the number of problems per run.
- If you want to start fresh, delete `leetcode_profile/` and you’ll be prompted to log in again on the next run.

## License

MIT – see `LICENSE`.
