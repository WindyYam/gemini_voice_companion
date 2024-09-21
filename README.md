# Gemini Voice Companion

Gemini Voice Companion is a Python-based voice assistant that offers a wide range of voice-controlled features and capabilities. This project leverages advanced speech recognition and synthesis technologies to create a versatile and interactive voice assistant, all without lifting a finger.

This app is best for users who crave hands-free convenience.  Seamlessly access information and control your devices with just your voice while your hands are on other activities.
Or, if you are the one who like to get eyes a bit of rest while still want to explore the internet world, then this will be the perfect choice for you.

Currently test on Windows only.
My Laptop is nVidia RTX A500 with 4GB VRAM. So in `voice_recognition.py` I am using the small model of whisper. If your PC is rich in VRAM don't hesitate to use the `large-v2` one.

Quick Rundown: https://youtu.be/6eXayNvU6ds
Introduction: https://youtu.be/6NTnIVsfiNM
In-car usage: https://youtu.be/Fer7pBjVmyA
Answer phone call(remote usage): https://youtu.be/kon9clc4MDQ

## Core dependencies

- **Gemini**: The gemini 1.5 flash API
- **Real-time Speech-to-Text (STT)**: Converts spoken words into text in real-time.
- **Real-time Text-to-Speech (TTS)**: Generates natural-sounding speech from text.
- **Fast Whisper**: The multi-language voice to text engine.
- **Coqui xTTS**: The powerful text-to-speech AI engine.
- **Resemblyzer**: For voice similarity and recognition.
- **Selenium**: For Google Chrome autonomous.

## Features

- **Multi-User Recognition**: Distinguish between different users based on voice samples, the extra benefit of this is it will filter out ambient voice or voice like noise.
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
- **Memorize Information**: It can memorize information and save locally, like the user's preference on music, user's family informations. You can explicitly ask it to remember something. The max number of memory items can be adjusted in `config.json`

- For more detail of the API it can use, see the api_list.txt.

## Installation

Make sure your nVidia graphic card is in latest driver.  
Download this repo and put all the content into a folder.  
Then first, install Python 3.12 from https://www.python.org/downloads/ (might work with other version but not tested).  
After that, simply run `setup.bat` to install all dependencies.  

## Usage

1. This is Google Gemini AI which has free tier usage enough for a single user. I'm not gonna use my API key here (unless I'm going to charge you for the excess usage beyond free tier). So you should get the (free) Gemini API key here `https://aistudio.google.com/app/apikey` and either:   
  (recommended) put it in environment variable as GEMINI_API_KEY (please search for detail on how to add environment variable if you are not familiar with). Or  
  (not recommended) do nothing, and `run.bat` will prompt you to enter GEMINI_API_KEY at the beginning every time.
2. Run `manage_user.bat` to add/delete user voice for AI to recognize. You can add multiple users.
3. Use any text editor to open and configure through `config.json` for several parameters. You should modify `user_chrome_data_path` to point to your chrome user profile(Which has Spotify logged in). Typically just replace "Zhenya" with your Google account name, or you can explore in your PC to the same folder structure to find out.
4. Run `run.bat`. Make sure you've GEMINI_API_KEY variable in step 1.
5. When using Chrome related features(such as playing spotify music, navigate webpage), make sure you have Google Chrome installed, Spotify logged in, and Chrome is closed before doing AI Chrome features.

### Modes

- **Free Talk Mode** (Default): The companion listens continuously for commands.
- **Trigger Mode**: Disable free talk mode by saying "Turn off free talk mode". Then use:
  - Tab key or media play/pause key to start speaking
  - Press the same key again to stop and get a response
- **Photo Stream Mode**: By normal, you only upload photo if you ask the AI to take a photo. If you ask Gemini to turn this mode on, every single of your request will be attached with a photo from your camera, captured at the very beginning of your voice, to provide a vision-like experience. Use it wisely, as photos take siginificant amount of tokens and time for AI to process.
- **Sleep Mode**: Tell the companion to go to sleep, it will not react to any voice activity. Only work in Free Talk mode. To wake it up again, use a phrase which contains its name. As usual, longer phrase have better recognition.

### Activating your voice

- For the main users, the voice is already recognized by the setup voice samples in ## Usage 2.
- For a stranger that is not in the list, the default keyword is "Jarvis"(Or AI_NAME if you modified it), or "Nice/Pleased/Good/Ok/xxx to meet you". Use it in a phrase long enough to generate a voice embedding, so the AI can recognize the voice subsequentially without the keyword.
- For stranger, once activated, the companion will recognize the current user until another stranger replace it.
- All strangers other than main users will be considered as stranger using prefix, Gemini will not react to the house commands from them. But will still help with other commands.
- Keep in mind, if you change the recorder device (like from a microphone to a VoIP output), the system might have problem recognize your voice, so you might need to record in ## Usage 2 again with new recorder device(as a new user with different voice sample).
- Or, a backdoor to temporarily setup a master user embedding is to say: "Jarvis(Or AI_NAME if you modified it), ... I'm your master ..." (As long as the phrase have AI_NAME and master together), this will force to update the main embedding no matter who is speaking(A notification sound will play). 

## Customization

- Just remove default.json, and put a default.wav of whatever voice you want the API to be like. Thanks to Coqui xTTS powerful ability to mimic voice.

## Tip

- The Free talk mode does continuous voice sample analysis thus is (slightly more) energy hunger if you are taking your laptop with only battery and in noisy environment. The trigger mode works better in this scenario.
- Sometimes Gemini can be carried away by the context thus forgot to call function for a specific task, you should remind it about the function access like "Have you forgot you had function API access?". I have no good solution to this yet.
- Normally, longer phrase can be easier for the voice recognition.
- The voice break to consider as a speech is short, so try to avoid long break in one speech. If you do want to extend it, try connect with voice like "eh.." instead of blank.
- If you find the voice recognition fails too many times, consider re-record your voice sample or lower the 'voice_similarity_threshold' field in `config.json`
- To remove a user voice sample, simply delete file in sounds/users

## Contributing

## License

## Acknowledgements

---

Note: This project is under active development. Features and usage instructions may change. Please check for updates regularly.