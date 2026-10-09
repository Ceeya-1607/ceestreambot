import asyncio
import re
from playwright.async_api import async_playwright, Route, Request

# Common ad/tracker domain patterns to block immediately
BLOCKED_PATTERNS = [
    r"google-analytics\.com",
    r"googletagmanager\.com",
    r"doubleclick\.net",
    r"adnxs\.com",
    r"popads\.net",
    r"onclickads\.net",
    r"propellerads\.com",
    r"exoclick\.com",
    r"ad-delivery",
    r"shortener",
]

BLOCKED_REGEX = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)

# Resource types you can drop to speed up execution and stop ad scripts
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


async def route_interceptor(route: Route, request: Request):
    """
    Evaluates every outgoing HTTP/HTTPS request before it leaves the browser.
    Aborts matching ad domains, trackers, and unnecessary heavy media.
    """
    url = request.url
    resource_type = request.resource_type

    # 1. Drop blocked asset types (images, videos, fonts)
    if resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
        return

    # 2. Block known ad domains and popup networks
    if BLOCKED_REGEX.search(url):
        # print(f"[BLOCKED AD]: {url}")
        await route.abort()
        return

    # 3. Allow legitimate content to proceed
    await route.continue_()


async def fetch_sandboxed_page(target_url: str):
    async with async_playwright() as p:
        # Launch Chromium.
        # Note: If running inside Docker as root, Chromium requires
        # args=["--no-sandbox", "--disable-setuid-sandbox"]
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--disable-extensions",
            ]
        )

        # Create an isolated incognito browser context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )

        page = await context.new_page()

        # Disallow popup windows and new tabs opened by malicious scripts
        page.on("popup", lambda popup: asyncio.create_task(popup.close()))

        # Register the network interceptor for all traffic
        await page.route("**/*", route_interceptor)

        try:
            print(f"Navigating to: {target_url}")
            # Wait until DOM is loaded or network is idle (max 15s timeout)
            await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)

            # Optional: Wait for a specific selector or short delay if page hydrates dynamically
            # await page.wait_for_selector("div.content", timeout=5000)

            content = await page.content()
            title = await page.title()
            print(f"Loaded page title: {title}")

            return content

        except Exception as e:
            print(f"Error navigating to {target_url}: {e}")
            return None

        finally:
            # Clean up the sandbox context and browser instance
            await context.close()
            await browser.close()


if __name__ == "__main__":
    test_url = "https://example.com"
    html = asyncio.run(fetch_sandboxed_page(test_url))
    if html:
        print(f"Successfully retrieved {len(html)} bytes of HTML.")
