# 📱 App Store & Google Play Reviews Scraper (Unified & Multi-App)

Scrape customer reviews and ratings from **Google Play** and the **Apple App Store** for multiple apps in a single run. No login, no accounts, and no API keys required! All reviews are automatically standardized into one clean dataset ready for Excel, Google Sheets, or CSV export.

---

## 🌟 Why Use This Scraper?

- **All-in-One Dual Platform**: Extract reviews from both Android (Google Play) and iOS (Apple App Store) together.
- **Multi-App Batching**: Enter 1 app or 50 apps in a single run.
- **Copy-Paste Friendly**: Paste either raw app IDs or full store URLs (e.g. `https://apps.apple.com/...` or `https://play.google.com/...`) — the scraper extracts the ID automatically!
- **Unified Output**: No need to spend hours reconciling different column formats. Ratings, review text, author names, app versions, dates, and helpful counts come formatted identically.
- **Export Anywhere**: Download results instantly as **Excel (.xlsx)**, **CSV**, **JSON**, or connect directly to **Google Sheets** and webhooks.

---

## 👥 Who Is This For?

- **Non-Technical Marketers & Founders**: Monitor user feedback on your own apps and keep an eye on competitors without writing a line of code.
- **Product Managers & UX Researchers**: Spot common complaints, bug reports, and highly requested features directly from real users.
- **ASO (App Store Optimization) Specialists**: Analyze keywords, user sentiments, and rating trends across store categories.
- **Investors & Analysts**: Evaluate market adoption, brand sentiment, and post-update reactions across an entire product landscape.

---

## 🔍 How to Find Your App IDs (Super Simple!)

You don't need any technical skills to find the app IDs. You can even just copy and paste the full web link!

### 1. Google Play Store (Android)
- Open [play.google.com](https://play.google.com) in your browser and search for your app.
- Look at the web address (URL) in your browser address bar.
- **Option A (Easiest)**: Just copy and paste the **entire link**, for example:  
  `https://play.google.com/store/apps/details?id=com.spotify.music`
- **Option B**: Copy the package name after `id=`, for example:  
  `com.spotify.music` or `com.whatsapp`

### 2. Apple App Store (iOS)
- Open [apps.apple.com](https://apps.apple.com) in your browser and search for your app.
- Look at the address in your browser address bar.
- **Option A (Easiest)**: Just copy and paste the **entire link**, for example:  
  `https://apps.apple.com/us/app/spotify-music-and-podcasts/id324684580`
- **Option B**: Copy the numeric ID at the end of the URL (e.g., `324684580` or `310633997`).

---

## ⚙️ Input Parameters

Configure the scraper in the Apify Console using simple fields:

| Field Name | Type | Default | Description | Example |
|---|---|---|---|---|
| `googlePlayAppIds` | Array / List | `[]` | List of Google Play package IDs or full store URLs | `["com.whatsapp", "com.spotify.music"]` |
| `appleAppIds` | Array / List | `[]` | List of numeric Apple App IDs or full store URLs | `["310633997", "324684580"]` |
| `country` | String | `"us"` | Two-letter country storefront code | `"us"`, `"gb"`, `"in"`, `"de"`, `"ca"` |
| `language` | String | `"en"` | Language code for Google Play reviews | `"en"`, `"es"`, `"fr"`, `"de"` |
| `maxReviewsPerApp` | Integer | `100` | Maximum reviews to retrieve per app (1 to 5,000) | `100` |
| `sortGooglePlay` | Dropdown | `"NEWEST"` | Sort order for Google Play reviews | `NEWEST` or `MOST_RELEVANT` |
| `sortAppStore` | Dropdown | `"mostrecent"` | Sort order for App Store reviews | `mostrecent` or `mosthelpful` |

---

## 📊 Sample Output

Every review is cleaned and structured into a standardized format:

```json
{
  "platform": "app_store",
  "appId": "324684580",
  "appName": "Spotify: Music and Podcasts",
  "rating": 5,
  "title": "Best music streaming service",
  "text": "The recommendations and playlists are spot on. Can't imagine daily commutes without it!",
  "author": "MusicLover99",
  "version": "9.1.86",
  "date": "2026-09-30T18:21:01-07:00",
  "helpfulCount": 12,
  "country": "us",
  "reviewUrl": "https://itunes.apple.com/us/review?id=324684580",
  "scrapedAt": "2026-10-02T12:00:00+00:00"
}
```

### Output Field Explanations

- **`platform`**: Either `google_play` or `app_store`.
- **`appId`**: The unique identifier of the app.
- **`appName`**: The official title of the application.
- **`rating`**: Star rating given by the user (integer from `1` to `5`).
- **`title`**: The review title (App Store provides review headlines; Google Play reviews usually have text only).
- **`text`**: The actual review content written by the user.
- **`author`**: Display name or nickname of the reviewer.
- **`version`**: The app version the user had installed when writing the review.
- **`date`**: Timestamp when the review was posted.
- **`helpfulCount`**: How many users marked this review as helpful / thumbs-up.
- **`country`**: The country storefront where the review was published.
- **`reviewUrl`**: Direct link to the review when available.
- **`scrapedAt`**: Exact UTC timestamp when this record was captured.

---

## 🚀 Step-by-Step Guide for Beginners

1. **Open the Actor**: Navigate to the Actor in your Apify Console.
2. **Add Your Apps**:
   - Paste your Google Play store URLs or package names under **Google Play package names or URLs**.
   - Paste your Apple App Store URLs or IDs under **Apple App Store app IDs or URLs**.
   - You can enter just Google Play apps, just Apple apps, or both!
3. **Choose Options**:
   - Select your target **Country** (e.g. `us` for United States, `gb` for United Kingdom).
   - Set **Max reviews per app** (e.g. `50` or `500`).
4. **Click "Start"**: Watch real-time logs as the scraper pulls reviews.
5. **Export Your Data**: When the run finishes, click the **Export** button in the Dataset tab to download your reviews as an **Excel spreadsheet**, **CSV**, or sync to **Google Sheets**.

---

## 💡 Pro Tips & Automation

- **Automated Scheduling**: Use [Apify Schedules](https://docs.apify.com/platform/schedules) to automatically run this scraper every Monday morning or every day to track newly posted reviews.
- **Instant Alerts via Webhooks**: Connect [Apify Webhooks](https://docs.apify.com/platform/integrations/webhooks) or Zapier / Make.com to get instant Slack or Email notifications whenever a negative 1-star or 2-star review is posted.
- **International Storefronts**: Reviews are segmented by country. If you want global feedback for an app like WhatsApp or Spotify, run the scraper across multiple country codes (`us`, `gb`, `de`, `in`, `br`).

---

## ⚖️ Integrity & Resilience

- **Fault Tolerant**: If an app ID is invalid or has no reviews in a given country, the scraper logs a warning and smoothly continues processing the rest of your apps.
- **Edge Caching Resilient**: Features dual User-Agent and smart URL routing to seamlessly navigate Apple's regional CDN edges.
- **Zero Credentials Needed**: Operates entirely over official public feeds without requiring Google Play or Apple developer credentials.
