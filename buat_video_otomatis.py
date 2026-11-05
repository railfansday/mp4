from icrawler.builtin import BingImageCrawler
from moviepy import ImageClip, concatenate_videoclips
import os
import shutil
import glob

# ==========================================
# KONFIGURASI
# ==========================================
KEYWORD_FILE = "keyword.txt"  
TEMP_DIR = "temp_gambar"
JUMLAH_GAMBAR = 10

def bersihkan_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def buat_video():
    if not os.path.exists(KEYWORD_FILE):
        print("❌ File keyword.txt tidak ditemukan!")
        return
        
    # ✅ BACA FILE PER BARIS (Bukan sekaligus)
    with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
        daftar_keyword = [line.strip() for line in f if line.strip()]
        
    if not daftar_keyword:
        print("❌ Kata kunci kosong.")
        return

    # ✅ LOOPING UNTUK SETIAP KEYWORD
    for i, keyword in enumerate(daftar_keyword):
        print(f"\n[{i+1}/{len(daftar_keyword)}] Mencari gambar untuk: '{keyword}'")
        
        folder_keyword = os.path.join(TEMP_DIR, f"kw_{i}")
        bersihkan_folder(folder_keyword)

        # 1. Scrape Gambar
        crawler = BingImageCrawler(storage={'root_dir': folder_keyword})
        crawler.crawl(keyword=keyword, max_num=JUMLAH_GAMBAR)
        
        daftar_gambar = sorted(glob.glob(f"{folder_keyword}/*.jpg") + glob.glob(f"{folder_keyword}/*.png"))
        
        if not daftar_gambar:
            print(f"   ⚠️ Gagal mengunduh gambar untuk {keyword}. Lanjut...")
            continue
            
        print(f"   ✅ Berhasil mengunduh {len(daftar_gambar)} gambar.")

        # 2. Buat Video
        clips = []
        for img_path in daftar_gambar:
            try:
                clip = ImageClip(img_path).with_duration(3)
                clip = clip.resized(height=1920)
                clip = cropped_clip = clip.cropped(x_center=clip.w/2, width=1080)
                clips.append(clip)
            except Exception:
                pass

        if clips:
            video_final = concatenate_videoclips(clips, method="compose")
            
            # Buat nama file aman (hilangkan spasi)
            nama_aman = "".join(c if c.isalnum() else "_" for c in keyword)
            output_video = f"video_{nama_aman}.mp4"
            
            video_final.write_videofile(output_video, fps=30, codec="libx264", logger=None)
            print(f"   🎬 Selesai! Video disimpan: {output_video}")
            
            # Hapus folder temp agar tidak menumpuk
            shutil.rmtree(folder_keyword)

if __name__ == "__main__":
    buat_video()
