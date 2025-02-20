"""
modified to do transcribe at the beginning of silence detection for faster transcribe
"""
from RealtimeSTT import AudioToTextRecorder
import time
import logging
import numpy as np
import os
import struct
import collections
import itertools
import copy
import torch
import signal

INT16_MAX_ABS_VALUE = 32768.0
SAMPLE_RATE = 16000
class FasterAudioRecorder(AudioToTextRecorder):
    def _recording_worker(self):
        """
        The main worker method which constantly monitors the audio
        input for voice activity and accordingly starts/stops the recording.
        """

        logging.debug('Starting recording worker')
        if not hasattr(self, "transcribe_count"):
            self.transcribe_count = 0
        if not hasattr(self, "recording_judger"):
            self.recording_judger = lambda : True
        if not hasattr(self, "silero_off_sensitivity"):
            self.silero_off_sensitivity = self.silero_sensitivity
        try:
            was_recording = False
            delay_was_passed = False

            # Continuously monitor audio for voice activity
            while self.is_running:

                try:

                    data = self.audio_queue.get()
                    if self.on_recorded_chunk:
                        self.on_recorded_chunk(data)

                    if self.handle_buffer_overflow:
                        # Handle queue overflow
                        if (self.audio_queue.qsize() >
                                self.allowed_latency_limit):
                            logging.warning("Audio queue size exceeds "
                                            "latency limit. Current size: "
                                            f"{self.audio_queue.qsize()}. "
                                            "Discarding old audio chunks."
                                            )

                        while (self.audio_queue.qsize() >
                                self.allowed_latency_limit):

                            data = self.audio_queue.get()

                except BrokenPipeError:
                    print("BrokenPipeError _recording_worker")
                    self.is_running = False
                    break
                allow_record = self.recording_judger()
                if not allow_record:
                    self.is_recording = False
                    self.start_recording_on_voice_activity = True
                    self.frames.clear()
                    continue

                if not self.is_recording:
                    # Check for voice activity to
                    # trigger the start of recording
                    if (self.start_recording_on_voice_activity):

                        if self._is_silero_speech(data[:]):
                            logging.info("voice activity detected")

                            self.start()
                        else:
                            pass

                    self.speech_end_silence_start = 0

                else:
                    # If we are currently recording

                    # Stop the recording if silence is detected after speech
                    if self.stop_recording_on_voice_deactivity:

                        if self._is_not_silero_speech(data[:]):
                            # Voice deactivity was detected, so we start
                            # measuring silence time before stopping recording
                            if self.speech_end_silence_start == 0:
                                self.speech_end_silence_start = time.time()
                                if  (len(self.frames) > 0):
                                    # remove pending
                                    while self.parent_transcription_pipe.poll():
                                        status, result = self.parent_transcription_pipe.recv()
                                        self.transcribe_count -= 1
                                    audio_array = np.frombuffer(b''.join(self.frames), dtype=np.int16)
                                    audio = audio_array.astype(np.float32) / INT16_MAX_ABS_VALUE
                                    self.parent_transcription_pipe.send((audio, self.language))
                                    self.transcribe_count += 1

                        else:
                            self.speech_end_silence_start = 0

                        # Wait for silence to stop recording after speech
                        if self.speech_end_silence_start and time.time() - \
                                self.speech_end_silence_start > \
                                self.post_speech_silence_duration:
                            logging.info("voice deactivity detected")
                            self.stop()

                if not self.is_recording and was_recording:
                    # Reset after stopping recording to ensure clean state
                    self.stop_recording_on_voice_deactivity = False

                if time.time() - self.silero_check_time > 0.1:
                    self.silero_check_time = 0

                was_recording = self.is_recording

                if self.is_recording:
                    self.frames.append(data)

        except Exception as e:
            if not self.interrupt_stop_event.is_set():
                logging.error(f"Unhandled exeption in _recording_worker: {e}")
                raise
    
    def transcribe(self) -> str:
        self._set_state("transcribing")
        audio_copy = copy.deepcopy(self.audio)
        if self.transcribe_count == 0:
            self.parent_transcription_pipe.send((self.audio, self.language))
            self.transcribe_count += 1
        while self.transcribe_count > 0:
            status, result = self.parent_transcription_pipe.recv()
            self.transcribe_count -= 1
            
        self._set_state("inactive")
        if status == 'success':
            self.last_transcription_bytes = audio_copy
            return self._preprocess_output(result)
        else:
            logging.error(result)
            raise Exception(result)
        
    def _is_not_silero_speech(self, chunk):
        """
        This is similiar to is_silero_speech but use a different threshold
        """
        if self.sample_rate != 16000:
            pcm_data = np.frombuffer(chunk, dtype=np.int16)
            data_16000 = signal.resample_poly(
                pcm_data, 16000, self.sample_rate)
            chunk = data_16000.astype(np.int16).tobytes()

        self.silero_working = True
        audio_chunk = np.frombuffer(chunk, dtype=np.int16)
        audio_chunk = audio_chunk.astype(np.float32) / INT16_MAX_ABS_VALUE
        vad_prob = self.silero_vad_model(
            torch.from_numpy(audio_chunk),
            SAMPLE_RATE).item()
        is_not_silero_speech_active = vad_prob < (1 - self.silero_off_sensitivity)
        self.silero_working = False
        return is_not_silero_speech_active
    
    #For dynamic judgement of fast transcribe during recording. since I don't want it to transcribe when the AI is speaking at the same time, which can cause performance issue on my PC
    def set_recording_judger(self, judger):
        self.recording_judger = judger

    def set_silero_off_sensitivity(self, off_sens):
        self.silero_off_sensitivity = off_sens