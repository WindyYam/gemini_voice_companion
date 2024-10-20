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

INT16_MAX_ABS_VALUE = 32768.0

class FasterAudioRecorder(AudioToTextRecorder):
    def _recording_worker(self):
        """
        The main worker method which constantly monitors the audio
        input for voice activity and accordingly starts/stops the recording.
        """

        logging.debug('Starting recording worker')
        if not hasattr(self, "transcribe_count"):
            self.transcribe_count = 0
        if not hasattr(self, "fast_transcribe_on_recording_judger"):
            self.fast_transcribe_on_recording_judger = lambda : True
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

                if not self.is_recording:
                    # Handle not recording state
                    time_since_listen_start = (time.time() - self.listen_start
                                               if self.listen_start else 0)

                    wake_word_activation_delay_passed = (
                        time_since_listen_start >
                        self.wake_word_activation_delay
                    )

                    # Handle wake-word timeout callback
                    if wake_word_activation_delay_passed \
                            and not delay_was_passed:

                        if self.use_wake_words and self.wake_word_activation_delay:
                            if self.on_wakeword_timeout:
                                self.on_wakeword_timeout()
                    delay_was_passed = wake_word_activation_delay_passed

                    # Set state and spinner text
                    if not self.recording_stop_time:
                        if self.use_wake_words \
                                and wake_word_activation_delay_passed \
                                and not self.wakeword_detected:
                            self._set_state("wakeword")
                        else:
                            if self.listen_start:
                                self._set_state("listening")
                            else:
                                self._set_state("inactive")

                    #self.wake_word_detect_time = time.time()
                    if self.use_wake_words and wake_word_activation_delay_passed:
                        try:
                            wakeword_index = self._process_wakeword(data)

                        except struct.error:
                            logging.error("Error unpacking audio data "
                                          "for wake word processing.")
                            continue

                        except Exception as e:
                            logging.error(f"Wake word processing error: {e}")
                            continue

                        # If a wake word is detected                        
                        if wakeword_index >= 0:

                            # Removing the wake word from the recording
                            samples_time = int(self.sample_rate * self.wake_word_buffer_duration)
                            start_index = max(
                                0,
                                len(self.audio_buffer) - samples_time
                                )
                            temp_samples = collections.deque(
                                itertools.islice(
                                    self.audio_buffer,
                                    start_index,
                                    None)
                                )
                            self.audio_buffer.clear()
                            self.audio_buffer.extend(temp_samples)

                            self.wake_word_detect_time = time.time()
                            self.wakeword_detected = True
                            #self.wake_word_cooldown_time = time.time()
                            if self.on_wakeword_detected:
                                self.on_wakeword_detected()

                    # Check for voice activity to
                    # trigger the start of recording
                    if ((not self.use_wake_words
                         or not wake_word_activation_delay_passed)
                            and self.start_recording_on_voice_activity) \
                            or self.wakeword_detected:

                        if self._is_voice_active():
                            logging.info("voice activity detected")

                            self.start()

                            if self.is_recording:
                                self.start_recording_on_voice_activity = False

                                # Add the buffered audio
                                # to the recording frames
                                self.frames.extend(list(self.audio_buffer))
                                self.audio_buffer.clear()

                            self.silero_vad_model.reset_states()
                        else:
                            #pass
                            data_copy = data[:]
                            self._check_voice_activity(data_copy)

                    self.speech_end_silence_start = 0

                else:
                    # If we are currently recording

                    # Stop the recording if silence is detected after speech
                    if self.stop_recording_on_voice_deactivity:

                        if not self._is_webrtc_speech(data, True):
                            # Voice deactivity was detected, so we start
                            # measuring silence time before stopping recording
                            if self.speech_end_silence_start == 0:
                                self.speech_end_silence_start = time.time()
                                if self.fast_transcribe_on_recording_judger() and (len(self.frames) > 0):
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

                # Handle wake word timeout (waited to long initiating
                # speech after wake word detection)
                if self.wake_word_detect_time and time.time() - \
                        self.wake_word_detect_time > self.wake_word_timeout:

                    self.wake_word_detect_time = 0
                    if self.wakeword_detected and self.on_wakeword_timeout:
                        self.on_wakeword_timeout()
                    self.wakeword_detected = False

                was_recording = self.is_recording

                if self.is_recording:
                    self.frames.append(data)

                if not self.is_recording or self.speech_end_silence_start:
                    self.audio_buffer.append(data)

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
    
    #For dynamic judgement of fast transcribe during recording. since I don't want it to transcribe when the AI is speaking at the same time, which can cause performance issue on my PC
    def set_fast_transcribe_on_recording_judger(self, judger):
        self.fast_transcribe_on_recording_judger = judger
