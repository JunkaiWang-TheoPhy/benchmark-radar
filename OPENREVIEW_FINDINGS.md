# OpenReview API v2 Authentication Investigation

## Issue
Unauthenticated requests to `https://api2.openreview.net/notes?venueid=...` return HTTP 403 `ChallengeRequiredError` with a Cloudflare Turnstile challenge URL.

## Findings

### 1. Challenge is Universal (Not IP-Based)
| Source | Result |
|--------|--------|
| GitHub Actions (datacenter IP) | ChallengeRequiredError |
| Residential IP (local machine) | ChallengeRequiredError |

**Conclusion**: The challenge applies to ALL unauthenticated requests to `/notes` endpoint, not just datacenter IPs.

### 2. Authentication Works with Correct Parameters
Using `openreview-py` client v2.4.2 with valid credentials:

```python
import openreview
client = openreview.api.OpenReviewClient(
    baseurl='https://api2.openreview.net',
    username='ktwu@utexas.edu',
    password='...'
)
notes = client.get_notes(invitation='ICLR.cc/2026/Conference/-/Submission', limit=5)
# Returns 3 notes successfully
```

**Key finding**: The `venueid` query parameter is NOT supported by the official client. The correct parameter is `invitation` with the full submission invitation ID.

### 3. Working Invitation IDs for ICLR 2026
| Invitation ID | Notes Returned |
|---------------|----------------|
| `ICLR.cc/2026/Conference/-/Submission` | ✅ 3 notes |
| `ICLR.cc/2026/Conference/-/Blind_Submission` | 0 notes |
| `ICLR.cc/2026/Conference/-/Conference_Submission` | 0 notes |
| `ICLR.cc/2026/Conference` (bare) | 0 notes |

### 4. GitHub Actions Authentication Issue
The workflow fails with "Invalid username or password" - likely due to special characters in the password being mangled by shell expansion in the inline script.

## Recommended Fix for benchmark-radar

### Option A: Use openreview-py client (Recommended)
Update `sources.py` to use the official client:

```python
import openreview

def fetch_openreview(config, since, limit):
    client = openreview.api.OpenReviewClient(
        baseurl='https://api2.openreview.net',
        username=os.getenv('OPENREVIEW_USERNAME'),
        password=os.getenv('OPENREVIEW_PASSWORD'),
    )
    
    for venue in config.get('venues', []):
        # Map venue to correct invitation ID
        invitation = f"{venue}/-/Submission"  # or Blind_Submission
        notes = client.get_notes(invitation=invitation, limit=limit)
        # ... process notes
```

### Option B: Use authenticated session cookies
Login via client, extract cookies, use in existing `get_json` calls with `venueid` param.

## Questions for OpenReview Support

1. Is `venueid` query parameter deprecated/unsupported for automation?
2. What is the official mapping from venue ID (e.g., `ICLR.cc/2026/Conference`) to submission invitation ID?
3. Is there a supported way to query by `venueid` with authentication?
4. Can you document the expected automation path for CI/CD systems?

## Reproduction
```bash
# Unauthenticated (fails with ChallengeRequiredError)
curl "https://api2.openreview.net/notes?venueid=ICLR.cc/2026/Conference&limit=1"

# Authenticated via openreview-py with correct invitation (works)
python -c "
import openreview
client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net', username=..., password=...)
notes = client.get_notes(invitation='ICLR.cc/2026/Conference/-/Submission', limit=1)
print(notes[0].id)
"
```