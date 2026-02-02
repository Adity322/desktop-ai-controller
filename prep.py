import time
import pvporcupine
import pyaudio
import speech_recognition as sr
from typing import Optional
def create_porcupine(porcupine_key: str, keyword_path: str):
    porcupine = pvporcupine.create(
        access_key=porcupine_key,
        keyword_paths=[keyword_path]
    )

    pa = pyaudio.PyAudio()

    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )

    return porcupine, pa, audio_stream


def destroy_porcupine(porcupine, audio_stream, pa):
    try:
        audio_stream.stop_stream()
        audio_stream.close()
    except:
        pass

    try:
        porcupine.delete()
    except:
        pass

    try:
        pa.terminate()
    except:
        pass

    time.sleep(0.8)  # 🔥 critical on macOS


class AudioManager:
    def __init__(self, porcupine_key: str, keyword_path: str):
        self.porcupine_key = porcupine_key
        self.keyword_path = keyword_path

        self.porcupine = None
        self.pa = None
        self.audio_stream = None

    # ---------- WAKE WORD ----------
    def start_wake_word(self):
        from prep import create_porcupine
        self.porcupine, self.pa, self.audio_stream = create_porcupine(
            self.porcupine_key,
            self.keyword_path
        )

    def stop_wake_word(self):
        from prep import destroy_porcupine
        destroy_porcupine(self.porcupine, self.audio_stream, self.pa)
        self.porcupine = None
        self.pa = None
        self.audio_stream = None

    # ---------- COMMAND LISTEN ----------
    def listen_once(
        self,
        timeout: int = 7,
        phrase_time_limit: int = 10
    ) -> Optional[str]:

        recognizer = sr.Recognizer()

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            return recognizer.recognize_google(audio).lower()

        except (sr.UnknownValueError, sr.WaitTimeoutError):
            return None
