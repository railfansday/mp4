from icrawler.builtin import BingImageCrawler
from moviepy import ImageClip, concatenate_videoclips
import os
import shutil
import glob

# ==========================================
# KONFIGURASI
# ==========================================
KEYWORD_FILE = "keyword.txt"  # File yang berisi teks "xiaomi 15 t"
TEMP_DIR = "temp_gambar"
OUTPUT_VIDEO = "video_1080x1920.mp4"
JUMLAH_GAMBAR = 10

def bersihkan_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def buat_video():
    # 1. Baca kata kunci
    if not os.path.exists(KEYWORD_FILE):
        print("❌ File keyword.txt tidak ditemukan!")
        return
        
    with open(KEYWORD_FILE, "r") as f:
        keyword = f.read().strip()
        
    if not keyword:
        print("❌ Kata kunci kosong.")
        return

    print(f"[*] Mencari gambar untuk: '{keyword}'")
    bersihkan_folder(TEMP_DIR)

    # 2. Scrape Gambar (menggunakan Bing Image Crawler)
    crawler = BingImageCrawler(storage={'root_dir': TEMP_DIR})
    crawler.crawl(keyword=keyword, max_num=JUMLAH_GAMBAR)
    
    # Kumpulkan gambar yang berhasil diunduh
    daftar_gambar = sorted(glob.glob(f"{TEMP_DIR}/*.jpg") + glob.glob(f"{TEMP_DIR}/*.png"))
    
    if not daftar_gambar:
        print("❌ Gagal mengunduh gambar.")
        return
        
    print(f"[*] Berhasil mengunduh {len(daftar_gambar)} gambar.")

    # 3. Buat Video MP4 1080x1920
    print("[*] Membuat video vertikal...")
    clips = []
    for img_path in daftar_gambar:
        try:
            # Setiap gambar tampil selama 3 detik
            clip = ImageClip(img_path).with_duration(3)
            
            # Resize dan Crop agar pas 1080x1920 tanpa gepeng
            # (Resize agar sisi terpendek 1080, lalu crop bagian tengah)
            clip = clip.resized(height=1920)
            clip = clip.cropped(x_center=clip.w/2, width=1080)
            
            clips.append(clip)
        except Exception as e:
            print(f"   ⚠️ Gagal memproses {img_path}: {e}")

    if not clips:
        print("❌ Tidak ada klip yang valid untuk digabungkan.")
        return

    video_final = concatenate_videoclips(clips, method="compose")
    
    # Simpan video
    video_final.write_videofile(OUTPUT_VIDEO, fps=30, codec="libx264")
    print(f"✅ Selesai! Video disimpan sebagai: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    buat_video()
