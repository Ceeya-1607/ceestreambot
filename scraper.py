import requests
from bs4 import BeautifulSoup

# Browser headers to prevent immediate bot-blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

API_KEY = "d154a6bffe6626a2744dfeb9f24f3f2338dfdbfe"

# In-memory mapping of link IDs to URLs
url_list = {}


def shorten_url(original_url: str) -> str:
    """Safely shortens a URL with timeout and fallback to original URL on error."""
    try:
        api_endpoint = f"https://urlshortx.com/api?api={API_KEY}&url={original_url}"
        res = requests.get(api_endpoint, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success" and "shortenedUrl" in data:
                return data["shortenedUrl"]
    except Exception as e:
        print(f"[Shortener Error]: {e}")
    return original_url


def search_movies(query: str):
    movies_list = []
    # If this domain remains blocked or looping, replace with an active working mirror
    target_url = f"https://new2.hdhub4u.free/?s={query.replace(' ', '+')}"

    try:
        response = requests.get(
            target_url,
            headers=HEADERS,
            timeout=8,
            allow_redirects=True
        )
        if response.status_code != 200:
            print(f"[Search Error] HTTP {response.status_code} returned.")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Primary selector for movie cards
        cards = soup.find_all("a", class_="ml-mask jt")
        
        # Fallback selector if the site layout changes
        if not cards:
            cards = soup.select("article a, .thumb a, .entry-title a")

        for idx, item in enumerate(cards):
            href = item.get("href")
            if not href or href.startswith("#"):
                continue

            info_span = item.find("span", class_="mli-info")
            title = info_span.get_text(strip=True) if info_span else item.get_text(strip=True) or item.get("title", "")

            if not title:
                continue

            link_id = f"link{idx}"
            url_list[link_id] = href

            movies_list.append({
                "id": link_id,
                "title": title,
                "url": href
            })

            if len(movies_list) >= 8:
                break

        return movies_list

    except requests.exceptions.TooManyRedirects:
        print(f"[Redirect Loop]: {target_url} redirected too many times.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Network Error]: {e}")
        return []


def get_movie(query: str):
    """
    Accepts either an ID ('link0') or a direct URL.
    """
    movie_details = {
        "title": "Unknown Title",
        "img": None,
        "links": {}
    }

    page_url = url_list.get(query, query)
    if not isinstance(page_url, str) or not page_url.startswith("http"):
        return movie_details

    try:
        response = requests.get(
            page_url,
            headers=HEADERS,
            timeout=8
        )
        if response.status_code != 200:
            return movie_details

        soup = BeautifulSoup(response.text, "html.parser")

        # Title extraction
        title_tag = soup.find("div", class_="mvic-desc")
        if title_tag and title_tag.find("h3"):
            movie_details["title"] = title_tag.find("h3").get_text(strip=True)
        elif soup.find("h1"):
            movie_details["title"] = soup.find("h1").get_text(strip=True)

        # Poster / Thumbnail extraction
        thumb_div = soup.find("div", class_="mvic-thumb")
        if thumb_div:
            movie_details["img"] = thumb_div.get("data-bg") or (thumb_div.find("img").get("src") if thumb_div.find("img") else None)
        elif soup.find("meta", property="og:image"):
            movie_details["img"] = soup.find("meta", property="og:image").get("content")

        # Download / Stream links
        links = soup.find_all("a", attrs={"rel": "noopener", "data-wpel-link": "internal"})
        if not links:
            links = [a for a in soup.find_all("a", href=True) if "download" in a.get("href", "").lower()]

        final_links = {}
        for a_tag in links[:5]:
            btn_text = a_tag.get_text(strip=True) or "Download Link"
            raw_href = a_tag.get("href")
            if raw_href:
                shortened = shorten_url(raw_href)
                final_links[btn_text] = shortened

        movie_details["links"] = final_links
        return movie_details

    except requests.exceptions.RequestException as e:
        print(f"[Movie Fetch Error]: {e}")
        return movie_details
