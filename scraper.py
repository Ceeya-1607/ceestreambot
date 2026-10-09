import requests
from bs4 import BeautifulSoup

# Restored hardcoded API key
API_KEY = "d154a6bffe6626a2744dfeb9f24f3f2338dfdbfe"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_movies(query: str) -> list[dict]:
    """Search for movies and return a list of dictionaries containing title and details page URL."""
    formatted_query = query.strip().replace(" ", "+")
    search_url = f"https://videodownloader.site/?s={formatted_query}"
    
    try:
        response = requests.get(search_url, headers=BASE_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching search results: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    movie_cards = soup.find_all("a", class_="ml-mask jt")
    
    movies_list = []
    for idx, card in enumerate(movie_cards):
        title_elem = card.find("span", class_="mli-info")
        href = card.get("href")
        
        if href:
            # Create a fresh dict per iteration to avoid pass-by-reference bugs
            movies_list.append({
                "id": f"link{idx}",
                "title": title_elem.get_text(strip=True) if title_elem else "Unknown Title",
                "url": href
            })
            
    return movies_list


def get_movie_details(movie_url: str) -> dict:
    """Scrape details and process shortened URLs for a given movie URL."""
    try:
        response = requests.get(movie_url, headers=BASE_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching movie page: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    movie_details = {}

    # Extract title
    desc_div = soup.find("div", class_="mvic-desc")
    if desc_div and desc_div.find("h3"):
        movie_details["title"] = desc_div.find("h3").get_text(strip=True)

    # Extract thumbnail image
    thumb_div = soup.find("div", class_="mvic-thumb")
    if thumb_div:
        movie_details["img"] = thumb_div.get("data-bg") or thumb_div.get("src")

    # Extract download/stream links
    links = soup.find_all("a", rel="noopener", attrs={"data-wpel-link": "internal"})
    final_links = {}

    for link in links:
        target_href = link.get("href")
        link_text = link.get_text(strip=True) or "Download Link"
        
        if not target_href:
            continue

        api_url = f"https://urlshortx.com/api?api={API_KEY}&url={target_href}"
        try:
            res = requests.get(api_url, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("status") == "success" and "shortenedUrl" in data:
                final_links[link_text] = data["shortenedUrl"]
            else:
                final_links[link_text] = target_href
        except (requests.RequestException, ValueError):
            final_links[link_text] = target_href

    movie_details["links"] = final_links
    return movie_details
