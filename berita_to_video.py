import os
import re
from icrawler.builtin import BingImageCrawler
from gtts import gTTS
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips
)
from PIL import Image, ImageOps

# ---------- KONFIGURASI ----------
BERITA_FILE    = "berita.txt"
OUTPUT_DIR     = "output"
RAW_DIR        = os.path.join(OUTPUT_DIR, "raw")
IMAGES_PER_SEG = 2          # gambar per segmen (kalimat)
VIDEO_SIZE     = (1280, 720)
FPS            = 24
LANG_TTS       = "id"
MAX_CHARS_SEG  = 500        # aman untuk gTTS
# -----------------------------------

os.makedirs(RAW_DIR, exist_ok=True)


# ========== 1. BACA BERITA ==========
def load_segments(path=BERITA_FILE):
    """Baca: teks|query (1 baris 1 segmen)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} tidak ditemukan.")
    segs = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                print(f"⚠️ Baris {i} dilewati (tanpa '|'): {line[:40]}...")
                continue
            teks, query = [x.strip() for x in line.split("|", 1)]
            if not teks or not query:
                print(f"⚠️ Baris {i} kosong salah satu sisi, dilewati.")
                continue
            segs.append((teks, query))
    if not segs:
        raise ValueError("Tidak ada segmen valid di berita.txt")
    return segs


# ========== 2. DOWNLOAD GAMBAR ==========
def download_images(query, folder, max_num=IMAGES_PER_SEG):
    os.makedirs(folder, exist_ok=True)
    crawler = BingImageCrawler(
        storage={"root_dir": folder},
        downloader_threads=2,
        feeder_threads=1,
        parser_threads=1,
        log_level=40,  # hanya warning
    )
    try:
        crawler.crawl(keyword=query, max_num=max_num)
    except Exception as e:
        print(f"      ⚠️ Crawl gagal: {e}")
    imgs = sorted([
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ])
    return imgs


# ========== 3. FIT GAMBAR ==========
def fit_image(path):
    img = ImageOps.fit(
        Image.open(path).convert("RGB"),
        VIDEO_SIZE,
        method=Image.LANCZOS,
    )
    tmp = path + "_fit.jpg"
    img.save(tmp, "JPEG", quality=90)
    return tmp


# ========== 4. BUILD SATU SEGMEN ==========
def build_segment(teks, query, seg_idx):
    print(f"\n🎬 Segmen {seg_idx}")
    print(f"   📝 Teks : {teks[:70]}...")
    print(f"   🔍 Query: {query}")

    # 1) Gambar
    folder = os.path.join(RAW_DIR, f"seg_{seg_idx}")
    imgs = download_images(query, folder)
    if not imgs:
        print("      ⚠️ Tidak ada gambar, pakai placeholder.")
        ph = os.path.join(RAW_DIR, f"ph_{seg_idx}.jpg")
        Image.new("RGB", VIDEO_SIZE, (30, 30, 30)).save(ph)
        imgs = [ph]
    print(f"      → {len(imgs)} gambar")

    # 2) TTS
    teks_tts = teks[:MAX_CHARS_SEG]
    audio_path = os.path.join(RAW_DIR, f"a_{seg_idx}.mp3")
    gTTS(text=teks_tts, lang=LANG_TTS, slow=False).save(audio_path)
    audio = AudioFileClip(audio_path)

    # 3) Gabung gambar, durasi = audio / n
    per_img = audio.duration / len(imgs)
    img_clips = []
    for p in imgs:
        fit = fit_image(p)
        img_clips.append(ImageClip(fit).with_duration(per_img))

    video = concatenate_videoclips(img_clips, method="compose")
    video = video.with_audio(audio)
    print(f"   ✅ Durasi segmen: {video.duration:.1f}s")
    return video


# ========== 5. MAIN ==========
def main():
    segments = load_segments()
    print(f"📋 Total segmen: {len(segments)}\n")

    clips = []
    for i, (teks, query) in enumerate(segments, start=1):
        try:
            clip = build_segment(teks, query, i)
            clips.append(clip)
        except Exception as e:
            print(f"   ❌ Gagal segmen {i}: {e}")
            import traceback
            traceback.print_exc()

    if not clips:
        print("❌ Tidak ada segmen berhasil.")
        return

    print(f"\n🔗 Menggabungkan {len(clips)} segmen...")
    final = concatenate_videoclips(clips, method="compose")
    total = final.duration
    print(f"   Total durasi video: {total:.1f}s ({total/60:.1f} menit)")

    out_path = os.path.join(OUTPUT_DIR, "berita_final.mp4")
    print(f"\n💾 Menulis video ke {out_path} ...")
    final.write_videofile(
        out_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",   # ganti "medium" kalau mau kualitas lebih baik
        threads=2,
    )
    print(f"\n✅ Selesai: {out_path}")


if __name__ == "__main__":
    main()
