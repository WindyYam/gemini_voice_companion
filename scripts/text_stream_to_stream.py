from RealtimeTTS import TextToAudioStream
import stream2sentence as s2s
import threading
import traceback
import logging
import queue
import time
import wave
from typing import Iterator

class TextStreamToAudioStream(TextToAudioStream):
    def play_async(self,
                   external_text_iterator: Iterator[str],
                   fast_sentence_fragment: bool = True,
                   buffer_threshold_seconds: float = 0.0,
                   minimum_sentence_length: int = 10, 
                   minimum_first_fragment_length: int = 10,
                   log_synthesized_text=False,
                   reset_generated_text: bool = True,
                   output_wavfile: str = None,
                   on_sentence_synthesized=None,
                   before_sentence_synthesized=None,
                   on_audio_chunk=None,
                   tokenizer: str = "",
                   tokenize_sentences=None,
                   language: str = "",
                   context_size: int = 12,
                   muted: bool = False,
                   sentence_fragment_delimiters: str = ".?!;:,\n…)]}。-",
                   force_first_fragment_after_words=15,
                   ):
        """
        Async handling of text to audio synthesis, see play() method.
        """
        if not self.is_playing_flag:
            self.is_playing_flag = True
            # Pass additional parameter to differentiate external call
            args = (external_text_iterator, fast_sentence_fragment, buffer_threshold_seconds, minimum_sentence_length, 
                    minimum_first_fragment_length, log_synthesized_text, reset_generated_text, 
                    output_wavfile, on_sentence_synthesized, before_sentence_synthesized, on_audio_chunk, tokenizer, tokenize_sentences, 
                    language, context_size, muted, sentence_fragment_delimiters, 
                    force_first_fragment_after_words, True)
            self.play_thread = threading.Thread(target=self.play, args=args)
            self.play_thread.start()
        else:
            logging.warning("play_async() called while already playing audio, skipping")

    def play(
            self,
            external_text_iterator: Iterator[str],
            fast_sentence_fragment: bool = True,
            buffer_threshold_seconds: float = 0.0,
            minimum_sentence_length: int = 10,
            minimum_first_fragment_length: int = 10,
            log_synthesized_text=False,
            reset_generated_text: bool = True,
            output_wavfile: str = None,
            on_sentence_synthesized=None,
            before_sentence_synthesized=None,
            on_audio_chunk=None,
            tokenizer: str = "nltk",
            tokenize_sentences=None,
            language: str = "en",
            context_size: int = 12,
            muted: bool = False,
            sentence_fragment_delimiters: str = ".?!;:,\n…)]}。-",
            force_first_fragment_after_words=15,
            is_external_call=True,
            ):
        """
        Handles the synthesis of text to audio.
        Plays the audio stream and waits until it is finished playing.
        If the engine can't consume generators, it utilizes a player.

        Args:
        - fast_sentence_fragment: Determines if sentence fragments should be quickly yielded. Useful when a faster response is desired even if a sentence isn't complete.
        - buffer_threshold_seconds (float): Time in seconds for the buffering threshold, influencing the flow and continuity of audio playback. Set to 0 to deactivate. Default is 0.
          - How it Works: The system verifies whether there is more audio content in the buffer than the duration defined by buffer_threshold_seconds. If so, it proceeds to synthesize the next sentence, capitalizing on the remaining audio to maintain smooth delivery. A higher value means more audio is pre-buffered, which minimizes pauses during playback. Adjust this upwards if you encounter interruptions.
          - Helps to decide when to generate more audio based on buffered content.
        - minimum_sentence_length (int): The minimum number of characters a sentence must have. If a sentence is shorter, it will be concatenated with the following one, improving the overall readability. This parameter does not apply to the first sentence fragment, which is governed by `minimum_first_fragment_length`. Default is 10 characters.
        - minimum_first_fragment_length (int): The minimum number of characters required for the first sentence fragment before yielding. Default is 10 characters.
        - log_synthesized_text: If True, logs the synthesized text chunks.
        - reset_generated_text: If True, resets the generated text.
        - output_wavfile: If set, saves the audio to the specified WAV file.
        - on_sentence_synthesized: Callback function that gets called after hen a single sentence fragment was synthesized.
        - before_sentence_synthesized: Callback function that gets called before a single sentence fragment gets synthesized.
        - on_audio_chunk: Callback function that gets called when a single audio chunk is ready.
        - tokenizer: Tokenizer to use for sentence splitting (currently "nltk" and "stanza" are supported).
        - tokenize_sentences (Callable): A function that tokenizes sentences from the input text. You can write your own lightweight tokenizer here if you are unhappy with nltk and stanza. Defaults to None. Takes text as string and should return splitted sentences as list of strings.
        - language: Language to use for sentence splitting.
        - context_size: The number of characters used to establish context for sentence boundary detection. A larger context improves the accuracy of detecting sentence boundaries. Default is 12 characters.
        - muted: If True, disables audio playback via local speakers (in case you want to synthesize to file or process audio chunks). Default is False.
        - sentence_fragment_delimiters (str): A string of characters that are
            considered sentence delimiters. Default is ".?!;:,\n…)]}。-".
        - force_first_fragment_after_words (int): The number of words after
            which the first sentence fragment is forced to be yielded.
            Default is 15 words.
        """
        if self.global_muted:
            muted = True

        if is_external_call:
            if not self.play_lock.acquire(blocking=False):
                logging.warning("play() called while already playing audio, skipping")
                return

        self.is_playing_flag = True

        # Log the start of the stream
        logging.info(f"stream start")

        tokenizer = tokenizer if tokenizer else self.tokenizer 
        language = language if language else self.language

        # Set the stream_running flag to indicate the stream is active
        self.stream_start_time = time.time()
        self.stream_running = True
        abort_event = threading.Event()
        self.abort_events.append(abort_event)

        if self.player:
            self.player.mute(muted)
        elif hasattr(self.engine, "set_muted"):
            self.engine.set_muted(muted)

        self.output_wavfile = output_wavfile
        self.chunk_callback = on_audio_chunk

        if output_wavfile:
            if self._is_engine_mpeg():
                self.wf = open(output_wavfile, 'wb')
            else:
                self.wf = wave.open(output_wavfile, 'wb')
                _, channels, rate = self.engine.get_stream_info()
                self.wf.setnchannels(channels) 
                self.wf.setsampwidth(2)
                self.wf.setframerate(rate)

        # Initialize the generated_text variable
        if reset_generated_text:
            self.generated_text = ""

        try:
            # Start the audio player to handle playback
            self.player.start()
            self.player.on_audio_chunk = self._on_audio_chunk

            # Generate sentences from the characters
            #generate_sentences = s2s.generate_sentences(external_text_iterator, context_size=context_size, minimum_sentence_length=minimum_sentence_length, minimum_first_fragment_length=minimum_first_fragment_length, quick_yield_single_sentence_fragment=fast_sentence_fragment, cleanup_text_links=True, cleanup_text_emojis=True, tokenize_sentences=tokenize_sentences, tokenizer=tokenizer, language=language, log_characters=self.log_characters, sentence_fragment_delimiters=sentence_fragment_delimiters, force_first_fragment_after_words=force_first_fragment_after_words)

            # Create the synthesis chunk generator with the given sentences
            #chunk_generator = self._synthesis_chunk_generator(generate_sentences, buffer_threshold_seconds, log_synthesized_text)

            self.sentence_queue = queue.Queue()

            def synthesize_worker():
                while not abort_event.is_set():
                    sentence = self.sentence_queue.get()

                    synthesis_successful = False
                    if log_synthesized_text:
                        logging.info(f"synthesizing: {sentence}")

                    while not synthesis_successful:
                        try:
                            if abort_event.is_set():
                                break
                            
                            if before_sentence_synthesized:
                                before_sentence_synthesized(sentence)
                            success = self.engine.synthesize(sentence)
                            if success:
                                if on_sentence_synthesized:
                                    on_sentence_synthesized(sentence)
                                synthesis_successful = True
                            else:
                                logging.warning(f"engine {self.engine.engine_name} failed to synthesize sentence \"{sentence}\", unknown error")

                        except Exception as e:
                            logging.warning(f"engine {self.engine.engine_name} failed to synthesize sentence \"{sentence}\" with error: {e}")
                            tb_str = traceback.format_exc()
                            print (f"Traceback: {tb_str}")
                            print (f"Error: {e}")                                

                        if not synthesis_successful:
                            if len(self.engines) == 1:
                                time.sleep(0.2)
                                logging.warning(f"engine {self.engine.engine_name} is the only engine available, can't switch to another engine")
                                break
                            else:
                                logging.warning(f"fallback engine(s) available, switching to next engine")
                                self.engine_index = (self.engine_index + 1) % len(self.engines)

                                self.player.stop()
                                self.load_engine(self.engines[self.engine_index])
                                self.player.start()
                                self.player.on_audio_chunk = self._on_audio_chunk

                    self.sentence_queue.task_done()


            worker_thread = threading.Thread(target=synthesize_worker)
            worker_thread.start()      

            import re
            import emoji
            def _remove_links(text: str) -> str:
                pattern = (
                    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
                    r'[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                )
                return re.sub(pattern, '', text)

            def _remove_emojis(text: str) -> str:
                return emoji.replace_emoji(text, u'')
            pattern = f"([^{re.escape(sentence_fragment_delimiters)}]+[{re.escape(sentence_fragment_delimiters)}]+)"
            # Iterate through the synthesized chunks and feed them to the engine for audio synthesis
            buffer = ""
            for chunk in external_text_iterator:
                buffer += chunk  # Accumulate the chunk into the buffer
                matches = list(re.finditer(pattern, buffer))  
                for match in matches:
                    sentence = _remove_emojis(_remove_links(match.group(1))).strip()
                    if sentence:
                        self.sentence_queue.put(sentence)

                buffer = re.sub(pattern, "", buffer, count=len(matches))  # Remove yielded sentences

            # Signal to the worker to stop
            self.sentence_queue.put(None)
            worker_thread.join()

        except Exception as e:
            logging.warning(f"error in play() with engine {self.engine.engine_name}: {e}")
            tb_str = traceback.format_exc()
            print (f"Traceback: {tb_str}")
            print (f"Error: {e}")

        finally:
            try:
            
                self.player.stop()

                self.abort_events.remove(abort_event)
                self.stream_running = False
                logging.info("stream stop")

                self.output_wavfile = None
                self.chunk_callback = None

            finally:
                if output_wavfile and self.wf:
                    self.wf.close()
                    self.wf = None

        if is_external_call:
            if self.on_audio_stream_stop:
                self.on_audio_stream_stop()

            self.is_playing_flag = False
            self.play_lock.release()

    def check_player(self):
        if(not self.player.playback_active):
            # clear audio buffer before enable player
            with self.engine.queue.mutex:
                self.engine.queue.queue.clear()
            self.player.start()
            self.player.on_audio_chunk = self._on_audio_chunk
    
    def stop(self):
        with self.sentence_queue.mutex:
            self.sentence_queue.queue.clear()
        self.player.immediate_stop.set()
        self.player.stop()

    def is_still_playing(self):
        playing = not self.player.buffer_manager.audio_buffer.empty()
        return playing

