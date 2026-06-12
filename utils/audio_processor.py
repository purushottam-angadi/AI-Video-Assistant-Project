from pydub import AudioSegment
from urllib.parse import urlparse, parse_qs
import os
import gc

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---------------- YouTube transcript helpers ----------------
def is_youtube_url(source: str) -> bool:
    """Check if the given source string is a YouTube URL."""
    return "youtube.com" in source or "youtu.be" in source
 
 
def extract_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL (watch, youtu.be, embed, shorts)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
 
    if host in ("youtu.be",):
        return parsed.path.lstrip("/").split("/")[0]
 
    if host in ("www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id:
                return video_id
        for prefix in ("/embed/", "/v/", "/shorts/"):
            if parsed.path.startswith(prefix):
                return parsed.path.split("/")[2]
 
    raise ValueError(f"Could not extract video ID from URL: {url}")
 
 
def get_youtube_transcript(url: str, language: str = "english") -> str:
    """
    Fetch the transcript for a YouTube video directly (no audio download/transcription).
 
    - english  -> prefer English captions ('en')
    - hinglish -> prefer Hindi captions ('hi'), fall back to English
    """
    from youtube_transcript_api import YouTubeTranscriptApi
 
    video_id = extract_video_id(url)
 
    lang_codes = ["hi", "en"] if language.lower() == "hinglish" else ["en", "hi"]
 
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_codes)
        text = " ".join(segment["text"].strip() for segment in transcript_list if segment.get("text"))
    else:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=lang_codes)
        text = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)
 
    return text.strip()

def convert_to_wav(input_path: str) -> str:
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    filename = os.path.join(DOWNLOAD_DIR, base_name + '_converted.wav')
    audio.export(filename, format='wav')
    del audio
    gc.collect()
    return filename

def convert_to_chunks(wav_path: str, chunk_length_mins: int = 1) -> list:
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
    print("Processing local audio file...")
    wav_path = convert_to_wav(source)
    print("Splitting audio into chunks...")
    chunks = convert_to_chunks(wav_path)
    if os.path.exists(wav_path):
        os.remove(wav_path)
    print(f"Audio processing complete. Generated {len(chunks)} chunks.")
    return chunks
