#!/usr/bin/env python3
"""
Capture screenshots of Grafana dashboards for README documentation.
Uses Playwright to navigate and capture live dashboard views.
"""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def capture_grafana_screenshots():
    """Capture screenshots of the main Grafana dashboards."""
    
    # Configuration - require environment variables (no hardcoded defaults per AGENTS.md)
    grafana_url = os.environ.get("GRAFANA_URL")
    username = os.environ.get("GRAFANA_USERNAME")
    password = os.environ.get("GRAFANA_PASSWORD")
    
    if not all([grafana_url, username, password]):
        raise ValueError(
            "GRAFANA_URL, GRAFANA_USERNAME, and GRAFANA_PASSWORD environment variables must be set. "
            "See AGENTS.md: Secrets must never be committed, logged, or copied into artifacts."
        )
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "docs" / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Dashboards to capture (based on README references)
    # Note: experiment-summary uses $experiment variable - set to seeded experiment name
    dashboards = [
        {
            "name": "Live Request Latency",
            "uid": "live-latency",
            "output": "grafana-live-request-latency.png",
            "params": {}
        },
        {
            "name": "Live TTFT Metrics",
            "uid": "live-ttft",
            "output": "grafana-live-ttft-metrics.png",
            "params": {}
        },
        {
            "name": "Live Error Rate",
            "uid": "live-error-rate",
            "output": "grafana-live-error-rate.png",
            "params": {}
        },
        {
            "name": "Experiment Summary",
            "uid": "experiment-summary",
            "output": "grafana-experiment-summary.png",
            "params": {"var-experiment": "demo-grafana-validation"}
        }
    ]
    
    screenshots_captured = []
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2  # Higher resolution for better quality
        )
        page = context.new_page()
        
        try:
            # Navigate to Grafana
            print(f"Navigating to Grafana at {grafana_url}")
            page.goto(grafana_url, wait_until="networkidle", timeout=30000)
            
            # Handle login if presented
            if page.locator('input[name="user"]').count() > 0:
                print("Logging in with default credentials")
                page.locator('input[name="user"]').fill(username)
                page.locator('input[name="password"]').fill(password)
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state("networkidle", timeout=10000)
                
                # Skip password change prompt if presented
                try:
                    skip_button = page.locator('button:has-text("Skip")')
                    if skip_button.count() > 0:
                        skip_button.click()
                        page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
            
            # Capture each dashboard
            for dashboard in dashboards:
                print(f"\nCapturing dashboard: {dashboard['name']}")
                
                # Build URL with query parameters
                dashboard_url = f"{grafana_url}/d/{dashboard['uid']}"
                if dashboard['params']:
                    query_string = "&".join(f"{k}={v}" for k, v in dashboard['params'].items())
                    dashboard_url = f"{dashboard_url}?{query_string}"
                
                print(f"  URL: {dashboard_url}")
                
                try:
                    # Create a new page for each dashboard to avoid caching issues
                    page = context.new_page()
                    
                    # Navigate to the specific dashboard
                    page.goto(dashboard_url, wait_until="networkidle", timeout=30000)
                    
                    # Wait for dashboard to fully render
                    print(f"  Waiting for dashboard to render...")
                    time.sleep(5)
                    
                    # Verify we're on the correct dashboard by checking URL
                    current_url = page.url
                    if dashboard['uid'] not in current_url:
                        print(f"  Warning: URL mismatch. Expected uid {dashboard['uid']}, got {current_url}")
                    
                    # Wait for panels to show content (check for canvas elements)
                    try:
                        # Wait for at least one panel to render with data
                        page.wait_for_selector('div.panel-content', timeout=10000)
                        # Additional wait for charts to render
                        time.sleep(3)
                    except Exception:
                        print(f"  Warning: Timeout waiting for panel content")
                    
                    # Set time range to last 1 hour for consistent view
                    try:
                        time_picker = page.locator('[aria-label="Time picker"]')
                        if time_picker.count() > 0:
                            time_picker.click()
                            page.wait_for_timeout(500)
                            
                            # Select "Last 1 hour"
                            last_1h = page.locator('text=/Last 1 hour/i')
                            if last_1h.count() > 0:
                                last_1h.first.click()
                                page.wait_for_timeout(2000)
                    except Exception as e:
                        print(f"  Warning: Could not set time range: {e}")
                    
                    # Capture screenshot
                    output_path = output_dir / dashboard['output']
                    page.screenshot(path=str(output_path), full_page=False)
                    
                    print(f"  ✓ Screenshot saved: {output_path}")
                    screenshots_captured.append({
                        "name": dashboard['name'],
                        "path": str(output_path),
                        "filename": dashboard['output']
                    })
                    
                    # Close the page to ensure fresh state for next dashboard
                    page.close()
                    
                except Exception as e:
                    print(f"  ✗ Failed to capture {dashboard['name']}: {e}")
                    try:
                        page.close()
                    except Exception:
                        pass
                    
        except Exception as e:
            print(f"Error accessing Grafana: {e}")
            raise
        finally:
            browser.close()
    
    print(f"\n{'='*60}")
    print(f"Screenshot capture complete!")
    print(f"{'='*60}")
    print(f"Captured {len(screenshots_captured)} screenshots:")
    for screenshot in screenshots_captured:
        print(f"  - {screenshot['name']}: docs/assets/{screenshot['filename']}")
    print(f"\nOutput directory: {output_dir}")
    
    return screenshots_captured


if __name__ == "__main__":
    capture_grafana_screenshots()