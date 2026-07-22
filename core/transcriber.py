
#groq api
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_PIECE_SECONDS = 25

groq_client = Groq(api_key=GROQ_API_KEY)

def transcribe_audio_chunk_groq(chunk_path: str) -> str:
    """Send one chunk to Groq Whisper API and return transcript."""
    with open(chunk_path, "rb") as f:
        response = groq_client.audio.transcriptions.create(
            file=(os.path.basename(chunk_path), f),
            model="whisper-large-v3-turbo",
            language="en",
            response_format="text"
        )
    return response if isinstance(response, str) else response.text


def send_to_sarvam(piece_path: str) -> str:
    """Send one ≤25s WAV file to Sarvam and return transcript."""
    from sarvamai import SarvamAI
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    with open(piece_path, "rb") as f:
        response = client.speech_to_text.transcribe(
            file=f,
            model=SARVAM_MODEL,
            mode="translate"
        )
    return response.transcript if hasattr(response, "transcript") else ""

def transcribe_audio_chunk_sarvam(chunk_path: str) -> str:
    """Split into ≤25s pieces and send each to Sarvam."""
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY is not set.")

    from pydub import AudioSegment
    import concurrent.futures

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
            return i, send_to_sarvam(piece_path)
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    results = [None] * total_pieces
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for i, transcript in executor.map(process_piece, piece_args):
            results[i] = transcript

    return " ".join(t for t in results if t).strip()


def transcribe_audio_chunk(chunk_path: str, language: str = "english") -> str:
    if language.lower() == "hinglish":
        return transcribe_audio_chunk_sarvam(chunk_path)
    else:
        return transcribe_audio_chunk_groq(chunk_path)

def transcribe_full(chunks: list, language: str = "english") -> str:
    import concurrent.futures
    engine = "Sarvam AI" if language.lower() == "hinglish" else "Groq Whisper API"
    print(f"Starting transcription using {engine}...")

    def process_chunk(args):
        i, chunk = args
        print(f"Processing chunk {i+1}/{len(chunks)}")
        transcript = transcribe_audio_chunk(chunk, language=language)
        if os.path.exists(chunk):
            os.remove(chunk)
        return i, transcript

    max_workers = 3 if language.lower() != "hinglish" else 2

    results = [None] * len(chunks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, transcript in executor.map(process_chunk, enumerate(chunks)):
            results[i] = transcript

    print("Transcription completed")
    return "\n".join(t for t in results if t).strip()



# from pydub import AudioSegment

# import os
# import concurrent.futures
# from dotenv import load_dotenv
# from sarvamai import SarvamAI

# load_dotenv()

# SARVAM_PIECE_SECONDS = 25
# WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
# SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
# DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
# COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# _model = None


# def load_model():
#     global _model
#     if _model is None:
#         from faster_whisper import WhisperModel
#         print(f"Loading Faster-Whisper model: {WHISPER_MODEL} on {DEVICE}...")
#         _model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
#         print("Model loaded successfully.")
#     return _model

# def unload_model():
#     global _model
#     _model = None
#     import gc
#     gc.collect()

# def transcribe_audio_chunk_whisper(chunk_path: str) -> str:
#     model = load_model()
#     segments, info = model.transcribe(
#         chunk_path,
#         task="transcribe",
#         beam_size=1,
#         vad_filter=True,
#         chunk_length=30
#     )
#     print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
#     return " ".join([segment.text.strip() for segment in segments])

# def send_to_sarvam(piece_path: str, language: str = "hinglish") -> str:
#     """Send one ≤30s WAV file to Sarvam and return transcript."""
#     client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
#     with open(piece_path, "rb") as f:
#         response = client.speech_to_text.transcribe(
#             file=f,
#             model=SARVAM_MODEL,
#             mode="translate" if language.lower() == "hinglish" else "transcribe"
#         )
#     return response.transcript if hasattr(response, "transcript") else ""

# def transcribe_audio_chunk_sarvam(chunk_path: str, language: str = "hinglish") -> str:
#     """Split into ≤25s pieces and send each to Sarvam in parallel."""
#     if not SARVAM_API_KEY:
#         raise ValueError("SARVAM_API_KEY is not set in environment variables.")

#     audio = AudioSegment.from_wav(chunk_path)
#     piece_ms = SARVAM_PIECE_SECONDS * 1000
#     total_pieces = (len(audio) + piece_ms - 1) // piece_ms

#     piece_args = []
#     for i, start in enumerate(range(0, len(audio), piece_ms)):
#         piece_path = f"{chunk_path}_piece_{i}.wav"
#         audio[start:start + piece_ms].export(piece_path, format="wav")
#         piece_args.append((piece_path, i))

#     def process_piece(args):
#         piece_path, i = args
#         try:
#             print(f"Processing piece {i+1}/{total_pieces}")
#             return i, send_to_sarvam(piece_path, language=language)
#         finally:
#             if os.path.exists(piece_path):
#                 os.remove(piece_path)

#     results = [None] * total_pieces
#     with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#         for i, transcript in executor.map(process_piece, piece_args):
#             results[i] = transcript

#     return " ".join(t for t in results if t).strip()


# def transcribe_audio_chunk(chunk_path: str, language: str = "english") -> str:
#     """
#     Route one chunk to Faster-Whisper or Sarvam depending on language choice.
#     - english  → Faster-Whisper (local model)
#     - hinglish → Sarvam (translates to English while transcribing)
#     """
#     if language.lower() == "hinglish":
#         return transcribe_audio_chunk_sarvam(chunk_path, language=language)
#     else:
#         return transcribe_audio_chunk_whisper(chunk_path)

# # def transcribe_full(chunks: list, language: str = "english") -> str:
# #     parts = []
# #     engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
# #     print(f"Starting transcription using {engine}...")
# #     for i, chunk in enumerate(chunks):
# #         print(f"Processing chunk {i+1}/{len(chunks)}")
# #         parts.append(transcribe_audio_chunk(chunk, language=language))
# #     print("Transcription completed")
# #     return "\n".join(parts).strip()

# # main code:=
# # def transcribe_full(chunks: list, language: str = "english") -> str:
# #     engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
# #     print(f"Starting transcription using {engine}...")

# #     def process_chunk(args):
# #         i, chunk = args
# #         print(f"Processing chunk {i+1}/{len(chunks)}")
# #         return i, transcribe_audio_chunk(chunk, language=language)

# #     results = [None] * len(chunks)
# #     # CHANGE: parallelize chunk transcription
# #     with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
# #         for i, transcript in executor.map(process_chunk, enumerate(chunks)):
# #             results[i] = transcript

# #     print("Transcription completed")
# #     return "\n".join(t for t in results if t).strip()


# # after getting error on railway memory ran out
# # Replace transcribe_full with this sequential version
# def transcribe_full(chunks: list, language: str = "english") -> str:
#     engine = "Sarvam AI" if language.lower() == "hinglish" else "Faster-Whisper"
#     print(f"Starting transcription using {engine}...")
#     parts = []
#     for i, chunk in enumerate(chunks):
#         print(f"Processing chunk {i+1}/{len(chunks)}")
#         parts.append(transcribe_audio_chunk(chunk, language=language))
#         # Delete chunk file immediately after transcription
#         if os.path.exists(chunk):
#             os.remove(chunk)
#     print("Transcription completed")
#     return "\n".join(parts).strip()
