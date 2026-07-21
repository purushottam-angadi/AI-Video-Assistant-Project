# # from pydub import AudioSegment
# # from urllib.parse import urlparse, parse_qs
# # import os
# # import gc

# # DOWNLOAD_DIR = "downloads"
# # os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # # ---------------- YouTube transcript helpers ----------------
# # def is_youtube_url(source: str) -> bool:
# #     """Check if the given source string is a YouTube URL."""
# #     return "youtube.com" in source or "youtu.be" in source
 
 
# # def extract_video_id(url: str) -> str:
# #     """Extract the video ID from a YouTube URL (watch, youtu.be, embed, shorts)."""
# #     parsed = urlparse(url)
# #     host = (parsed.hostname or "").lower()
 
# #     if host in ("youtu.be",):
# #         return parsed.path.lstrip("/").split("/")[0]
 
# #     if host in ("www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"):
# #         if parsed.path == "/watch":
# #             video_id = parse_qs(parsed.query).get("v", [None])[0]
# #             if video_id:
# #                 return video_id
# #         for prefix in ("/embed/", "/v/", "/shorts/"):
# #             if parsed.path.startswith(prefix):
# #                 return parsed.path.split("/")[2]
 
# #     raise ValueError(f"Could not extract video ID from URL: {url}")
 
 
# # def get_youtube_transcript(url: str, language: str = "english") -> str:
# #     """
# #     Fetch the transcript for a YouTube video directly (no audio download/transcription).
 
# #     - english  -> prefer English captions ('en')
# #     - hinglish -> prefer Hindi captions ('hi'), fall back to English
# #     """
# #     from youtube_transcript_api import YouTubeTranscriptApi
 
# #     video_id = extract_video_id(url)
 
# #     lang_codes = ["hi", "en"] if language.lower() == "hinglish" else ["en", "hi"]
 
# #     if hasattr(YouTubeTranscriptApi, "get_transcript"):
# #         transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_codes)
# #         text = " ".join(segment["text"].strip() for segment in transcript_list if segment.get("text"))
# #     else:
# #         fetched = YouTubeTranscriptApi().fetch(video_id, languages=lang_codes)
# #         text = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)
 
# #     return text.strip()

# # def convert_to_wav(input_path: str) -> str:
# #     audio = AudioSegment.from_file(input_path)
# #     audio = audio.set_channels(1).set_frame_rate(16000)
# #     base_name = os.path.splitext(os.path.basename(input_path))[0]
# #     filename = os.path.join(DOWNLOAD_DIR, base_name + '_converted.wav')
# #     audio.export(filename, format='wav')
# #     del audio
# #     gc.collect()
# #     return filename

# # def convert_to_chunks(wav_path: str, chunk_length_mins: int = 1) -> list:
# #     audio = AudioSegment.from_wav(wav_path)
# #     if len(audio) == 0:
# #      raise ValueError(f"Audio file is empty: {wav_path}")
# #     chunk_length_ms = chunk_length_mins * 60 * 1000
# #     chunks = []
# #     for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
# #         chunk = audio[start:start + chunk_length_ms]
# #         chunk_path = f"{os.path.splitext(wav_path)[0]}_chunk_{i}.wav"
# #         chunk.export(chunk_path, format='wav')
# #         del chunk
# #         gc.collect()
# #         chunks.append(chunk_path)
# #     del audio
# #     gc.collect()
# #     return chunks

# # def process_audio(source: str) -> list:
# #     print("Processing local audio file...")
# #     wav_path = convert_to_wav(source)
# #     print("Splitting audio into chunks...")
# #     chunks = convert_to_chunks(wav_path)
# #     if os.path.exists(wav_path):
# #         os.remove(wav_path)
# #     print(f"Audio processing complete. Generated {len(chunks)} chunks.")
# #     return chunks


# from urllib.parse import urlparse, parse_qs
# import subprocess
# import os

# DOWNLOAD_DIR = "downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # ---------------- YouTube transcript helpers ----------------
# def is_youtube_url(source: str) -> bool:
#     """Check if the given source string is a YouTube URL."""
#     return "youtube.com" in source or "youtu.be" in source


# def extract_video_id(url: str) -> str:
#     """Extract the video ID from a YouTube URL (watch, youtu.be, embed, shorts)."""
#     parsed = urlparse(url)
#     host = (parsed.hostname or "").lower()

#     if host in ("youtu.be",):
#         return parsed.path.lstrip("/").split("/")[0]

#     if host in ("www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"):
#         if parsed.path == "/watch":
#             video_id = parse_qs(parsed.query).get("v", [None])[0]
#             if video_id:
#                 return video_id
#         for prefix in ("/embed/", "/v/", "/shorts/"):
#             if parsed.path.startswith(prefix):
#                 return parsed.path.split("/")[2]

#     raise ValueError(f"Could not extract video ID from URL: {url}")


# def get_youtube_transcript(url: str, language: str = "english") -> str:
#     """
#     Fetch the transcript for a YouTube video directly (no audio download/transcription).

#     - english  -> prefer English captions ('en')
#     - hinglish -> prefer Hindi captions ('hi'), fall back to English
#     """
#     from youtube_transcript_api import YouTubeTranscriptApi

#     video_id = extract_video_id(url)
#     lang_codes = ["hi", "en"] if language.lower() == "hinglish" else ["en", "hi"]

#     if hasattr(YouTubeTranscriptApi, "get_transcript"):
#         transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_codes)
#         text = " ".join(segment["text"].strip() for segment in transcript_list if segment.get("text"))
#     else:
#         fetched = YouTubeTranscriptApi().fetch(video_id, languages=lang_codes)
#         text = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)

#     return text.strip()


# # ---------------- Audio chunking (streamed via ffmpeg) ----------------
# def process_audio(source: str, chunk_length_secs: int = 60) -> list:
#     """
#     Splits `source` directly into 16kHz mono WAV chunks using ffmpeg's segment
#     muxer, streaming the whole way through.

#     This replaces the old two-pass pydub approach (convert_to_wav then
#     convert_to_chunks), which decoded the entire file into Python memory
#     TWICE — once for the full-length conversion, once again to reload it for
#     chunking. ffmpeg here writes chunks straight to disk without Python ever
#     holding decoded audio in RAM.
#     """
#     base_name = os.path.splitext(os.path.basename(source))[0]
#     pattern = os.path.join(DOWNLOAD_DIR, f"{base_name}_chunk_%03d.wav")

#     cmd = [
#         "ffmpeg", "-y", "-i", source,
#         "-ar", "16000", "-ac", "1",
#         "-f", "segment", "-segment_time", str(chunk_length_secs),
#         pattern,
#     ]

#     print("Splitting audio into chunks via ffmpeg...")
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     if result.returncode != 0:
#         raise RuntimeError(f"ffmpeg failed: {result.stderr}")

#     chunks = sorted(
#         os.path.join(DOWNLOAD_DIR, f)
#         for f in os.listdir(DOWNLOAD_DIR)
#         if f.startswith(f"{base_name}_chunk_") and f.endswith(".wav")
#     )
#     if not chunks:
#         raise ValueError(f"No chunks produced for {source}")

#     print(f"Audio processing complete. Generated {len(chunks)} chunks.")
#     return chunks

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


# ---------------- Audio processing (single pass) ----------------
def process_audio(source: str) -> list:
    """
    Load the audio file once, convert to 16kHz mono, and split into
    1-minute WAV chunks — all in a single pass.

    Old approach loaded the file twice (convert_to_wav then convert_to_chunks)
    causing a 2x memory spike. This version loads once and frees immediately
    after chunking, halving the peak memory usage.
    """
    print("Processing local audio file...")

    # Single load — convert channels and sample rate in place
    audio = AudioSegment.from_file(source)
    audio = audio.set_channels(1).set_frame_rate(16000)

    if len(audio) == 0:
        raise ValueError(f"Audio file is empty: {source}")

    chunk_length_ms = 60 * 1000
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start:start + chunk_length_ms]
        chunk_path = os.path.join(DOWNLOAD_DIR, f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        del chunk
        gc.collect()
        chunks.append(chunk_path)

    # Free the full audio object immediately after chunking
    del audio
    gc.collect()

    print(f"Audio processing complete. Generated {len(chunks)} chunks.")
    return chunks