from moviepy import ImageClip, concatenate_videoclips
import os
import glob

def buat_video_dari_gambar():
    # Cari semua gambar di folder saat ini
    daftar_gambar = sorted(glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png"))
    
    if not daftar_gambar:
        print("❌ Tidak ada gambar (.jpg/.png) di folder ini.")
        return

    print(f"[*] Ditemukan {len(daftar_gambar)} gambar. Memproses...")
    clips = []

    for gambar in daftar_gambar:
        print(f"   -> Memproses {gambar}")
        # Buat klip 3 detik untuk setiap gambar
        clip = ImageClip(gambar).with_duration(3)
        
        # Ubah ukuran ke vertikal 1080x1920
        clip = clip.resized(new_size=(1080, 1920))
        clips.append(clip)

    print("[*] Menggabungkan gambar menjadi video...")
    video_final = concatenate_videoclips(clips, method="compose")

    # Simpan sebagai MP4
    output_name = "video_1080x1920.mp4"
    video_final.write_videofile(output_name, fps=30, codec="libx264")
    
    print(f"✅ Selesai! Video disimpan sebagai: {output_name}")

if __name__ == "__main__":
    buat_video_dari_gambar()
