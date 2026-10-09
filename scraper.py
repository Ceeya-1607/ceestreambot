import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

API_KEY = "d154a6bffe6626a2744dfeb9f24f3f2338dfdbfe"
FALLBACK_IMG = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&auto=format&fit=crop&q=60"

DOMAINS = ["mobiletvshows.site"]
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


def resolve_universal_download_link(raw_url: str) -> str:
    """Universal resolver: handles file hosts (Downloadwella, Sabishares, Wideshares), videodownloader.site, and direct streams."""
    try:
        # 1. Handle Downloadwella / Xfileshare / Sabishares architecture natively
        if "downloadwella.com" in raw_url or "wideshares.org" in raw_url:
            page_res = requests.get(raw_url, headers=HEADERS, timeout=6)
            if page_res.status_code == 200:
                soup = BeautifulSoup(page_res.text, "html.parser")
                form = soup.find("form", {"name": "F1"}) or soup.find("form")
                
                file_id = ""
                rand_val = ""
                if form:
                    id_input = form.find("input", {"name": "id"})
                    rand_input = form.find("input", {"name": "rand"})
                    if id_input: file_id = id_input.get("value", "")
                    if rand_input: rand_val = rand_input.get("value", "")

                if not file_id:
                    parts = raw_url.split("/")
                    if len(parts) > 3: file_id = parts[3]

                post_data = {
                    "op": "download2",
                    "id": file_id,
                    "rand": rand_val,
                    "referer": raw_url,
                    "method_free": "Free Download"
                }

                post_res = requests.post(raw_url, data=post_data, headers={
                    **HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": raw_url
                }, timeout=8)

                if post_res.status_code == 200:
                    post_soup = BeautifulSoup(post_res.text, "html.parser")
                    direct_a = post_soup.select_one('a[href*=".mkv"], a[href*=".mp4"]')
                    if direct_a and direct_a.get("href"):
                        return direct_a.get("href")
                    match = re.search(r'href=["\'](https://[^"\']+\.(?:mkv|mp4)[^"\']*)["\']', post_res.text, re.IGNORECASE)
                    if match:
                        return match.group(1)

        elif "sabishares.com" in raw_url:
            clean_url = raw_url.split("?preview")[0]
            head_res = requests.head(clean_url, headers=HEADERS, allow_redirects=False, timeout=5)
            loc = head_res.headers.get("location")
            if loc and loc.startswith("http"):
                return loc
            return clean_url

        # 2. Integrate videodownloader.site API/extraction
        try:
            vd_endpoint = f"https://https://mobiletvshows.site/api/extract?url={requests.utils.quote(raw_url)}"
            vd_res = requests.get(vd_endpoint, headers=HEADERS, timeout=4)
            if vd_res.status_code == 200:
                vd_data = vd_res.json()
                if vd_data.get("success") and vd_data.get("download_url"):
                    return vd_data["download_url"]
        except Exception:
            pass

        # 3. Generic HTML5 Fallback
        page_res = requests.get(raw_url, headers=HEADERS, timeout=6)
        if page_res.status_code == 200:
            soup = BeautifulSoup(page_res.text, "html.parser")
            video_tag = soup.find("video")
            if video_tag and video_tag.get("src"):
                return video_tag.get("src")
            source_tag = soup.find("source")
            if source_tag and source_tag.get("src"):
                return source_tag.get("src")
            
            match = re.search(r'https?://[^\s"\'<>]+?\.(?:mkv|mp4|avi|mov|webm)', page_res.text, re.IGNORECASE)
            if match:
                return match.group(0)

    except Exception as e:
        print(f"[Universal Resolver Error]: {e}")

    return raw_url


def search_movies(query: str):
    global url_list
    movies_list = []
    
    for domain in DOMAINS:
        target_url = f"https://{domain}/?s={query.replace(' ', '+')}"
        try:
            response = requests.get(target_url, headers=HEADERS, timeout=6, allow_redirects=True)
            if response.status_code != 200:
                continue

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

                link_id = f"{domain}_link{idx}"
                url_list[link_id] = href

                movies_list.append({
                    "id": link_id,
                    "title": title,
                    "url": href
                })

                if len(movies_list) >= 8:
                    break

            if movies_list:
                break # Stop trying other domains if results found

        except Exception as e:
            print(f"[Search Exception on {domain}]: {e}")
            continue

    return movies_list


def get_movie(query: str):
    movie_details = {
        "title": "Movie Details",
        "img": FALLBACK_IMG,
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

        # 2. Extract Image safely
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

        # 3. Extract Links and resolve universally
        links = soup.find_all("a", attrs={"rel": "noopener", "data-wpel-link": "internal"})
        if not links:
            links = [a for a in soup.find_all("a", href=True) if "download" in a.get("href", "").lower()]

        final_links = {}
        for a_tag in links[:5]:
            btn_text = a_tag.get_text(strip=True) or "Download Link"
            raw_href = a_tag.get("href")
            if raw_href and raw_href.startswith("http"):
                direct_url = resolve_universal_download_link(raw_href)
                shortened = shorten_url(direct_url)
                final_links[btn_text] = shortened

        if not final_links:
            final_links["View on Website"] = shorten_url(page_url)

        movie_details["links"] = final_links
        return movie_details

    except Exception as e:
        print(f"[Get Movie Error]: {e}")
        return movie_details
