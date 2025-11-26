# populate_lc_list.py
# automate LeetCode list population via GraphQL API & Playwright browser automation

#!/usr/bin/env python3
import sys
import time
import json
import textwrap
from typing import List, Dict, Optional

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

GRAPHQL_URL = "https://leetcode.com/graphql"

QUERY = textwrap.dedent("""
query problemsetQuestionList($categorySlug: String, $skip: Int, $limit: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    skip: $skip
    limit: $limit
    filters: $filters
  ) {
    questions: data {
      title
      titleSlug
    }
  }
}
""")


def search_slug(title: str) -> Optional[str]:
    # * search LeetCode for given title & return best-matching slug via GraphQL API
    variables = {
        "categorySlug": "",
        "skip": 0,
        "limit": 10,
        "filters": {"searchKeywords": title}
    }

    resp = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers={
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/problemset/all/",
            "User-Agent": "leetcode-list-populator/1.0",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    questions = (
        data
        .get("data", {})
        .get("problemsetQuestionList", {})
        .get("questions", [])
    )

    if not questions:
        return None

    # prefer exact title match if available
    for q in questions:
        if q.get("title", "").strip().lower() == title.strip().lower():
            return q.get("titleSlug")

    # fallback to first result
    return questions[0].get("titleSlug")


def load_config(path: str) -> Dict[str, List[str]]:
    # load configuration from JSON file & validate structure
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # validate that all config values are lists
    for k, v in cfg.items():
        if not isinstance(v, list):
            raise ValueError(f"List '{k}' must map to a list of titles")
    return cfg


def resolve_all_slugs(config: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
    # * resolve all unique problem titles to slugs via LeetCode GraphQL API
    all_titles = sorted({t for titles in config.values() for t in titles})
    print(f"[i] Resolving {len(all_titles)} unique titles to slugs via LeetCode GraphQL...")

    title_to_slug: Dict[str, Optional[str]] = {}
    for title in all_titles:
        slug = search_slug(title)
        title_to_slug[title] = slug
        if slug is None:
            print(f"    [!] NOT FOUND: {title}")
        else:
            print(f"    [✓] {title} -> {slug}")
        # rate limit to avoid overwhelming API
        time.sleep(0.1)

    with open("resolved_slugs.json", "w", encoding="utf-8") as f:
        json.dump(
            [{"title": t, "slug": s} for t, s in title_to_slug.items()],
            f,
            indent=2,
        )
    print("[i] Wrote resolved_slugs.json")
    return title_to_slug


def add_problem_to_list(page, title: str, slug: str, list_name: str, manual_fails: List[dict]):
    # * add problem to specified list using Playwright browser automation
    url = f"https://leetcode.com/problems/{slug}/"
    print(f"[+] {list_name}: {title} -> {url}")

    # navigate to problem page
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except PWTimeoutError:
        print(f"    [!] Timeout loading {url}, marking for manual add")
        manual_fails.append({
            "list": list_name,
            "title": title,
            "slug": slug,
            "reason": "goto_timeout"
        })
        return

    # allow React to hydrate
    page.wait_for_timeout(500)

    # click star icon to open list popover
    try:
        star = page.locator("svg[data-icon='star']").first
        star.click(timeout=5000)
    except PWTimeoutError:
        print(f"    [!] Could not find star icon for {slug}, marking for manual add")
        manual_fails.append({
            "list": list_name,
            "title": title,
            "slug": slug,
            "reason": "star_not_found"
        })
        return

    # allow popover to render
    page.wait_for_timeout(200)

    # find existing list row or create new list
    list_row = page.locator(
        "div.flex.w-full.cursor-pointer"
    ).filter(has_text=list_name)

    if list_row.count() == 0:
        # list doesn't exist, create it
        print(f"    [i] List '{list_name}' not found, creating...")

        try:
            # Row at the bottom: <div class="text-md ..."> ... Create a new list
            create_row = page.locator(
                "div.text-md",
                has_text="Create a new list"
            ).first
            create_row.click(timeout=4000)
        except PWTimeoutError:
            print(f"    [!] Could not click 'Create a new list' for {slug}, marking for manual add")
            manual_fails.append({
                "list": list_name,
                "title": title,
                "slug": slug,
                "reason": "create_row_not_found"
            })
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return

        # fill list name & click create button
        try:
            overlay = page.locator("div.bg-sd-popover").filter(
                has_text="Create a new list"
            ).first

            input_box = overlay.get_by_placeholder("Enter a list name")
            input_box.fill(list_name)

            # let button enable
            page.wait_for_timeout(200)

            create_btn = overlay.get_by_role("button", name="Create")
            create_btn.click(timeout=5000)
        except PWTimeoutError:
            print(f"    [!] Failed to create list '{list_name}' for {slug}, marking for manual add")
            manual_fails.append({
                "list": list_name,
                "title": title,
                "slug": slug,
                "reason": "create_click_failed"
            })
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return

        page.wait_for_timeout(400)
        # LeetCode auto-adds problem to newly created list
        print(f"    [✓] Created list '{list_name}' and added '{title}'")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return

    # list exists, toggle checkbox if needed
    try:
        row = list_row.first
        checkbox = row.locator("button[role='checkbox']").first
        state = checkbox.get_attribute("aria-checked") or "false"

        if state == "true":
            print(f"    [•] Already in list '{list_name}'")
        else:
            checkbox.click(timeout=4000)
            page.wait_for_timeout(200)
            print(f"    [✓] Added to list '{list_name}'")
    except PWTimeoutError:
        print(f"    [!] Failed to toggle checkbox for '{list_name}' on {slug}, marking for manual add")
        manual_fails.append({
            "list": list_name,
            "title": title,
            "slug": slug,
            "reason": "checkbox_toggle_failed"
        })
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return

    # close popover
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def main():
    # * main entry point: load config, resolve slugs, & populate lists via browser automation
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} mega_config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    config = load_config(config_path)
    print(f"[i] Loaded {len(config)} lists from {config_path}")

    title_to_slug = resolve_all_slugs(config)

    manual_fails: List[dict] = []

    with sync_playwright() as p:
        # use persistent profile to remember cookies & login across runs
        context = p.chromium.launch_persistent_context(
            user_data_dir="leetcode_profile",
            headless=False,
        )
        page = context.new_page()
        page.goto("https://leetcode.com", wait_until="domcontentloaded")

        input("[i] Once you are logged in (if needed), press Enter to continue...")

        for list_name, titles in config.items():
            print(f"\n===== Processing list: {list_name} ({len(titles)} problems) =====")
            for title in titles:
                slug = title_to_slug.get(title)
                if not slug:
                    print(f"    [!] No slug for '{title}', marking for manual add")
                    manual_fails.append({
                        "list": list_name,
                        "title": title,
                        "slug": None,
                        "reason": "slug_not_found"
                    })
                    continue

                try:
                    add_problem_to_list(page, title, slug, list_name, manual_fails)
                except Exception as e:
                    print(f"    [!] Unexpected error while processing '{title}' ({slug}): {e}")
                    manual_fails.append({
                        "list": list_name,
                        "title": title,
                        "slug": slug,
                        "reason": f"unexpected: {repr(e)}"
                    })

                # small delay between problems
                page.wait_for_timeout(250)

        print("\n[i] Done with all lists.")
        context.close()

    if manual_fails:
        with open("manual_fails.json", "w", encoding="utf-8") as f:
            json.dump(manual_fails, f, indent=2)
        print(f"[i] Wrote manual_fails.json with {len(manual_fails)} entries that need manual fixing.")
        print("    Quick summary:")
        for item in manual_fails:
            print(f"    - {item['list']}: {item['title']} ({item.get('reason')})")
    else:
        print("[i] No manual failures 🎉")


if __name__ == "__main__":
    main()
