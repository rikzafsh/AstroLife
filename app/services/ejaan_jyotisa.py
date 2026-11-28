"""Ejaan nama unsur jyotisa menurut persis-times-js (js/services/panchanga_service.js, objek PN; aksara Latin-Jawa Kuna dari daftar pemilik proyek).
Urutan = urutan baku. Huruf awal kapital seperti pada daftar sumber (JS sendiri menyeragamkannya menjadi huruf kecil saat dipakai)."""

TITHI = ["Pꭉaŧama", "Dwitīyā", "Tꭉétỿa", "Catur̀ŧī", "Pañcamī", "Ṣaṣṭī", "Saptamī", "Äṣṭamī", "Nawamī", "Dašamī", "Ë́kādašī", "Dwādašī", "Tꭉayodašī", "Catur̀dašī", "Pañcadašī"]
NAKSATRA = ["äšwini", "ƀaraṇī", "kr̥t͟tikā", "rohiṇī", "mr̥gašīr̀ṣa", "ǟr̀dꭉā", "punar̀wasu", "puṣỿa", "ǟšléṣā", "maǥā", "pūr̀w͟wa⹝ꝑalguṇī", "üttara⹝ꝑalguṇī", "hasta", "citꭉā", "swāti", "wišāꝁā", "änurāđā", "jỿéṣŧ̣ā", "mūla", "pūr̀w͟wa⹝ǟṣāđ̣ā", "üttara⹝ǟṣāđ̣ā", "šꭉāwaṇa", "đaniṣŧ̣ā", "šataƀiṣā", "pūr̀w͟wa⹝ƀādꭉapada", "üttara⹝ƀādꭉapada", "réwatī"]
YOGA = ["Wiṣkamƀa", "Pꭉīti", "Ǟyuṣmāna", "Sꜷƀāgỿa", "Šoƀana", "Ätigaṇḍa", "Sukar̀m͟mā", "Đr̥ti", "Šūla", "Gaṇḍa", "Wr̥dđi", "Đꭉuwa", "Wỿāǥāta", "Har̀ṣaṇa", "Wajꭉa", "Sidđi", "Wỿatipāta", "Warīyas⸝", "Pariǥa", "Šiwa", "Sidđa", "Sāđỿa", "Šuƀa", "Šukla", "Bꭉahma", "Mahe̋ndꭉa", "Wꜽđr̥ti"]
KARANA_BERGERAK = ["Wawa", "Walawa", "Kolawa", "Tꜽŧila", "Garadi", "Waṇija", "Wiṣṭi"]
MASA = ["Cꜽtꭉa", "Wꜽšāꝁa", "Jỿéṣṭa", "Äsađa", "šꭉawaṇa", "ƀadꭉawāda", "Äsuji", "Kar̀t͟tika", "Mār̀g͟gašira", "Puṣā", "Māǥa", "ꝑalguṇa"]
RASI = ["meša", "wr̥ṣaƀa", "miŧuna", "kar̀k͟ka", "siṅha", "kanỿā", "tūla", "mr̥c⃬ꞓika", "đanuḥ", "makara", "kumƀa", "mīna"]
PAKSA = ["Šukla", "Kr̥ṣṇa"]
KARANA_TETAP = {1: "Kimtuǥna", 58: "Sakuni", 59: "Catuspada", 60: "Naga"}


def nama_karana(k: int) -> str:
    """Karana ke-k (1-60): 1 dan 58-60 tetap, 2-57 siklus tujuh karana bergerak."""
    return KARANA_TETAP.get(k) or KARANA_BERGERAK[(k - 2) % 7]
