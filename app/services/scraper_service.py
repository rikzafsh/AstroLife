import json
import time
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from config import Config

CACHE_DIR = Config.CACHE_DIR

def get_cache_file(year: int, month: int) -> Path:
    return CACHE_DIR / f"events_{year}_{month:02d}.json"

def scrape_in_the_sky_events(year: int = None, month: int = None, force_refresh: bool = False):
    """
    Scrapes astronomical phenomena for a given month and year from in-the-sky.org.
    Includes file-based caching to prevent redundant requests and rate-limiting.
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    cache_file = get_cache_file(year, month)
    
    # 1. Check Cache
    if not force_refresh and cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                cached_time = cached_data.get('timestamp', 0)
                # If cache is still valid
                if (time.time() - cached_time) < Config.CACHE_EXPIRY_SECONDS:
                    return cached_data.get('events', [])
        except Exception as e:
            print(f"[Warning] Failed reading cache: {e}")

    # 2. Fetch from in-the-sky.org
    url = f"https://in-the-sky.org/newscal.php?year={year}&month={month}&maxrows=100"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    events = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # in-the-sky event listing items: usually elements with class 'feeditem' or in calendar tables
            feed_items = soup.find_all('div', class_='feeditem')
            
            if not feed_items:
                # Fallback to general table/list if page structure differs
                table_rows = soup.select('table.table_calendar tr, table.newscal tr')
                for row in table_rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        date_str = cols[0].get_text(strip=True)
                        desc_str = cols[1].get_text(strip=True)
                        if desc_str:
                            events.append({
                                'date': f"{year}-{month:02d} ({date_str})",
                                'title': desc_str,
                                'type': 'Astronomical Event',
                                'description': desc_str,
                                'source': 'in-the-sky.org'
                            })

            for item in feed_items:
                # Extract date, title, link, type
                date_tag = item.find('div', class_='feeditem_date') or item.find('time')
                title_tag = item.find('a', class_='feeditem_title') or item.find('h3') or item.find('a')
                desc_tag = item.find('div', class_='feeditem_desc') or item.find('p')
                
                date_val = date_tag.get_text(strip=True) if date_tag else f"{year}-{month:02d}"
                title_val = title_tag.get_text(strip=True) if title_tag else "Fenomena Astronomi"
                desc_val = desc_tag.get_text(strip=True) if desc_tag else title_val
                link_val = "https://in-the-sky.org/" + title_tag['href'].lstrip('/') if title_tag and title_tag.has_attr('href') else url

                # Determine basic category
                event_type = 'General'
                title_lower = title_val.lower()
                if 'moon' in title_lower or 'bulan' in title_lower:
                    event_type = 'Fase Bulan'
                elif 'meteor' in title_lower:
                    event_type = 'Hujan Meteor'
                elif 'eclipse' in title_lower or 'gerhana' in title_lower:
                    event_type = 'Gerhana'
                elif 'conjunction' in title_lower or 'konjungsi' in title_lower:
                    event_type = 'Konjungsi Planet'
                elif 'planet' in title_lower:
                    event_type = 'Planet'

                events.append({
                    'date': date_val,
                    'title': title_val,
                    'type': event_type,
                    'description': desc_val,
                    'link': link_val,
                    'source': 'in-the-sky.org'
                })

            # If scraped successfully, save to cache
            if events:
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({'timestamp': time.time(), 'events': events}, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[Warning] Failed writing cache: {e}")

    except Exception as e:
        print(f"[Error] Failed scraping in-the-sky.org: {e}")

    # 3. Fallback: If network down, blocked by anti-bot, or empty, read curated dataset or existing cache
    if not events:
        dataset_file = Config.DATASETS_DIR / "astronomy_events.json"
        if dataset_file.exists():
            try:
                with open(dataset_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

    return events
