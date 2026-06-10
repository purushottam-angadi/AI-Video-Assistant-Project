# from langchain_huggingface import data
# from pydub import AudioSegment
# import whisper
# import os
# from dotenv import load_dotenv
# from sarvamai import SarvamAI

# load_dotenv()  # Load environment variables from .env file

# SARVAM_PIECE_SECONDS = 25

# WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny, base, small, medium, large
# SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")  # updated default model


# _model = None

# # ---------------- Whisper ----------------
# def load_model():
#     global _model
#     if _model is None:
#         print(f"Loading Whisper model: {WHISPER_MODEL}...")
#         _model = whisper.load_model(WHISPER_MODEL)
#         print("Model loaded successfully.")
#     return _model

# def transcribe_audio_chunk_whisper(chunk_path: str) -> str:
#     model = load_model()
#     result = model.transcribe(chunk_path, task="transcribe")
#     return result['text']

# # ---------------- Sarvam ----------------
# client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

# def send_to_sarvam(piece_path: str) -> str:
#     """Send one ≤30s WAV file to Sarvam and return transcript."""
#     with open(piece_path, "rb") as f:
#         response = client.speech_to_text.transcribe(
#             file=f,
#             model=SARVAM_MODEL,
#             mode="translate"   # or "translate" if you want Hinglish→English
#         )
#     return response.transcript if hasattr(response, "transcript") else ""

# def transcribe_audio_chunk_sarvam(chunk_path: str) -> str:
#     """Split into ≤25s pieces and send each to Sarvam."""
#     if not SARVAM_API_KEY:
#         raise ValueError("SARVAM_API_KEY is not set in environment variables.")
    
#     audio = AudioSegment.from_wav(chunk_path)
#     piece_ms = SARVAM_PIECE_SECONDS * 1000
#     full_transcription = ""
#     total_pieces = (len(audio) + piece_ms - 1) // piece_ms

#     for i, start in enumerate(range(0, len(audio), piece_ms)):
#         piece = audio[start:start+piece_ms]
#         piece_path = f"{chunk_path}_piece_{i}.wav"
#         piece.export(piece_path, format="wav")

#         try:
#             print(f"Processing piece {i+1}/{total_pieces}")
#             transcription = send_to_sarvam(piece_path)
#             full_transcription += transcription + " "
#         finally:
#             if os.path.exists(piece_path):
#                 os.remove(piece_path)

#     return full_transcription.strip()

# # ---------------- Router ----------------
# def transcribe_audio_chunk(chunk_path: str, language: str="english") -> str:
#     """
#     Route one chunk to Whisper or Sarvam depending on language choice.
#     - english  → Whisper (local model)
#     - hinglish → Sarvam (translates to English while transcribing)
#     """
#     if language.lower() == "hinglish":
#         return transcribe_audio_chunk_sarvam(chunk_path)
#     else:
#         return transcribe_audio_chunk_whisper(chunk_path)

# def transcribe_full(chunks: list, language: str="english") -> str:
#     full_transcription = ""
#     engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
#     print(f"Starting transcription using {engine}...")
#     for i, chunk in enumerate(chunks):
#         print(f"Processing chunk {i+1}/{len(chunks)}")
#         transcription = transcribe_audio_chunk(chunk, language=language)
#         full_transcription += transcription + "\n"
#     print("Transcription completed")
#     return full_transcription.strip()


from pydub import AudioSegment

import os
import concurrent.futures
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

SARVAM_PIECE_SECONDS = 25
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_model = None

# ---------------- Faster Whisper ----------------
def load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"Loading Faster-Whisper model: {WHISPER_MODEL} on {DEVICE}...")
        _model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
        print("Model loaded successfully.")
    return _model

def unload_model():
    global _model
    _model = None
    import gc
    gc.collect()

def transcribe_audio_chunk_whisper(chunk_path: str) -> str:
    model = load_model()
    segments, info = model.transcribe(
        chunk_path,
        task="transcribe",
        beam_size=1,
        vad_filter=True,
        chunk_length=30
    )
    print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    return " ".join([segment.text.strip() for segment in segments])

# ---------------- Sarvam ----------------
def send_to_sarvam(piece_path: str, language: str = "hinglish") -> str:
    """Send one ≤30s WAV file to Sarvam and return transcript."""
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    with open(piece_path, "rb") as f:
        response = client.speech_to_text.transcribe(
            file=f,
            model=SARVAM_MODEL,
            mode="translate" if language.lower() == "hinglish" else "transcribe"
        )
    return response.transcript if hasattr(response, "transcript") else ""

def transcribe_audio_chunk_sarvam(chunk_path: str, language: str = "hinglish") -> str:
    """Split into ≤25s pieces and send each to Sarvam in parallel."""
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY is not set in environment variables.")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    piece_args = []
    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece_path = f"{chunk_path}_piece_{i}.wav"
        audio[start:start + piece_ms].export(piece_path, format="wav")
        piece_args.append((piece_path, i))

    def process_piece(args):
        piece_path, i = args
        try:
            print(f"Processing piece {i+1}/{total_pieces}")
            return i, send_to_sarvam(piece_path, language=language)
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    results = [None] * total_pieces
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for i, transcript in executor.map(process_piece, piece_args):
            results[i] = transcript

    return " ".join(t for t in results if t).strip()

# ---------------- Router ----------------
def transcribe_audio_chunk(chunk_path: str, language: str = "english") -> str:
    """
    Route one chunk to Faster-Whisper or Sarvam depending on language choice.
    - english  → Faster-Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_audio_chunk_sarvam(chunk_path, language=language)
    else:
        return transcribe_audio_chunk_whisper(chunk_path)

# def transcribe_full(chunks: list, language: str = "english") -> str:
#     parts = []
#     engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
#     print(f"Starting transcription using {engine}...")
#     for i, chunk in enumerate(chunks):
#         print(f"Processing chunk {i+1}/{len(chunks)}")
#         parts.append(transcribe_audio_chunk(chunk, language=language))
#     print("Transcription completed")
#     return "\n".join(parts).strip()

# main code:=
# def transcribe_full(chunks: list, language: str = "english") -> str:
#     engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
#     print(f"Starting transcription using {engine}...")

#     def process_chunk(args):
#         i, chunk = args
#         print(f"Processing chunk {i+1}/{len(chunks)}")
#         return i, transcribe_audio_chunk(chunk, language=language)

#     results = [None] * len(chunks)
#     # 🔥 CHANGE: parallelize chunk transcription
#     with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#         for i, transcript in executor.map(process_chunk, enumerate(chunks)):
#             results[i] = transcript

#     print("Transcription completed")
#     return "\n".join(t for t in results if t).strip()


# after getting error on railway memory ran out
# Replace transcribe_full with this sequential version
def transcribe_full(chunks: list, language: str = "english") -> str:
    engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
    print(f"Starting transcription using {engine}...")
    parts = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        parts.append(transcribe_audio_chunk(chunk, language=language))
        # Delete chunk file immediately after transcription
        if os.path.exists(chunk):
            os.remove(chunk)
    print("Transcription completed")
    return "\n".join(parts).strip()