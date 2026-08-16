#!/usr/bin/env python3
"""Test OpenReview authentication in GitHub Actions."""

import os

import openreview


def main():
    username = os.getenv("OPENREVIEW_USERNAME")
    password = os.getenv("OPENREVIEW_PASSWORD")

    if not username or not password:
        print("ERROR: OPENREVIEW_USERNAME or OPENREVIEW_PASSWORD not set")
        return 1

    print(f"Username: {username}")
    print(f"Password length: {len(password)}")

    client = openreview.api.OpenReviewClient(
        baseurl="https://api2.openreview.net",
        username=username,
        password=password,
    )

    # Test with the working invitation ID
    invitation = "ICLR.cc/2026/Conference/-/Submission"
    notes = client.get_notes(invitation=invitation, limit=5)
    print(f"SUCCESS: Got {len(notes)} notes from {invitation}")
    
    for n in notes:
        title = n.content.get("title", {}).get("value", "N/A")
        print(f"  {n.id}: {title[:80]}")
    
    return 0

if __name__ == "__main__":
    exit(main())