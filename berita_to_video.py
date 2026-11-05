import os
import re
import shutil
import requests
from bs4 import BeautifulSoup
from icrawler.builtin import BingImageCrawler
from gtts import gTTS
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, TextClip
)
from PIL import Image

# ---------- KONFIGURASI ----------
KEYWORDS_FILE   = "keywords.txt"
OUTPUT_DIR      = "output"
RAW_DIR         = os.path.join(OUTPUT_DIR, "raw")
IMAGES_PER_KW   = 3          # jumlah gambar per keyword (biar ada variasi)
MAX_TEXT_CHARS  = 450        # batas teks untuk TTS (~30-45 detik)
VIDEO_SIZE      = (1280, 720)
FPS             = 24
LANG            = "id"
# --------------------------------

os.makedirs(RAW_DIR, exist_ok=True)


# ========== 1. BACA KEYWORDS ==========
def load_keywords(path=KEYWORDS_FILE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} tidak ditemukan. Buat file dengan 1 keyword per baris.")
    with open(path, "r", encoding="utf-8") as f:
        kws = [line.strip() for line in f if line.strip()]
    if not kws:
        raise ValueError("keywords.txt kosong.")
    return kws


# ========== 2. SCRAPE TEKS BERITA ==========
def scrape_news_text(keyword):
    """Ambil ringkasan teks dari hasil pencarian berita (Bing News)."""
    try:
        url = "https://www.bing.com/news/search"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params={"q": keyword}, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        snippets = []
        for tag in soup.select("div.news-card, a.title, div.snippet"):
            txt = tag.get_text(" ", strip=True)
            if txt and len(txt) > 40:
                snippets.append(txt)
            if len(snippets) >= 3:
                break
        text = " ".join(snippets).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            text = f"Berita terbaru mengenai {keyword}. Informasi lebih lanjut sedang dikembangkan."
        return text[:MAX_TEXT_CHARS]
    except Exception as e:
        print(f"   ⚠️ Gagal scrape, pakai fallback: {e}")
        return f"Berita terbaru mengenai {keyword}."


# ========== 3. DOWNLOAD GAMBAR ==========
def download_images(keyword, idx):
    folder = os.path.join(RAW_DIR, f"img_{idx}")
    os.makedirs(folder, exist_ok=True)
    crawler = BingImageCrawler(
        storage={"root_dir": folder},
        downloader_threads=2,
        feeder_threads=1,
        parser_threads=1,
        log_level=40,  # warning only
    )
    crawler.crawl(keyword=keyword, max_num=IMAGES_PER_KW)
    imgs = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder)
         if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    )
    return imgs


# ========== 4. TEKS -> SUARA ==========
def text_to_speech(text, out_path):
    tts = gTTS(text=text, lang=LANG, slow=False)
    tts.save(out_path)
    return out_path


# ========== 5. RESIZE / FIT GAMBAR ==========
def fit_image(img_path, size=VIDEO_SIZE):
    """Resize + crop tengah supaya pas rasio video."""
    from PIL import ImageOps
    img = Image.open(img_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, size, method=Image.LANCZOS)
    tmp = img_path + "_fit.jpg"
    img.save(tmp, "JPEG", quality=90)
    return tmp


# ========== 6. BUAT CLIP PER KEYWORD ==========
def build_clip_for_keyword(keyword, idx):
    print(f"\n🎬 Memproses keyword [{idx}]: {keyword}")

    # 1) teks
    print("   📝 Scrape teks berita...")
    text = scrape_news_text(keyword)
    print(f"      → {text[:90]}...")

    # 2) gambar
    print("   🖼️  Download gambar...")
    imgs = download_images(keyword, idx)
    if not imgs:
        print("      ⚠️ Tidak ada gambar, pakai gambar placeholder.")
        placeholder = os.path.join(RAW_DIR, f"placeholder_{idx}.jpg")
        Image.new("RGB", VIDEO_SIZE, (30, 30, 30)).save(placeholder)
        imgs = [placeholder]
    print(f"      → {len(imgs)} gambar")

    # 3) suara
    print("   🔊 Generate TTS...")
    audio_path = os.path.join(RAW_DIR, f"audio_{idx}.mp3")
    text_to_speech(text, audio_path)
    audio = AudioFileClip(audio_path)

    # 4) bagi durasi audio ke jumlah gambar
    per_img = audio.duration / len(imgs)
    clips = []
    for p in imgs:
        fit = fit_image(p)
        clip = ImageClip(fit).with_duration(per_img)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video = video.with_audio(audio)
    print(f"   ✅ Clip selesai: {video.duration:.1f}s, {len(imgs)} gambar")
    return video


# ========== 7. MAIN ==========
def main():
    keywords = load_keywords()
    print(f"📋 {len(keywords)} keyword ditemukan.\n")

    clips = []
    for i, kw in enumerate(keywords, start=1):
        try:
            clips.append(build_clip_for_keyword(kw, i))
        except Exception as e:
            print(f"   ❌ Gagal memproses '{kw}': {e}")
            continue

    if not clips:
        print("Tidak ada clip yang berhasil. Berhenti.")
        return

    print("\n🔗 Menggabungkan semua clip...")
    final = concatenate_videoclips(clips, method="compose")

    out_path = os.path.join(OUTPUT_DIR, "berita_final.mp4")
    print(f"💾 Menulis video ke {out_path} ...")
    final.write_videofile(
        out_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",   # lebih cepat di CPU
        threads=2,
    )
    print(f"\n✅ Selesai: {out_path}")


if __name__ == "__main__":
    main()
