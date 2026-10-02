import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from apify import Actor
from google_play_scraper import Sort as GPSort
from google_play_scraper import app as gp_app
from google_play_scraper import reviews as gp_reviews

APPLE_LOOKUP_URL = "https://itunes.apple.com/lookup"
APPLE_BASE_URL = "https://itunes.apple.com"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CURL_UA = "curl/8.4.0"

USER_AGENTS = [BROWSER_UA, CURL_UA]

GP_SORT_MAP = {
    "NEWEST": GPSort.NEWEST,
    "MOST_RELEVANT": GPSort.MOST_RELEVANT,
}


def extract_google_play_id(raw: Any) -> str:
    """Accepts a package name or full play.google.com URL and returns the clean package ID."""
    raw_str = str(raw).strip()
    match = re.search(r"[?&]id=([a-zA-Z0-9._]+)", raw_str)
    if match:
        return match.group(1)
    match_slash = re.search(r"details/([a-zA-Z0-9._]+)", raw_str)
    if match_slash:
        return match_slash.group(1)
    return raw_str


def extract_apple_id(raw: Any) -> str:
    """Accepts a numeric Apple ID, 'id'-prefixed ID, or full apps.apple.com URL."""
    raw_str = str(raw).strip()
    match = re.search(r"id(\d+)", raw_str)
    if match:
        return match.group(1)
    match_digits = re.search(r"(\d+)", raw_str)
    if match_digits:
        return match_digits.group(1)
    return raw_str


def _normalize_app_list(val: Any) -> list[str]:
    """Handles list, tuple, comma-separated, or newline-separated app identifiers."""
    if not val:
        return []
    if isinstance(val, str):
        items = re.split(r"[,\n\r]+", val)
        return [i.strip() for i in items if i.strip()]
    if isinstance(val, (list, tuple, set)):
        items = []
        for x in val:
            if isinstance(x, str) and ("," in x or "\n" in x):
                items.extend([sub.strip() for sub in re.split(r"[,\n\r]+", x) if sub.strip()])
            elif x:
                items.append(str(x).strip())
        return items
    return [str(val).strip()]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _get_label(obj: Any) -> str | None:
    if isinstance(obj, dict):
        val = obj.get("label")
        return str(val) if val is not None else None
    elif isinstance(obj, (str, int, float)):
        return str(obj)
    return None


async def scrape_google_play(
    raw_app_id: str,
    country: str,
    lang: str,
    max_reviews: int,
    sort_key: str,
) -> list[dict]:
    app_id = extract_google_play_id(raw_app_id)
    sort = GP_SORT_MAP.get(sort_key, GPSort.NEWEST)

    def _fetch():
        meta = {}
        try:
            meta = gp_app(app_id, lang=lang, country=country)
        except Exception as e:
            Actor.log.warning(f"[google_play] Metadata lookup failed for {app_id}: {e}")

        collected = []
        token = None
        while len(collected) < max_reviews:
            fetch_count = min(200, max_reviews - len(collected))
            try:
                batch, token = gp_reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=sort,
                    count=fetch_count,
                    continuation_token=token,
                )
            except Exception as e:
                Actor.log.warning(f"[google_play] Error fetching review batch for {app_id}: {e}")
                break

            if not batch:
                break

            collected.extend(batch)
            if token is None or token.token is None:
                break

        return meta, collected[:max_reviews]

    meta, raw_reviews = await asyncio.to_thread(_fetch)
    app_name = meta.get("title") if meta else None
    scraped_at = datetime.now(timezone.utc).isoformat()

    return [
        {
            "platform": "google_play",
            "appId": app_id,
            "appName": app_name,
            "rating": _safe_int(r.get("score")),
            "title": None,
            "text": r.get("content"),
            "author": r.get("userName"),
            "version": r.get("reviewCreatedVersion") or r.get("appVersion"),
            "date": _iso(r.get("at")),
            "helpfulCount": _safe_int(r.get("thumbsUpCount")),
            "country": country,
            "reviewUrl": None,
            "scrapedAt": scraped_at,
        }
        for r in raw_reviews
    ]


def _build_apple_urls(country: str, app_id: str, page: int, sort: str) -> list[str]:
    """Generates candidate Apple RSS URLs ordered by compatibility."""
    is_helpful = "help" in sort.lower()

    if is_helpful:
        sort_slugs = [
            "sortby=mosthelpful",
            "sortBy=mostHelpful",
            "sortby=mostHelpful",
            "sortBy=mosthelpful",
            "sortby=mostrecent",
            "sortBy=mostRecent",
            "sortby=mostRecent",
        ]
    else:
        sort_slugs = [
            "sortby=mostrecent",
            "sortBy=mostRecent",
            "sortby=mostRecent",
            "sortby=mosthelpful",
            "sortBy=mostHelpful",
        ]

    urls = []
    # Standard format: page=X/...
    for slug in sort_slugs:
        urls.append(f"{APPLE_BASE_URL}/{country}/rss/customerreviews/page={page}/id={app_id}/{slug}/json")

    # If page == 1, also check path without page=1
    if page == 1:
        for slug in sort_slugs:
            urls.append(f"{APPLE_BASE_URL}/{country}/rss/customerreviews/id={app_id}/{slug}/json")
        urls.append(f"{APPLE_BASE_URL}/{country}/rss/customerreviews/page=1/id={app_id}/json")
        urls.append(f"{APPLE_BASE_URL}/{country}/rss/customerreviews/id={app_id}/json")

    return urls


async def _fetch_apple_entries(
    client: httpx.AsyncClient,
    candidate_urls: list[str],
) -> tuple[list[dict], str | None]:
    """Tries candidate URLs across browser and curl User-Agents until reviews are found."""
    for ua in USER_AGENTS:
        headers = {"User-Agent": ua}
        for url in candidate_urls:
            try:
                resp = await client.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                raw_entries = data.get("feed", {}).get("entry", [])
                if isinstance(raw_entries, dict):
                    raw_entries = [raw_entries]
                elif not isinstance(raw_entries, list):
                    raw_entries = []

                valid_entries = [e for e in raw_entries if isinstance(e, dict) and "im:rating" in e]
                if valid_entries:
                    return valid_entries, url
            except Exception:
                continue

    return [], None


async def scrape_app_store(
    raw_app_id: str,
    country: str,
    max_reviews: int,
    sort: str,
    client: httpx.AsyncClient,
) -> list[dict]:
    app_id = extract_apple_id(raw_app_id)
    scraped_at = datetime.now(timezone.utc).isoformat()

    # App metadata lookup
    app_name = None
    try:
        resp = await client.get(
            APPLE_LOOKUP_URL,
            params={"id": app_id, "country": country},
            headers={"User-Agent": BROWSER_UA},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("resultCount", 0) > 0:
                app_name = data["results"][0].get("trackName")
    except Exception as e:
        Actor.log.warning(f"[app_store] Metadata lookup failed for {app_id}: {e}")

    results: list[dict] = []
    seen_ids: set[str] = set()
    page = 1
    max_pages = min(10, (max_reviews + 49) // 50)
    working_slug: str | None = None

    while len(results) < max_reviews and page <= max_pages:
        candidate_urls = []
        if working_slug:
            candidate_urls.append(
                f"{APPLE_BASE_URL}/{country}/rss/customerreviews/page={page}/id={app_id}/{working_slug}/json"
            )
        candidate_urls.extend(_build_apple_urls(country, app_id, page, sort))

        entries, used_url = await _fetch_apple_entries(client, candidate_urls)

        if not entries:
            Actor.log.debug(f"[app_store] No reviews returned for {app_id} on page {page}.")
            break

        # Save successful slug pattern for subsequent pages
        if used_url and not working_slug:
            for s in [
                "sortBy=mostRecent",
                "sortby=mostRecent",
                "sortby=mostrecent",
                "sortBy=mostHelpful",
                "sortby=mosthelpful",
            ]:
                if s in used_url:
                    working_slug = s
                    break

        new_on_page = 0
        for entry in entries:
            review_id = _get_label(entry.get("id"))
            if review_id and review_id in seen_ids:
                continue
            if review_id:
                seen_ids.add(review_id)

            link_obj = entry.get("link")
            review_url = None
            if isinstance(link_obj, dict):
                review_url = link_obj.get("attributes", {}).get("href")
            elif isinstance(link_obj, list) and link_obj:
                first = link_obj[0]
                if isinstance(first, dict):
                    review_url = first.get("attributes", {}).get("href")

            author_obj = entry.get("author")
            author_name = None
            if isinstance(author_obj, dict):
                author_name = _get_label(author_obj.get("name"))
            elif isinstance(author_obj, str):
                author_name = author_obj

            results.append({
                "platform": "app_store",
                "appId": app_id,
                "appName": app_name,
                "rating": _safe_int(_get_label(entry.get("im:rating"))),
                "title": _get_label(entry.get("title")),
                "text": _get_label(entry.get("content")),
                "author": author_name,
                "version": _get_label(entry.get("im:version")),
                "date": _get_label(entry.get("updated")),
                "helpfulCount": _safe_int(_get_label(entry.get("im:voteSum"))),
                "country": country,
                "reviewUrl": review_url,
                "scrapedAt": scraped_at,
            })
            new_on_page += 1
            if len(results) >= max_reviews:
                break

        if new_on_page == 0:
            break

        page += 1

    return results[:max_reviews]


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}

        google_raw = actor_input.get("googlePlayAppIds")
        apple_raw = actor_input.get("appleAppIds")

        google_apps = _normalize_app_list(google_raw)
        apple_apps = _normalize_app_list(apple_raw)

        country = str(actor_input.get("country") or "us").strip().lower()
        lang = str(actor_input.get("language") or "en").strip().lower()
        max_reviews = _safe_int(actor_input.get("maxReviewsPerApp"), default=100)
        sort_gp = str(actor_input.get("sortGooglePlay") or "NEWEST").strip().upper()
        sort_as = str(actor_input.get("sortAppStore") or "mostrecent").strip().lower()

        if not google_apps and not apple_apps:
            Actor.log.warning(
                "No apps specified! Please provide at least one app in 'googlePlayAppIds' or 'appleAppIds'."
            )
            return

        Actor.log.info(
            f"Starting scraper run: {len(google_apps)} Google Play app(s), {len(apple_apps)} App Store app(s). "
            f"Country: '{country}', Max reviews/app: {max_reviews}"
        )

        total_pushed = 0

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Process Google Play apps
            for raw_id in google_apps:
                clean_id = extract_google_play_id(raw_id)
                Actor.log.info(f"[google_play] Scraping '{clean_id}' (country: {country}, lang: {lang})...")
                try:
                    records = await scrape_google_play(clean_id, country, lang, max_reviews, sort_gp)
                except Exception as e:
                    Actor.log.error(f"[google_play] Failed to scrape {clean_id}: {e}")
                    continue

                if records:
                    await Actor.push_data(records)
                    total_pushed += len(records)
                    Actor.log.info(f"[google_play] Successfully saved {len(records)} reviews for '{clean_id}'.")
                else:
                    Actor.log.warning(f"[google_play] 0 reviews found for '{clean_id}'.")

            # Process Apple App Store apps
            for raw_id in apple_apps:
                clean_id = extract_apple_id(raw_id)
                Actor.log.info(f"[app_store] Scraping '{clean_id}' (country: {country})...")
                try:
                    records = await scrape_app_store(clean_id, country, max_reviews, sort_as, client)
                except Exception as e:
                    Actor.log.error(f"[app_store] Failed to scrape {clean_id}: {e}")
                    continue

                if records:
                    await Actor.push_data(records)
                    total_pushed += len(records)
                    Actor.log.info(f"[app_store] Successfully saved {len(records)} reviews for '{clean_id}'.")
                else:
                    Actor.log.warning(f"[app_store] 0 reviews found for '{clean_id}'.")

        Actor.log.info(
            f"All done! Total reviews collected & pushed: {total_pushed} across {len(google_apps) + len(apple_apps)} app(s)."
        )


if __name__ == "__main__":
    asyncio.run(main())
