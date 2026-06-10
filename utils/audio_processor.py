import yt_dlp
from pydub import AudioSegment
import os
import gc

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_audio_from_youtube(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'worstaudio/worst',  # lowest quality = smallest file
        'outtmpl': output_path,
        'cookiefile': 'cookies.txt',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '64',  # lowered from 192
        }],
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        audio_file = ydl.prepare_filename(info_dict).replace('.webm', '.wav').replace('.m4a', '.wav').replace('.mp4', '.wav')
        return audio_file

def convert_to_wav(input_path: str) -> str:
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    filename = os.path.join(DOWNLOAD_DIR, base_name + '_converted.wav')
    audio.export(filename, format='wav')
    del audio
    gc.collect()
    return filename

def convert_to_chunks(wav_path: str, chunk_length_mins: int=3) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_length_ms = chunk_length_mins * 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start:start + chunk_length_ms]
        chunk_path = f"{os.path.splitext(wav_path)[0]}_chunk_{i}.wav"
        chunk.export(chunk_path, format='wav')
        del chunk
        gc.collect()
        chunks.append(chunk_path)

    del audio
    gc.collect()
    return chunks

def process_audio(source: str) -> list:
    if source.startswith("http") or source.startswith("https"):
        print("Downloading audio from YouTube...")
        wav_path = download_audio_from_youtube(source)
    else:
        print("Processing local audio file...")
        wav_path = convert_to_wav(source)

    print("Splitting audio into chunks...")
    chunks = convert_to_chunks(wav_path)

    if os.path.exists(wav_path):
        os.remove(wav_path)

    print(f"Audio processing complete. Generated {len(chunks)} chunks.")
    return chunks