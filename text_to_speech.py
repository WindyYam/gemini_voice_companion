import RealtimeTTS
import os
import wave
import pygame
import langdetect
import numpy as np
class TextToSpeech:
    def __init__(self, voice_path):
        self.DEFAULT_VOICE = 'default'
        self.MIMIC_VOICE = 'mimic'
        self.TRUMP_VOICE = 'trump3'
        self.BIDEN_VOICE = 'biden'
        self.VADER_VOICE = 'vader'
        self.ROBOT_VOICE = 'robot'
        self.FEMALE_VOICE = 'female'
        self.voice_path = voice_path
        self.eng = RealtimeTTS.CoquiEngine(   
            voice=self.DEFAULT_VOICE,
            specific_model='v2.0.3',
            stream_chunk_size=30,
            speed=1.3,
            pretrained=False,
            comma_silence_duration=0.2,
            sentence_silence_duration=0.4,
            default_silence_duration=0.2,
            voices_path=voice_path,
            language='en')
        self.stream = RealtimeTTS.TextToAudioStream(self.eng)
        
        self.vader_breath = pygame.mixer.Sound(f"{voice_path}breathing.mp3")
        self.vader_breath.set_volume(0.1)

    def stop(self):
        self.stream.stop()

    def speak(self, text):
        text = text.replace('*', ' ')
        lang = langdetect.detect(text)
        if('en' in lang):
            lang = 'en'
        else:
            lang = 'zh-cn'
        self.eng.language = lang
        self.stream.feed(text)
        self.stream.play_async(sentence_fragment_delimiters = ".?!;,\n…{[())]}。-？，")

    def switch_user_voice(self, audio):
        self.vader_breath.stop()
        samplerate = 16000
        audio = audio / np.max(np.abs(audio))
        audio = (audio * (2 ** 15 - 1)).astype(np.int16)
        with wave.open(self.voice_path + self.MIMIC_VOICE + ".wav", "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(samplerate)
            f.writeframes(audio)
        mimic_latent = self.voice_path + self.MIMIC_VOICE+'.json'
        if os.path.exists(mimic_latent):
            os.remove(mimic_latent)
        self.eng.set_voice(voice=self.MIMIC_VOICE)

    def switch_default_mode(self):
        self.vader_breath.stop()
        self.eng.set_voice(voice=self.DEFAULT_VOICE)

    def switch_trump_mode(self):
        self.vader_breath.stop()
        self.eng.set_voice(voice=self.TRUMP_VOICE)
    
    def switch_biden_mode(self):
        self.vader_breath.stop()
        self.eng.set_voice(voice=self.BIDEN_VOICE)

    def switch_vader_mode(self):
        self.vader_breath.play(-1)
        self.eng.set_voice(voice=self.VADER_VOICE)
    
    def switch_robot_mode(self):
        self.vader_breath.stop()
        self.eng.set_voice(voice=self.ROBOT_VOICE)

    def switch_female_mode(self):
        self.vader_breath.stop()
        self.eng.set_voice(voice=self.FEMALE_VOICE)