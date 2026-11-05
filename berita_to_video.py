import os, re, requests
from bs4 import BeautifulSoup
from icrawler.builtin import BingImageCrawler
from gtts import gTTS
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageOps
from deep_translator import GoogleTranslator

KEYWORDS_FILE  = "keywords.txt"
OUTPUT_DIR     = "output"
RAW_DIR        = os.path.join(OUTPUT_DIR, "raw")
IMAGES_PER_KW  = 3
MAX_TEXT_CHARS = 450
VIDEO_SIZE     = (1280, 720)
FPS            = 24
LANG_TTS       = "id"        # suara Indonesia
LANG_SEARCH    = "en"        # pencarian gambar & berita pakai Inggris
os.makedirs(RAW_DIR, exist_ok=True)


# ========== TERJEMAHKAN KEYWORD ==========
def translate_keyword(kw_id):
    """Terjemahkan keyword Indonesia -> Inggris untuk pencarian."""
    try:
        kw_en = GoogleTranslator(source="id", target="en").translate(kw_id)
        return kw_en
    except Exception as e:
        print(f"   ⚠️ Gagal terjemah: {e}, pakai keyword asli")
        return kw_id


# ========== SCRAPE TEKS BERITA (INDONESIA) ==========
def scrape_news_text(keyword_id, keyword_en):
    """
    Cari berita dari situs Indonesia, ambil ringkasan dalam bahasa Indonesia.
    Fallback: pakai keyword ID kalau gagal.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # 1) Coba situs berita Indonesia via Bing News (region ID)
        url = "https://www.bing.com/news/search"
        params = {"q": keyword_id, "mkt": "id-ID", "setlang": "id"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")

        snippets = []
        for tag in soup.select("div.news-card, a.title, div.snippet"):
            txt = tag.get_text(" ", strip=True)
            if txt and len(txt) > 40:
                snippets.append(txt)
            if len(snippets) >= 3:
                break

        text_id = re.sub(r"\s+", " ", " ".join(snippets)).strip()

        # 2) Kalau kosong, coba berita Inggris lalu terjemahkan ke Indonesia
        if not text_id:
            params_en = {"q": keyword_en, "mkt": "en-US", "setlang": "en"}
            r2 = requests.get(url, params=params_en, headers=headers, timeout=15)
            soup2 = BeautifulSoup(r2.text, "lxml")
            snippets_en = []
            for tag in soup2.select("div.news-card, a.title, div.snippet"):
                txt = tag.get_text(" ", strip=True)
                if txt and len(txt) > 40:
                    snippets_en.append(txt)
                if len(snippets_en) >= 3:
                    break
            text_en = " ".join(snippets_en).strip()
            if text_en:
                text_id = GoogleTranslator(source="en", target="id").translate(text_en)

        if not text_id:
            text_id = f"Berita terbaru mengenai {keyword_id}."

        return text_id[:MAX_TEXT_CHARS]

    except Exception as e:
        print(f"   ⚠️ Gagal scrape: {e}")
        return f"Berita terbaru mengenai {keyword_id}."


# ========== DOWNLOAD GAMBAR (PAKAI KEYWORD INGGRIS) ==========
def download_images(keyword_en, idx):
    folder = os.path.join(RAW_DIR, f"img_{idx}")
    os.makedirs(folder, exist_ok=True)
    crawler = BingImageCrawler(
        storage={"root_dir": folder},
        downloader_threads=2,
        log_level=40,
    )
    crawler.crawl(keyword=keyword_en, max_num=IMAGES_PER_KW)
    imgs = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ])
    return imgs


# ========== BUILD CLIP ==========
def build_clip_for_keyword(keyword_id, idx):
    print(f"\n🎬 [{idx}] {keyword_id}")

    # 1) Terjemahkan keyword untuk pencarian
    keyword_en = translate_keyword(keyword_id)
    print(f"   🔁 Keyword pencarian: {keyword_en}")

    # 2) Scrape teks Indonesia
    print("   📝 Scrape teks berita (ID)...")
    text = scrape_news_text(keyword_id, keyword_en)
    print(f"      → {text[:80]}...")

    # 3) Download gambar pakai keyword Inggris
    print("   🖼️  Download gambar (EN)...")
    imgs = download_images(keyword_en, idx)
    if not imgs:
        ph = os.path.join(RAW_DIR, f"placeholder_{idx}.jpg")
        Image.new("RGB", VIDEO_SIZE, (30, 30, 30)).save(ph)
        imgs = [ph]

    # 4) TTS Indonesia
    print("   🔊 TTS (ID)...")
    audio_path = os.path.join(RAW_DIR, f"audio_{idx}.mp3")
    gTTS(text=text, lang=LANG_TTS, slow=False).save(audio_path)
    audio = AudioFileClip(audio_path)

    # 5) Gabung gambar (durasi = audio / n)
    per_img = audio.duration / len(imgs)
    clips = []
    for p in imgs:
        img = ImageOps.fit(Image.open(p).convert("RGB"), VIDEO_SIZE, Image.LANCZOS)
        tmp = p + "_fit.jpg"
        img.save(tmp, "JPEG", quality=90)
        clips.append(ImageClip(tmp).with_duration(per_img))

    video = concatenate_videoclips(clips, method="compose").with_audio(audio)
    print(f"   ✅ {video.duration:.1f}s")
    return video
