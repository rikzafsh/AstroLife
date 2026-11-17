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
    peak_time_str = link_green.get_text(' ', strip=True) if link_green else ""   # ' ' menjaga pemisah antar node
    
    # 3. Ikon & Tingkat Kesulitan Resmi (level1_icon.png, dst.)
    # Tidak ada nilai bawaan: bila ikon level tidak ditemukan, field dibiarkan kosong (None)
    diff_level = None
    diff_label = ""
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
        # Prioritas: paragraf yang menyebut Jakarta; cadangan: paragraf visibilitas umum.
        paras = [p.get_text(' ', strip=True) for p in newsbody.find_all('p')]
        generic = re.compile(r'(from|in|over) (jakarta|indonesia)|visible (from|in)', re.I)
        ordered = [t for t in paras if re.search(r'jakarta', t, re.I)] + [t for t in paras if generic.search(t)]
        for text in ordered[:1]:
            if True:
                visibility_p = text
                
                # Zona waktu HANYA diambil dari teks halaman (mis. "(WIB)" atau jam puncak); tidak diasumsikan.
                tz_peak = re.search(r'\b(WIB|WITA|WIT|UTC|GMT)\b', peak_time_str or '')
                tz_default = tz_peak.group(1) if tz_peak else ''

                # Jam Terbit: "rising at 00:55 (WIB)"
                r_match = re.search(r'rising at\s*(\d{1,2}:\d{2})(?:\s*\(([A-Z]{2,4})\))?', text, re.I)
                tz_text = (r_match.group(2) if r_match and r_match.group(2) else tz_default)
                if r_match:
                    rising_time = r_match.group(1) + (f" ({tz_text})" if tz_text else "")

                # Ketinggian & Arah: "reaching an altitude of 58° above the north-eastern horizon"
                alt_match = re.search(r'altitude of\s*([0-9.]+\s*(?:&deg;|°|degrees))\s*above the\s*([a-zA-Z\s-]+?horizon)', text, re.I)
                if alt_match:
                    altitude = re.sub(r'\s*(&deg;|degrees)', '°', alt_match.group(1))
                    azimuth_dir = alt_match.group(2).strip()

                # Jam Fajar: "dawn breaks at around 05:12" (zona waktu mengikuti paragraf yang sama)
                d_match = re.search(r'dawn breaks at around\s*(\d{1,2}:\d{2})', text, re.I)
                if d_match:
                    fade_time = d_match.group(1) + (f" ({tz_text})" if tz_text else "")
                break
                
    # 5. Rasi Bintang
    constellation = ""
    const_link = soup.find('a', href=re.compile(r'constellation\.php\?id='))
    if const_link:
        constellation = const_link.get_text(strip=True)   # data mentah; awalan 'Rasi' ditambahkan di lapisan tampilan

    # 6. Objek Langit Terlibat
    objects = []
    for tag in soup.find_all('span', class_='event_tag'):
        obj_link = tag.find('a', href=re.compile(r'object\.php\?id='))
        if obj_link:
            objects.append(obj_link.get_text(strip=True))

    # 7. Deskripsi Ilmiah Utama: paragraf bermakna pertama (bukan keterangan gambar/baris kosong)
    summary_desc = ""
    all_text = ""
    if newsbody:
        paras = [p.get_text(' ', strip=True) for p in newsbody.find_all('p')]
        summary_desc = next((t for t in paras if len(t) > 40), "")
        all_text = ' '.join(paras)

    # 8. Okultasi: jam hilang (ingress) & muncul kembali (egress) sebagaimana tertulis di halaman
    tzp = r'(?:\s*(WIB|WITA|WIT|UTC|GMT))?'
    ing = re.search(r'disappearance[^.]{0,120}?\bat\s*(\d{1,2}:\d{2})' + tzp, all_text, re.I)
    egr = re.search(r'reappearance[^.]{0,120}?\bat\s*(\d{1,2}:\d{2})' + tzp, all_text, re.I)
    occ_alt = re.search(r'disappearance[^.]{0,160}?altitude of\s*([0-9.]+)', all_text, re.I)
    fmt = lambda m: (m.group(1) + (f" ({m.group(2).upper()})" if m.group(2) else "")) if m else ""

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
        'occultation_ingress': fmt(ing),
        'occultation_egress': fmt(egr),
        'occultation_altitude': occ_alt.group(1) if occ_alt else "",
        'description': summary_desc,
        'url': url
    }
