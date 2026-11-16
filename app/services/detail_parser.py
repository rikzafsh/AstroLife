from bs4 import BeautifulSoup
import re
import json

def parse_in_the_sky_detail_html(html_content: str, url: str = "") -> dict:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Judul
    title_el = soup.find('p', class_='widetitle') or soup.find('title')
    title = title_el.get_text(strip=True).replace(' - In-The-Sky.org', '') if title_el else ""
    
    # 2. Tanggal & Jam Puncak Event
    link_green = soup.find('div', class_='link_green')
    peak_time_str = link_green.get_text(strip=True) if link_green else ""
    
    # 3. Ikon & Tingkat Kesulitan Resmi (level1_icon.png, dst.)
    diff_level = 1
    diff_label = "Mata Telanjang"
    diff_alt = ""
    level_img = soup.find('img', src=re.compile(r'level\d+_icon\.png'))
    if level_img:
        diff_alt = level_img.get('alt', '') or level_img.get('title', '')
        src = level_img.get('src', '')
        m = re.search(r'level(\d+)_icon', src)
        if m:
            diff_level = int(m.group(1))
            labels = {
                1: 'Mata Telanjang (Naked Eye)',
                2: 'Binokular',
                3: 'Teleskop Kecil',
                4: 'Teleskop 4-inch',
                5: 'Teleskop Besar',
                6: 'Semua Alat',
                7: 'Tidak Dapat Diamati'
            }
            diff_label = labels.get(diff_level, f"Level {diff_level}")

    # 4. Paragraf Visibilitas Spesifik Lokasi (misal: "From Jakarta...")
    newsbody = soup.find('div', class_='newsbody')
    visibility_p = ""
    rising_time = ""
    fade_time = ""
    altitude = ""
    azimuth_dir = ""
    
    if newsbody:
        for p in newsbody.find_all('p'):
            text = p.get_text(strip=True)
            if 'From Jakarta' in text or 'visible in the' in text:
                visibility_p = text
                
                # Ekstrak Jam Terbit: "rising at 00:55 (WIB)"
                r_match = re.search(r'rising at\s*([0-9:]+)(?:\s*\((WIB|UTC)\))?', text, re.I)
                if r_match:
                    rising_time = r_match.group(1) + (" WIB" if not "WIB" in r_match.group(0) else " (WIB)")
                
                # Ekstrak Ketinggian & Arah: "reaching an altitude of 58° above the north-eastern horizon"
                alt_match = re.search(r'altitude of\s*([0-9]+&deg;|[0-9]+°)\s*above the\s*([a-zA-Z\s-]+?horizon)', text, re.I)
                if alt_match:
                    altitude = alt_match.group(1).replace('&deg;', '°')
                    azimuth_dir = alt_match.group(2).strip()

                # Ekstrak Jam Hilang/Fajar: "dawn breaks at around 05:12"
                d_match = re.search(r'dawn breaks at around\s*([0-9:]+)', text, re.I)
                if d_match:
                    fade_time = d_match.group(1) + " WIB"
                break
                
    # 5. Rasi Bintang
    constellation = ""
    const_link = soup.find('a', href=re.compile(r'constellation\.php\?id='))
    if const_link:
        constellation = f"Rasi {const_link.get_text(strip=True)}"

    # 6. Objek Langit Terlibat
    objects = []
    for tag in soup.find_all('span', class_='event_tag'):
        obj_link = tag.find('a', href=re.compile(r'object\.php\?id='))
        if obj_link:
            objects.append(obj_link.get_text(strip=True))

    # 7. Deskripsi Ilmiah Utama
    summary_desc = ""
    if newsbody:
        first_p = newsbody.find('p')
        if first_p:
            summary_desc = first_p.get_text(strip=True)

    return {
        'title': title,
        'peak_event_time': peak_time_str,
        'difficulty_level': diff_level,
        'difficulty_label': diff_label,
        'difficulty_alt': diff_alt,
        'rising_time': rising_time,
        'fading_time': fade_time,
        'altitude': altitude,
        'azimuth_direction': azimuth_dir,
        'constellation': constellation,
        'objects': objects,
        'visibility_summary': visibility_p,
        'description': summary_desc,
        'url': url
    }
