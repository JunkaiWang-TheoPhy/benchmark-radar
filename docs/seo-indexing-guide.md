# SEO and indexing guide

Benchmark Radar is not ready to submit to search engines yet. The first job is
to make `https://benchmark-radar.org/` the one reliable public address. Search
engines can index the site after that; submitting an HTTP site with a broken
HTTPS certificate and an old-domain sitemap sends conflicting signals.

## Live status

Last checked: **August 29, 2026**.

| Check | Live result | What to do |
| --- | --- | --- |
| DNS | Apex points to GitHub Pages; `www` points to `ktwu01.github.io` | Keep it |
| GitHub Pages domain | `benchmark-radar.org` is registered and verified | Keep it |
| HTTPS | **Blocked:** the server presents a `*.github.io` certificate | Re-provision the certificate, then enforce HTTPS |
| HTTP redirect | **Blocked:** the apex returns `200` over HTTP | Redirect every HTTP request to HTTPS |
| `robots.txt` | **Stale:** its sitemap URL uses `koutian.is-a.dev` | Deploy the current source |
| `sitemap.xml` | **Stale:** all four URLs use `koutian.is-a.dev` | Regenerate and deploy it |
| Page metadata | The repository source uses the new canonical domain | Deploy and verify the rendered page |

Re-run the checks below after any DNS or Pages change. The table is a dated
snapshot, not a substitute for the live result.

## Fastest path to indexing

### 1. Fix HTTPS before submitting anything

In the GitHub repository, open **Settings → Pages**:

1. Set the custom domain to `benchmark-radar.org` and save it.
2. If it is already saved but the certificate is still wrong, remove the
   custom domain, save, then add it again. This asks GitHub Pages to provision
   the certificate again. GitHub says certificate and DNS changes can take up
   to 24 hours.
3. When it becomes available, enable **Enforce HTTPS**.
4. If a CAA DNS record exists, make sure it permits `letsencrypt.org`.

This project deploys with a custom GitHub Actions workflow, so it does not need
a committed `CNAME` file. The domain configured in **Settings → Pages** is the
important setting.

Verify the result:

```bash
curl -I https://benchmark-radar.org/
curl -I http://benchmark-radar.org/
curl -I https://www.benchmark-radar.org/
```

Pass condition: the first URL has a valid certificate and returns `200`; HTTP
and `www` redirect to `https://benchmark-radar.org/`. Old project URLs should
also end at that HTTPS address, preferably in one redirect.

GitHub references:

- [Manage a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [Troubleshoot custom domains](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages)
- [Secure a Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)

### 2. Deploy and check the canonical-domain files

The repository source is prepared to generate the new-domain metadata, feed,
robots file, and sitemap. After deploying, check the files search crawlers
actually receive:

```bash
curl -fsS https://benchmark-radar.org/robots.txt
curl -fsS https://benchmark-radar.org/sitemap.xml
curl -fsS https://benchmark-radar.org/ | grep -E 'canonical|og:url'
```

Every indexable URL should use `https://benchmark-radar.org`. There should be
no remaining `koutian.is-a.dev/benchmark-radar` or
`ktwu01.github.io/benchmark-radar` URLs in the live HTML, sitemap, feed, blog
posts, or internal links.

Use permanent redirects from both legacy hosts. Redirects are a stronger
canonical signal than a sitemap; combining redirects, `rel="canonical"`, and
consistent internal links makes the migration clearer to crawlers.

### 3. Add Google Search Console

1. Add a **Domain property** named `benchmark-radar.org` (no scheme or path).
2. Copy Google's TXT record into DNS and complete verification. A Domain
   property covers HTTP, HTTPS, the apex, and `www` together.
3. Submit `https://benchmark-radar.org/sitemap.xml` under **Sitemaps**.
4. In **URL Inspection**, test the live homepage and request indexing.
5. Inspect the canonical Google selected after crawling. It should be the HTTPS
   custom-domain URL.

Request indexing once after a meaningful fix. Google says crawling can take
days or weeks, is not guaranteed, and repeated requests do not make it faster.
The sitemap is also a hint, not a guarantee.

Google references:

- [Add a Search Console property](https://support.google.com/webmasters/answer/34592?hl=en)
- [Verify site ownership](https://support.google.com/webmasters/answer/9008080?hl=en)
- [Ask Google to recrawl a page](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)
- [Build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)

### 4. Add Bing Webmaster Tools

Import the verified Search Console property or add the site directly. Submit
the same sitemap, then use **URL Inspection** on the homepage. Bing also accepts
direct URL submissions.

[IndexNow](https://www.indexnow.org/) is optional. It is useful only if the
project wants search engines notified after each successful daily deployment;
it does not replace a sitemap or fix crawlability.

Bing references:

- [Submit URLs to Bing](https://www.bing.com/webmasters/help/URL-Submission-62f2860b)
- [Inspect a URL](https://www.bing.com/webmasters/help/URL-Inspection-55a30305)
- [Submit a sitemap](https://www.bing.com/webmasters/help/sitemaps-3b5cf6ed)

## Make each search result worth indexing

The homepage already supplies the right foundation: a descriptive title and
summary, a canonical URL, social preview metadata, and `WebSite` plus `Dataset`
JSON-LD. Validate the live HTML with Google's
[Rich Results Test](https://search.google.com/test/rich-results) after every
metadata change.

The next improvement is architectural. Today the dashboard views are query
URLs in a JavaScript application:

```text
/?view=leaderboard
/?view=trends
/?view=map
```

They initially return the same HTML and homepage canonical, then JavaScript
changes the title, description, and canonical. Google can render JavaScript,
but its guidance recommends putting a stable canonical in the original HTML
and not changing it to a different value during rendering. This makes separate
indexing of the current query views less dependable.

Choose one clear policy:

- **One indexed landing page now:** keep only the homepage in the sitemap and
  canonicalize dashboard state and filters to it.
- **Distinct search pages later:** publish crawlable paths such as
  `/leaderboard/`, `/trends/`, and `/explore/`. Each should return useful text,
  one descriptive heading, its own title and summary, and its own canonical in
  the initial HTML—not only after JavaScript runs.

Distinct pages are the better route if searches such as “AI benchmark
leaderboard” and “benchmark trends” should land directly on those experiences.
Do not index every filter combination; that creates many thin duplicate URLs.

The heavy dashboard views should also stop depending on a roughly 45 MB JSON
download for their first useful content. Ship a small summary payload or render
the explanatory text before loading the full interactive data. That improves
the reader's first screen and makes rendering cheaper for crawlers.

Google references:

- [JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Canonical URL guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Dataset structured data](https://developers.google.com/search/docs/appearance/structured-data/dataset)

## What to monitor

Check Search Console weekly for the first month after migration:

- **Page indexing:** the homepage is indexed under the HTTPS custom domain.
- **Sitemaps:** the sitemap is readable and its submitted URLs are discovered.
- **URL Inspection:** Google sees the intended canonical and no accidental
  `noindex` directive.
- **Performance:** impressions begin appearing for benchmark-related queries.
- **Core Web Vitals:** heavy dashboard data does not delay the first useful
  content.

Use Search Console as the source of truth. A `site:benchmark-radar.org` search
is a quick spot check, not a complete or authoritative index count.

## Launch checklist

- [ ] Valid TLS certificate for the apex and `www`
- [ ] **Enforce HTTPS** enabled in GitHub Pages
- [ ] HTTP and legacy URLs permanently redirect to the HTTPS custom domain
- [ ] Live `robots.txt`, sitemap, feed, canonicals, and internal links use only
      `https://benchmark-radar.org`
- [ ] Google Search Console Domain property verified
- [ ] Sitemap submitted successfully in Google and Bing
- [ ] Homepage passes live URL inspection and structured-data validation
- [ ] Indexing and performance reviewed after Google recrawls the site
