import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from datetime import datetime
from google.generativeai.types import file_types
from google.generativeai.types import RequestOptions
from google.generativeai import protos
import time
class SerializableFile(file_types.File):
    def to_json(self):
        return f'+{self.name}+'
class GeminiAI:
    def __init__(self, model_name, system_instruction):
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        try:
            print("Available models:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(m.name)
            print("Previous uploaded files:")
            lists = genai.list_files()
            for item in lists:
                print(item.name, item.mime_type, item.display_name)
        except Exception as e:
            print(e)
            pass
        
        self.model = self._initialize_model(model_name, system_instruction)

    def _initialize_model(self, model_name, system_instruction):
        print('Loading model', model_name)
        return genai.GenerativeModel(
            model_name=model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
            system_instruction=system_instruction
        )

    def generate_response(self, parts:list):
        response = self.model.generate_content(parts, stream=False, request_options=RequestOptions(timeout=30))
        return response.text

    @staticmethod
    def extract_code(input_string):
        start = input_string.find('```python')
        startlen = 9
        if start == -1:
            # The AI will sometimes try tool_code instead of python
            start =  input_string.find('```tool_code')
            startlen = 12
        end = -1
        if start >= 0:
            start = start + startlen
            end = input_string.find('```', start)
        if start == -1 or end == -1:
            return ''
        return input_string[start:end]

    @staticmethod
    def strip_code(input_string):
        start = input_string.find('```python')
        if start == -1:
            # The AI will sometimes try tool_code instead of python
            start =  input_string.find('```tool_code')
        end = input_string.find('```', start + 9)
        if start == -1 or end == -1:
            return input_string
        return input_string[:start] + input_string[end + 3:]

    def upload_file(self, path, display_name):
        return SerializableFile(genai.upload_file(path=path, display_name=display_name))
    
    def get_file(self, name):
        return SerializableFile(genai.get_file(name))
    
    def wait_file(self, fileD):
        while fileD.state.name == "PROCESSING":
            print('.', end='')
            time.sleep(0.5)
            fileD = genai.get_file(fileD.name)

    def clear_files(self):
        lists = genai.list_files()
        for item in lists:
            print(item.name, item.mime_type, item.display_name)
            genai.delete_file(item)

    def delete_file(self, file : file_types.File):
        genai.delete_file(file)
