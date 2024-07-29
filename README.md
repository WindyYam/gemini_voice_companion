# Gemini Voice Companion

Gemini Voice Companion is a Python-based voice assistant that offers a wide range of voice-controlled features and capabilities. This project leverages advanced speech recognition and synthesis technologies to create a versatile and interactive voice assistant, all without lifting a finger.

This app is best for users who crave hands-free convenience.  Seamlessly access information and control your devices with just your voice while your hands are on other activities.
Or, if you are the one who like to get eyes a bit of rest while still want to explore the internet world, then this will be the perfect choice for you.

Currently test on Windows only.
My Laptop is nVidia RTX A500 with 4GB VRAM. So in `voice_recognition.py` I am using the small model of whisper. If your PC is rich in VRAM don't hesitate to use the `large-v2` one.

Youtube Introduction: https://www.youtube.com/watch?v=HJQ7SzW7oSU&t=444s

## Core dependencies

- **Gemini**: The gemini 1.5 flash API
- **Real-time Speech-to-Text (STT)**: Converts spoken words into text in real-time.
- **Real-time Text-to-Speech (TTS)**: Generates natural-sounding speech from text.
- **Fast Whisper**: The multi-language voice to text engine.
- **Coqui xTTS**: The powerful text-to-speech AI engine.
- **Resemblyzer**: For voice similarity and recognition.
- **Selenium**: For Google Chrome autonomous.

## Features

- **Multi-User Recognition**: Distinguish between different users based on voice samples.
- **Voice Switching**: Change the companion's voice on command (e.g., mimic user's voice, switch to Darth Vader's voice. See `api_list.txt` for more.).
- **House Managing**: Smart house like operation through voice command. It is simulated by pygame as a simple GUI. You can open door, turn on light, etc.
- **Reminder Schedule**: Schedule a voice reminder or an alarm at specific time.
- **Information Lookup**: Search for information on the internet.
- **Navigate Browser**: Use together with information lookup, you can navigate to the search result webpage, e.g. news, youtube page, Wikipeda. 
- **Summarize Webpage**: Use together with information lookup, you can ask the AI to get the content from static webpage and summarize it.
- **Weather Updates**: Get current weather conditions and forecasts.
- **News Updates**: Fetch and read out the latest news.
- **Spotify Integration**: Play and control music on Spotify.
- **PC Keyboard Control**: Type content onto your PC using voice commands.
- **Take Picture**: Either take a photo from the camera, or take a screenshot of your PC, which will then get uploaded to gemini. For better experience, recommend to download ```DroidCam https://droidcam.app/``` to turn your mobile phone into a camera.
- **Write Diary Entry**: It can upload the conversation history today and then you can ask the AI to write diary entry based on that. You will have to explicitly ask the AI to access the history for reference(it is recommended to start a new conversation for AI after that as the history file can be huge which slows down the subsequential requests).
- For more detail of the API it can use, see the api_list.txt.

## Installation

First, you should create a virtual env on this folder for your convience.
Then, install cuda 12.1 package with this command(make sure your nVidia driver is the latest): 

```./.venv/Scripts/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121```

Then, run the command to install all the other dependencies:
```./.venv/Scripts/pip install -r requirements.txt```

## Usage

1. Get the Gemini API key and put it in environment variable as GEMINI_API_KEY (or you can simply replace it in the source code `gemini_ai.py`, not recommended)
2. Place your voice sample (at least 5 seconds long) as `master.wav` in the sounds directory.
or, run `./.venv/Scripts/python record_master_wav.py` to record a 30 sec voice sample of yourself.
3. Configure through `config.json` for several parameters. You should modify `user_chrome_data_path` to point to your user profile(Which has Spotify logged in)
4. Run the main script `./.venv/Scripts/python main.py`, or simply double click `run.bat`

### Modes

- **Free Talk Mode** (Default): The companion listens continuously for commands.
- **Trigger Mode**: Disable free talk mode by saying "Turn off free talk mode". Then use:
  - Tab key or media play/pause key to start speaking
  - Press the same key again to stop and get a response
- **Photo Stream Mode**: By normal, you only upload photo if you ask the AI to take a photo. If you ask Gemini to turn this mode on, every single of your request will be attached with a photo from your camera, captured at the very beginning of your voice, to provide a vision-like experience. Use it wisely, as photos take siginificant amount of tokens and time for AI to process.

### Activating your voice

- For the master user, the voice is already recognized by the voice sample.
- For others, the default keyword is "Jarvis"(Or AI_NAME if you modified it). Use it in a phrase long enough to generate a voice embedding, so the AI can recognize the voice subsequentially without the keyword.
- Once activated, the companion will recognize the current user until another user activates it.
- All other users other than master will be considered as stranger, Gemini will not react to the house commands from them. But will still help with other commands.

## Customization

- Just remove default.json, and put a default.wav of whatever voice you want the API to be like. Thanks to Coqui xTTS powerful ability to mimic voice.

## Tip

- The Free talk mode does continuous voice sample analysis thus is (slightly more) energy hunger if you are taking your laptop with only battery and in noisy environment. The trigger mode works better in this scenario.
- Sometimes Gemini can be carried away by the context thus forgot to call function for a specific task, you should remind it about the function access like "Have you forgot you had function API access?". I have no good solution to this yet.

## Contributing

## License

## Acknowledgements

---

Note: This project is under active development. Features and usage instructions may change. Please check for updates regularly.