from openai import OpenAI
import numpy as np
import pyaudio
import wave
import io
import base64

client = OpenAI()


class SpeechRecorder:
    def __init__(self):
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1
        self.rate = 16000  # Record at 16000 samples per second
        self.silence_threshold = 500  # Adjust this threshold as needed
        self.silence_duration = (
            3  # Seconds of silence before considering speech finished
        )
        self.audio = pyaudio.PyAudio()
        self.conversation_history = []
        self.noise_levels = []

    def is_silent(self, data):
        """Returns 'True' if below the silence threshold"""
        max_value = np.frombuffer(data, dtype=np.int16).max()
        if not self.noise_levels:  # If noise_levels is empty, we are still calibrating
            self.noise_levels.append(max_value)
        return max_value < self.silence_threshold

    def adjust_silence_threshold(self):
        if self.noise_levels:
            self.silence_threshold = (
                np.mean(self.noise_levels) + 100
            )  # Add buffer to average noise level

    def record(self):
        stream = self.audio.open(
            format=self.sample_format,
            channels=self.channels,
            rate=self.rate,
            frames_per_buffer=self.chunk,
            input=True,
        )

        print("Adjusting for ambient noise...")
        print("Ready to record. Start speaking...")

        calibrating = True
        frames = []
        silent_chunks = 0
        is_recording = False

        try:
            while True:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                except IOError as e:
                    print(f"Error: {e}")
                    continue

                frames.append(data)

                if calibrating:
                    self.noise_levels.append(np.frombuffer(data, dtype=np.int16).max())
                    if (
                        len(self.noise_levels) > 50
                    ):  # Collect 50 chunks of ambient noise
                        calibrating = False
                        self.adjust_silence_threshold()
                        print(f"Calibrated silence threshold: {self.silence_threshold}")

                if self.is_silent(data) and not calibrating:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                    is_recording = True

                if is_recording and silent_chunks > (
                    self.silence_duration * self.rate / self.chunk
                ):
                    print("Speech chunk finished.")
                    break

            if is_recording:
                audio_buffer = io.BytesIO()
                wf = wave.open(audio_buffer, "wb")
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.sample_format))
                wf.setframerate(self.rate)
                wf.writeframes(b"".join(frames))
                wf.close()
                audio_buffer.seek(0)
                audio_buffer.name = "audio.wav"
                user_text = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_buffer
                )
                print(user_text.text)
                return user_text.text

        except Exception as e:
            print(f"Error during recording: {e}")

        finally:
            # Ensure the stream and PyAudio are stopped and released in all cases
            stream.stop_stream()
            stream.close()
            self.audio.terminate()
            print("Microphone resources released.")

    def close(self):
        self.audio.terminate()

    def gpt_speech(self, gpt_response_text):
        audio_buffer = io.BytesIO()
        with client.audio.speech.with_streaming_response.create(
            model="tts-1", voice="alloy", input=gpt_response_text
        ) as response:
            response.stream_to_file(audio_buffer)

        # Encode audio to base64
        audio_buffer.seek(0)
        audio_base64 = base64.b64encode(audio_buffer.read()).decode("utf-8")

        # Return or send the base64 string to React Native
        return audio_base64
