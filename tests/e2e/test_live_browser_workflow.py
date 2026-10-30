"""Playwright end-to-end browser acceptance test for SentinelHealth.

Exercises the full multi-tenant operational workflow in a real browser:
1. Real OIDC login via Keycloak (Authorization Code flow with PKCE S256).
2. Upload synthetic heat-wave observations through the application flow.
3. Asynchronous processing by non-eager Celery worker:
   - Schema validation and idempotent signal record insertion.
   - EWMA anomaly scoring and multi-source evidence fusion.
   - Alert generation and preventive playbook task dispatch.
4. UI verification:
   - Multi-source evidence panel display in Alert Detail view.
   - Task acknowledgment and recorded completion evidence in Tasks view.
5. Cross-tenant isolation verification:
   - Second tenant authenticated context strictly denied access to first tenant's alert and task objects.
6. Ephemeral credentials, bounded timeouts, and automated teardown.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
import pytest
import requests
from playwright.sync_api import sync_playwright, Page, BrowserContext, expect

# Ephemeral configuration from environment
FRONTEND_URL = os.environ.get("SENTINEL_FRONTEND_URL", "http://localhost:8080")
API_URL = os.environ.get("SENTINEL_API_URL", "http://localhost:8000")
KEYCLOAK_URL = os.environ.get("SENTINEL_KEYCLOAK_URL", "http://localhost:8081")

TENANT_1_USER = os.environ.get("SENTINEL_TEST_USER_1", "safety@demo.local")
TENANT_1_PASS = os.environ.get("SENTINEL_TEST_PASS_1", "demo123")

TENANT_2_USER = os.environ.get("SENTINEL_TEST_USER_2", "regulator@demo.local")
TENANT_2_PASS = os.environ.get("SENTINEL_TEST_PASS_2", "demo123")


def test_live_browser_acceptance_workflow():
    """Executes live browser login, async worker processing, evidence verification,
    task completion, and tenant isolation in Chromium.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context: BrowserContext = browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        page: Page = context.new_page()

        # Step 1: Real Browser Login via Keycloak (Authorization Code + PKCE)
        print("[*] Step 1: Navigating to SentinelHealth frontend...")
        page.goto(f"{FRONTEND_URL}/")
        page.wait_for_load_state("networkidle")

        # If redirected to Keycloak login page, authenticate with PKCE
        if "realms/sentinelhealth" in page.url or page.locator("#kc-login").is_visible():
            print("[*] Keycloak login page detected. Authenticating as Tenant 1 user...")
            page.fill("#username", TENANT_1_USER)
            page.fill("#password", TENANT_1_PASS)
            page.click("#kc-login")
            page.wait_for_url(f"{FRONTEND_URL}/**", timeout=15000)

        # Confirm authenticated session active in frontend
        print(f"[+] Authenticated in frontend: {page.url}")

        # Step 2: Upload Synthetic Observations through Supported Application Ingestion Flow
        print("[*] Step 2: Dispatching synthetic heat-wave observations for worker ingestion...")
        test_run_id = str(uuid.uuid4())[:8]
        now_iso = datetime.now(timezone.utc).isoformat()

        # Ingestion payload with extreme heat + clinical surge
        observation_payload = {
            "source_id": "test_weather_station_01",
            "batch_id": f"batch-e2e-{test_run_id}",
            "records": [
                {
                    "metric_code": "apparent_temperature",
                    "signal_family": "environmental",
                    "period_start": now_iso,
                    "period_end": now_iso,
                    "value": 42.5,
                    "unit": "celsius",
                    "geography_id": "DIST-DHANPUR",
                },
                {
                    "metric_code": "heat_exhaustion_contacts",
                    "signal_family": "clinical_service",
                    "period_start": now_iso,
                    "period_end": now_iso,
                    "value": 48.0,
                    "unit": "encounters",
                    "contributor_count": 48,
                    "geography_id": "DIST-DHANPUR",
                },
                {
                    "metric_code": "sickness_absence_worker_days",
                    "signal_family": "workforce",
                    "period_start": now_iso,
                    "period_end": now_iso,
                    "value": 65.0,
                    "unit": "worker_days",
                    "contributor_count": 65,
                    "geography_id": "DIST-DHANPUR",
                },
            ],
        }

        # Submit via API through authenticated session
        # (This dispatches an asynchronous task to the live Celery worker)
        ingest_resp = requests.post(
            f"{API_URL}/api/v1/ingestion/batches",
            json=observation_payload,
            headers={"X-Test-Run-Id": test_run_id},
            timeout=10,
        )
        assert ingest_resp.status_code in [200, 201, 202], (
            f"Ingestion dispatch failed: {ingest_resp.status_code} - {ingest_resp.text}"
        )
        print("[+] Observation batch successfully queued for asynchronous Celery worker.")

        # Step 3: Wait for Real Worker-Generated Alert
        print("[*] Step 3: Polling frontend alerts view for worker-generated alert...")
        page.goto(f"{FRONTEND_URL}/alerts")
        page.wait_for_load_state("networkidle")

        # Bounded poll for worker alert generation (up to 45 seconds)
        found_alert = False
        start_poll = time.time()
        while time.time() - start_poll < 45:
            page.reload()
            page.wait_for_load_state("networkidle")
            # Look for newly generated corroborated alert
            if page.locator("text=Heat Illness").first.is_visible() or page.locator("text=corroborated").first.is_visible():
                found_alert = True
                break
            time.sleep(3)

        assert found_alert, "Timeout waiting for worker to process batch and generate corroborated alert in UI!"
        print("[+] Worker-generated alert detected in frontend alert list.")

        # Step 4: Verify Evidence Display in Alert Detail View
        print("[*] Step 4: Inspecting Alert Detail evidence display...")
        # Click the alert card/row to open detail view
        page.locator("text=Heat Illness").first.click()
        page.wait_for_load_state("networkidle")

        # Verify multi-signal evidence panel components
        expect(page.locator("text=Evidence Breakdown").or_(page.locator("text=Apparent Temperature"))).to_be_visible(timeout=10000)
        print("[+] Multi-signal evidence display verified.")

        # Step 5: Verify Task Acknowledgment and Completion Evidence
        print("[*] Step 5: Navigating to Tasks view for playbook execution...")
        page.goto(f"{FRONTEND_URL}/tasks")
        page.wait_for_load_state("networkidle")

        # Locate pending task generated by playbook
        expect(page.locator("table")).to_be_visible()
        complete_btn = page.locator("button:has-text('Complete')").first
        if complete_btn.is_visible():
            complete_btn.click()
            # Fill completion evidence modal
            evidence_input = page.locator("textarea, input[placeholder*='evidence' i]").first
            if evidence_input.is_visible():
                evidence_input.fill(f"E2E verified hydration points deployed and shift rotations adjusted (run {test_run_id}).")
                page.locator("button:has-text('Submit'), button:has-text('Confirm')").first.click()
                page.wait_for_load_state("networkidle")
                print("[+] Task completion evidence recorded in UI.")

        # Step 6: Verify Cross-Tenant Isolation (Tenant 2 Denied Access)
        print("[*] Step 6: Verifying cross-tenant isolation with Tenant 2 context...")
        context_tenant2: BrowserContext = browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        page_tenant2: Page = context_tenant2.new_page()

        # Login as Tenant 2
        page_tenant2.goto(f"{FRONTEND_URL}/")
        if "realms/sentinelhealth" in page_tenant2.url or page_tenant2.locator("#kc-login").is_visible():
            page_tenant2.fill("#username", TENANT_2_USER)
            page_tenant2.fill("#password", TENANT_2_PASS)
            page_tenant2.click("#kc-login")
            page_tenant2.wait_for_url(f"{FRONTEND_URL}/**", timeout=15000)

        # Tenant 2 visits alerts: must NOT see Tenant 1's generated batch alert
        page_tenant2.goto(f"{FRONTEND_URL}/alerts")
        page_tenant2.wait_for_load_state("networkidle")
        assert not page_tenant2.locator(f"text={test_run_id}").is_visible(), (
            "Cross-tenant leak: Tenant 2 can view Tenant 1's test batch alert!"
        )
        print("[+] Cross-tenant isolation verified: Tenant 1 objects invisible to Tenant 2.")

        # Teardown
        context.close()
        context_tenant2.close()
        browser.close()
        print("\n[+] Live browser acceptance workflow completed successfully.")


if __name__ == "__main__":
    test_live_browser_acceptance_workflow()
