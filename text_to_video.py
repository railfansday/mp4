from gtts import gTTS
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from icrawler.builtin import BingImageCrawler
import os
import shutil
import glob
import math

# ==========================================
# KONFIGURASI
# ==========================================
FILE_TEKS = "teks.txt"
TEMP_DIR = "temp_gambar_teks"
OUTPUT_VIDEO = "video_dari_teks.mp4"
JUMLAH_GAMBAR_PER_KALIMAT = 2  # Ambil 2 gambar untuk setiap potongan teks

def bersihkan_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

def buat_video_dari_teks():
    if not os.path.exists(FILE_TEKS):
        print("❌ File teks.txt tidak ditemukan!")
        return

    # 1. Baca Teks
    with open(FILE_TEKS, "r", encoding="utf-8") as f:
        teks_lengkap = f.read().strip()

    if not teks_lengkap:
        print("❌ Teks kosong.")
        return

    # 2. Buat Suara (TTS) menggunakan gTTS
    print("[*] Membuat suara dari teks...")
    audio_file = "suara_teks.mp3"
    tts = gTTS(text=teks_lengkap, lang='id', slow=False) # 'id' untuk bahasa Indonesia
    tts.save(audio_file)
    
    # Dapatkan durasi suara
    audio_clip = AudioFileClip(audio_file)
    total_durasi = audio_clip.duration
    print(f"   ✅ Suara dibuat. Durasi total: {total_durasi:.2f} detik.")

    # 3. Pecah Teks Menjadi Kalimat & Cari Gambar
    # Kita pecah berdasarkan titik (.) agar setiap gambar relevan dengan kalimatnya
    kalimat_list = [k.strip() for k in teks_lengkap.split('.') if k.strip()]
    
    # Perkiraan: Durasi per kalimat = Total durasi / Jumlah kalimat
    durasi_per_kalimat = total_durasi / len(kalimat_list)
    
    bersihkan_folder(TEMP_DIR)
    semua_gambar = []

    for i, kalimat in enumerate(kalimat_list):
        print(f"[*] Mencari gambar untuk kalimat: '{kalimat[:40]}...'")
        
        # Cari gambar menggunakan Bing berdasarkan kalimat (atau kata kuncinya)
        # Disarankan menggunakan kata kunci (2-3 kata) agar hasil gambar lebih akurat
        kata_kunci = " ".join(kalimat.split()[:3]) 
        
        folder_kalimat = os.path.join(TEMP_DIR, f"kal_{i}")
        crawler = BingImageCrawler(storage={'root_dir': folder_kalimat})
        crawler.crawl(keyword=kata_kunci, max_num=JUMLAH_GAMBAR_PER_KALIMAT)
        
        gambar_ditemukan = sorted(glob.glob(f"{folder_kalimat}/*.jpg") + glob.glob(f"{folder_kalimat}/*.png"))
        
        # Hitung berapa lama 1 gambar harus tampil
        if gambar_ditemukan:
            durasi_per_gambar = durasi_per_kalimat / len(gambar_ditemukan)
            for img_path in gambar_ditemukan:
                try:
                    # Buat klip gambar dengan durasi yang sudah dihitung
                    clip = ImageClip(img_path).with_duration(durasi_per_gambar)
                    # Resize vertikal 1080x1920
                    clip = clip.resized(height=1920)
                    clip = clip.cropped(x_center=clip.w/2, width=1080)
                    semua_gambar.append(clip)
                except Exception:
                    pass

    if not semua_gambar:
        print("❌ Tidak ada gambar yang berhasil diproses.")
        return

    # 4. Gabungkan Gambar & Suara
    print(f"[*] Menggabungkan {len(semua_gambar)} gambar menjadi video...")
    video_final = concatenate_videoclips(semua_gambar, method="compose")
    
    # Pasang suara ke video
    video_final = video_final.with_audio(audio_clip)

    # 5. Simpan Video
    video_final.write_videofile(OUTPUT_VIDEO, fps=30, codec="libx264", audio_codec="aac")
    print(f"✅ Selesai! Video disimpan sebagai: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    buat_video_dari_teks()
