import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

API_KEY = "d154a6bffe6626a2744dfeb9f24f3f2338dfdbfe"
# Guaranteed fallback image if the movie page has no thumbnail
FALLBACK_IMG = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&auto=format&fit=crop&q=60"

url_list = {}


def shorten_url(original_url: str) -> str:
    try:
        api_endpoint = f"https://urlshortx.com/api?api={API_KEY}&url={original_url}"
        res = requests.get(api_endpoint, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success" and "shortenedUrl" in data:
                return data["shortenedUrl"]
    except Exception:
        pass
    return original_url


def search_movies(query: str):
    global url_list
    movies_list = []
    
    # If hdhub4u redirects to the homepage, you will get the homepage latest releases
    target_url = f"https://fzmovies.live/?s={query.replace(' ', '+')}"

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=8, allow_redirects=True)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        cards = soup.find_all("a", class_="ml-mask jt")
        if not cards:
            cards = soup.select("article a, .thumb a, .entry-title a, .post-title a")

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

    except Exception as e:
        print(f"[Search Exception]: {e}")
        return []


def get_movie(query: str):
    movie_details = {
        "title": "Movie Details",
        "img": FALLBACK_IMG,  # Always set to a valid URL by default
        "links": {}
    }

    page_url = url_list.get(query, query)
    if not isinstance(page_url, str) or not page_url.startswith("http"):
        return movie_details

    try:
        response = requests.get(page_url, headers=HEADERS, timeout=8)
        if response.status_code != 200:
            return movie_details

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Extract Title
        title_tag = soup.find("div", class_="mvic-desc")
        if title_tag and title_tag.find("h3"):
            movie_details["title"] = title_tag.find("h3").get_text(strip=True)
        elif soup.find("h1"):
            movie_details["title"] = soup.find("h1").get_text(strip=True)

        # 2. Extract Image safely (checks meta, post thumbnails, and inline images)
        img_url = None
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img_url = og_img.get("content")

        if not img_url:
            thumb_div = soup.find("div", class_="mvic-thumb")
            if thumb_div:
                img_url = thumb_div.get("data-bg") or (thumb_div.find("img").get("src") if thumb_div.find("img") else None)

        if not img_url:
            first_img = soup.find("article")
            if first_img and first_img.find("img"):
                img_url = first_img.find("img").get("src")

        if img_url and img_url.startswith("http"):
            movie_details["img"] = img_url

        # 3. Extract Links
        links = soup.find_all("a", attrs={"rel": "noopener", "data-wpel-link": "internal"})
        if not links:
            links = [a for a in soup.find_all("a", href=True) if "download" in a.get("href", "").lower()]

        final_links = {}
        for a_tag in links[:5]:
            btn_text = a_tag.get_text(strip=True) or "Download Link"
            raw_href = a_tag.get("href")
            if raw_href and raw_href.startswith("http"):
                shortened = shorten_url(raw_href)
                final_links[btn_text] = shortened

        # Fallback if no internal download links were found
        if not final_links:
            final_links["View on Website"] = shorten_url(page_url)

        movie_details["links"] = final_links
        return movie_details

    except Exception as e:
        print(f"[Get Movie Error]: {e}")
        return movie_details
