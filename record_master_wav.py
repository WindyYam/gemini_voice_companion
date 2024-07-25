# This is for recording the master user's voice so the AI companion can recognize. Others will be strangers
import pyaudio
import wave
import time

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 30
WAVE_OUTPUT_FILENAME = "sounds/master.wav"

# Initialize PyAudio
p = pyaudio.PyAudio()

# Open stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("We are going to record 30 seconds voice.")
for i in [3, 2, 1]:
    print(f"* Recording will start in {i} seconds...")
    time.sleep(1)
print("* Recording")

frames = []

# Record for RECORD_SECONDS
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("* Done recording")

# Stop and close the stream
stream.stop_stream()
stream.close()
p.terminate()

# Save the recorded data as a WAV file
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"* Audio saved as {WAVE_OUTPUT_FILENAME}")