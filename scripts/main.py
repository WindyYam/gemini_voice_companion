if __name__ == "__main__":
    import os
    import threading
    import pygame
    import pygame.camera
    import time
    from datetime import datetime, date, timedelta
    import io
    from typing import Literal
    from gemini_ai import GeminiAI, SerializableFile
    from voice_recognition import VoiceRecognition
    from text_to_speech import TextToSpeech
    from extern_api import *
    import sched
    import queue
    import keyboard
    from pathlib import Path
    import sys

    print("Usage: Modify the config.json on parameters, and run: python main.py")
    print("Usage: To use a different config.json, run: python main.py your_config.json")

    SOUNDS_PATH = 'sounds/'
    USER_VOICE_PATH = 'sounds/users'
    TEMP_PATH = 'temp/'
    PHOTO_NAME = 'camera.jpg'
    CONFIG_FILE = 'config.json'
    HISTORY_FILE = 'history.txt'
    MEMORY_FILE = 'memory.txt'

    context = {
        'talk': [],
        'upload_file': None,
        'vision_mode': False,
        'system_message_in_a_row': 0,
        'upload_in_a_row': 0,
        'freetalk': True,
        'sleep': False,
        'memory': [],
        'memory_str': '',
        'vision_mode_camrea_is_screen' : False    # This will work with Discord video call to capture the video screen as the AI's vision, in this case you are on the other end of discord chat holding the phone camera
    }

    pygame.init()
    pygame.camera.init()
    scheduler = sched.scheduler(time.time, time.sleep)
    alarm_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}alarm.mp3")
    code_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}code.mp3")
    code_sound.set_volume(0.2)
    analyze_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}analyze.mp3")
    analyze_sound.set_volume(0.2)
    fail_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}failed.mp3")
    event_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}event.mp3")
    event_sound.set_volume(0.5)
    voice_on_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}sonar.mp3")
    voice_on_sound.set_volume(0.5)
    voice_off_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}confirm.mp3")
    voice_off_sound.set_volume(0.5)
    start_up_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}startup.mp3")
    shutter_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}shutter.mp3")
    recurring_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}recurring.mp3")
    today = str(date.today())
    evt_enter = threading.Event()

    # Create the folder if it doesn't exist
    os.makedirs(TEMP_PATH, exist_ok=True)

    if len(sys.argv) >= 2:
        CONFIG_FILE = sys.argv[1]

    def check_config():
        global config

        # The default values
        MAX_HISTORY = 20 
        MAX_MEMORY = 10
        AI_NAME = 'Jarvis'
        TARGET_CAMERA = 'DroidCam Video'
        USER_CHROME_DATA_PATH = 'C:\\Users\\Zhenya\\AppData\\Local\\Google\\Chrome\\User Data'
        RECORDER_DEVICE = None
        SPEAKER_DEVICE = None

        default_config = {
            'ai_name': AI_NAME,
            'user_chrome_data_path': USER_CHROME_DATA_PATH,
            'max_history' : MAX_HISTORY,
            'max_memory' : MAX_MEMORY,
            'target_camera': TARGET_CAMERA,
            'recorder_device': RECORDER_DEVICE,
            'speaker_device': SPEAKER_DEVICE,
            'voice_similarity_threshold': 0.72,
            'vision_mode_capture_delay' : 1
        }
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print('-----')
            for key in default_config.keys():
                print(key, config[key])
            print('-----')

        except Exception as e:
            print('Load config error! Create new.')

            config = default_config
            print(json.dumps(config, indent = 2))
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)

    check_config()
    set_browser_data_path(config['user_chrome_data_path'])

    instruction = [
        f'''Remember, your name is {config['ai_name']}.
        You are a well educated and professional assistant, have great knowledge on everything. You make most suitable decision for the users. You can raise question to or challenge the user's idea if you think it is not good, but still listen if I insist.
        Keep in mind that there can be multiple users speaking. If it is a main master user, his/her name will be as prefix. If it is a guest, there will be a **Guest:** prefix, attached at the beginning of request. 
        If the request message is with prefix **System:** then it means this message is from the system, not the user. 
        You have the interface on physical world through python code, there are several python function APIs to interact with the physical world. The list of which is in the uploaded text list file. 
        To execute the python code, put the code as python snippet at the end of the response, then any code in the snippet in response will be executed. 
        In that case, if you just want to show me the python code rather than execute it, do not put it in the python snippet form. 
        Be aware, you will not respond to the guest for the requests about operating the house, unless you get authorization from the users that are not with guest prefix. For other kinds of requests, you should help with the guest. 
        To operate with the PC, use the python code execution with necessary library. But do not do potentially harmful operations, like deleting files, unless get the non guest users' permission. 
        Be mindful always check the python function APIs to my instructions if there is a matching API. You are to answer questions in a concise and always humorous way, and talk more casual and use more expressive words that talks more lively, like haha, oh, wow, hmmm.'''
    ]

    def append2log(text:str):
        fname = TEMP_PATH + 'chatlog-' + today + '.txt'
        with open(fname, "a", encoding='utf8') as f:
            f.write(text.strip() + "\n")

    def save_history():
        with open(f'{TEMP_PATH}{HISTORY_FILE}', "w", encoding='utf8') as f:
            f.write(json.dumps(context['talk']))

    def load_history():
        try:
            with open(f'{TEMP_PATH}{HISTORY_FILE}', "r", encoding='utf8') as f:
                text = f.read()
                context['talk'] = json.loads(text)
                for item in context['talk']:
                    for idx, part in enumerate(item['parts']):
                        if part.startswith('+') and part.endswith('+'):
                            # this is a gemini file
                            filename = part[1:-1]
                            item['parts'][idx] = gemini_ai.get_file(filename)

        except Exception as e:
            print(e)
            context['talk'] = []

    def system_message(*values: object,
            sep: str | None = " ",
            end: str | None = "\n",
            flush: Literal[False] = False):
        string_output = io.StringIO()
        print(*values, file=string_output, sep=sep, end=end, flush=flush)
        response = string_output.getvalue().strip()
        if context['vision_mode'] and PHOTO_NAME in response:
            print('In photo stream mode, no need to upload capture photo here.')
            return
        if context['system_message_in_a_row'] < 2 and context['upload_in_a_row'] < 1:
            context['system_message_in_a_row'] += 1
            if response.endswith('.jpg'):
                image_file = string_output.getvalue().strip()
                context['upload_file'] = gemini_ai.upload_file(image_file, display_name='Photo')
                response = 'This is the photo.'
                context['upload_in_a_row'] += 1
            elif response.endswith('.txt'):
                txt_file = response
                context['upload_file'] = gemini_ai.upload_file(txt_file, display_name='Text')
                response = 'This is the content.'
                context['upload_in_a_row'] += 1
            response = f"**System:**{response}"
            mInputQueue.put(response)
            string_output.close()
            analyze_sound.play()
        else:
            print("Too many system message call in a row!")

    def vision_mode(on:bool, type:str):
        if type == 'camera':
            context['vision_mode_camrea_is_screen'] = False
        else:
            context['vision_mode_camrea_is_screen'] = True

        if(on):
            if not context['vision_mode_camrea_is_screen']:
                cam.start()
            context['vision_mode'] = True
        else:
            context['vision_mode'] = False
            cam.stop()
            
    def camera_shot()->str:
        # opening the camera, in case it is not open
        cam.start()
        img = cam.get_image()
        shutter_sound.play()
        photo_path = f"{TEMP_PATH}{PHOTO_NAME}"
        # saving the image 
        pygame.image.save(img, photo_path)
        return photo_path
    
    def screenshot() -> str:
        from PIL import ImageGrab, Image

        # Capture the screenshot
        screenshot = ImageGrab.grab()
        shutter_sound.play()
        if context['vision_mode'] and context['vision_mode_camrea_is_screen']:
            # In this mode, we scale down to half size, as the main purpose of this mode is to get the live video snapshot from discord video chat, which is actually low res
            width, height = screenshot.size

            # Calculate the new dimensions (half of the original)
            new_width = width // 2
            new_height = height // 2

            # Resize the image to half resolution
            screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
        filename = "temp/screenshot.jpg"

        # Save the screenshot as JPG
        screenshot.save(filename, "JPEG")
        return filename
    
    def capture_upload_photo():
        if context['vision_mode_camrea_is_screen']:
            filename = screenshot()
        else:
            filename = camera_shot()

        previous = context['upload_file']
        context['upload_file'] = gemini_ai.upload_file(path=filename,
                            display_name="Photo")
        if previous:
            # A previously unused photo file
            gemini_ai.delete_file(previous)


    def exec_code(code:str):
        try:
            d = dict(locals(), **globals())
            code_sound.play()
            exec(code, d, d)
        except Exception as e:
            fail_sound.play()
            err_msg = f'Code exec exception: {e}'
            print(err_msg)
            system_message(err_msg)

    def event_thread(cam: pygame.camera.Camera):
        clock = pygame.time.Clock()

        while True:
            try:
                clock.tick(10)
                scheduler.run(blocking=False)
            except Exception as e:
                print(e)

    def callback_wrapper(cb, arg=()):
        print('Event')
        event_sound.play()
        cb(*arg)
    
    def recurring_wrapper(interval_sec, cb, arg=()):
        print('Recurring event')
        recurring_sound.play()
        cb(*arg)
        scheduler.enter(interval_sec, 1, recurring_wrapper, argument=(interval_sec, cb, arg))

    def schedule_recurring(interval_sec, cb, arg=()):
        if not type(arg) is tuple:
            arg = (arg,)
        scheduler.enter(interval_sec, 1, recurring_wrapper, argument=(interval_sec, cb, arg))

    def schedule(dt:datetime, cb, arg=()):
        if not type(arg) is tuple:
            arg = (arg,)
        secs = (dt - datetime.now()).total_seconds()
        scheduler.enter(secs, 1, callback_wrapper, argument=(cb, arg))

    def clear_schedule():
        list(map(scheduler.cancel, scheduler.queue))

    def switch_user_voice():
        text_to_speech.switch_user_voice(voice_recognition.recorder.audio)

    def switch_default_mode():
        text_to_speech.switch_default_mode()

    def switch_trump_mode():
        text_to_speech.switch_trump_mode()

    def switch_biden_mode():
        text_to_speech.switch_biden_mode()

    def switch_vader_mode():
        text_to_speech.switch_vader_mode()

    def switch_robot_mode():
        text_to_speech.switch_robot_mode()
    
    def switch_female_mode():
        text_to_speech.switch_female_mode()

    def play_alarm_sound():
        alarm_sound.play(2)
    
    def play_text_voice(text:str):
        text_to_speech.speak(text)

    def freetalk_mode(on:bool):
        previous = context['freetalk']
        if previous == False and on == True:
            context['freetalk'] = on
            # The voice recognition thread might stuck on the event waiting for key input, we cancel that first
            evt_enter.set()
        elif previous == True and on == False:
            # hack to bypass the wait for audio in voice recorder
            voice_recognition.recorder.start()
            voice_recognition.recorder.stop()
            context['freetalk'] = on

    def get_today_conversation() -> str:
        fname = TEMP_PATH + 'chatlog-' + today + '.txt'
        return fname
    
    def start_new_conversation(summary:str):
        start_up_sound.play()
        context['talk'] = []
        context['talk'].append({'role': 'user', 'parts': [f'This is our previous talk summary from your perspective: {summary}']})
        context['talk'].append({'role': 'model', 'parts': ['All right, I will reference that information as part of the context.']})
        clear_schedule()
    
    def go_sleep():
        print('Enter sleep')
        context['sleep'] = True

    def save_memory():
        with open(f'{TEMP_PATH}{MEMORY_FILE}', "w") as file:
            for item in context['memory']:
                file.write(item + "\n")

    def update_memory_str():
        if len(context['memory']) > 0:
            context['memory_str'] = f"You have memories: {",".join(context['memory'])}"
        else:
            context['memory_str'] = ''

    def add_memory(item:str):
        context['memory'].append(item)
        if len(context['memory']) > config['max_memory']:
            context['memory'] = context['memory'][-config['max_memory']:]
        update_memory_str()
        save_memory()

    def load_memory():
        try:
            with open(f'{TEMP_PATH}{MEMORY_FILE}', "r") as file:
                context['memory'] = file.read().splitlines()
        except Exception as e:
            print("Memory load error, skip")
        update_memory_str()

    def clear_memory():
        context['memory'].clear()
        update_memory_str()
        save_memory()

    def main():
        global context, gemini_ai, voice_recognition, text_to_speech, cam, mInputQueue, photo_upload_thread, upload_handle, gemini_ai

        from json import JSONEncoder
        # for gemini file serialization
        def _default(self, obj):
            return getattr(obj.__class__, "to_json", _default.default)(obj)

        _default.default = JSONEncoder().default
        JSONEncoder.default = _default

        mInputQueue = queue.Queue()

        # Initialize camera
        camlist = pygame.camera.list_cameras()
        img_size = (420, 240)
        cam = None
        if camlist:
            if config['target_camera'] in camlist:
                cam = pygame.camera.Camera(config['target_camera'], img_size)
            else:
                cam = pygame.camera.Camera(camlist[0], img_size)

        # Start event thread
        threading.Thread(target=event_thread, args=(cam, )).start()

        talk_header = [
            {'role': 'user', 'parts': [None, 'This is the list of python APIs you can execute. To execute them, put them in python code snippet at the end of your response. Now start a new conversation.', '']},
            {'role': 'model', 'parts': ['''Alright, I'm ready to execute some Python code! Starting a fresh new talk!\n```python\nstart_new_conversation("""We had some fun talks over various topics.""")\n```''']}
        ]

        gemini_ai = GeminiAI(system_instruction=instruction)

        def check_function_file():
            try:
                if not talk_header[0]['parts'][0]:
                    function_file = gemini_ai.upload_file(path="api_list.txt", display_name="Python API")
                    talk_header[0]['parts'][0] = function_file
            except Exception as e:
                print(e)
                text_to_speech.speak('Hmm, looks like some connection issues out there.')

        def start_vision_mode_photo_thread():
            global photo_upload_thread
            photo_upload_thread = threading.Thread(target=capture_upload_photo)
            photo_upload_thread.start()

        def on_record_start():
            global upload_handle
            if not context['freetalk']:
                text_to_speech.stop()
            if context['vision_mode']:
                upload_handle = scheduler.enter(config['vision_mode_capture_delay'], 1, start_vision_mode_photo_thread)

        photo_upload_thread = None
        upload_handle = None
        text_to_speech = TextToSpeech(SOUNDS_PATH, device_name=config['speaker_device'])
        voice_recognition = VoiceRecognition(on_recording_start=on_record_start, device_name=config['recorder_device'])
        voice_recognition.recorder.set_fast_transcribe_on_recording_judger(lambda: not text_to_speech.stream.is_playing())

        def trigger_button(e):
            evt_enter.set()

        def input_thread():
            while True:
                text = input()
                text = f'**Master:**{text}'
                if context['vision_mode']:
                    start_vision_mode_photo_thread()
                mInputQueue.put(text)

        def voice_thread():
            global upload_handle
            new_speaker_recorded = False
            verify_threshold = config['voice_similarity_threshold']
            
            user_lists = []
            for root, _, files in os.walk(USER_VOICE_PATH):
                for file in files:
                    if file.endswith('.wav'):
                        file_path = os.path.join(root, file)
                        user = os.path.splitext(file)[0]
                        
                        # Generate embedding
                        embedding = voice_recognition.generate_embed(Path(file_path))
                        
                        user_lists.append({
                            "user": user,
                            "embedding": embedding
                        })

            if(len(user_lists) == 0):
                print("Warning: No user voice sample registered! Run record_master_wave.py to register a user first!")
                print(f"You can still talk by saying the AI name {config['ai_name']} in your phrase, or 'Nice to meet your'.")

            while True:
                try:
                    text = None
                    temp_text = None
                    if not context['freetalk']:
                        # -179 is the play/pause media key
                        keyboard.on_press_key(-179, trigger_button, suppress=True)
                        keyboard.on_press_key('tab', trigger_button, suppress=True)
                        
                        evt_enter.clear()
                        evt_enter.wait()
                        evt_enter.clear()
                        print("Listening ...")
                            
                        # In case change in the middle
                        if not context['freetalk']:
                            voice_on_sound.play()
                            voice_recognition.start_listen()
                            
                            evt_enter.wait()
                            evt_enter.clear()
                            
                            voice_off_sound.play()

                            temp_text = voice_recognition.stop_listen()
                            if context['vision_mode']:
                                if(upload_handle in scheduler.queue):
                                    # the scheduled upload not fired yet, upload it now
                                    scheduler.cancel(upload_handle)
                                    upload_handle = None
                                    start_vision_mode_photo_thread()
                            
                            voice_embed = voice_recognition.generate_embed(voice_recognition.recorder.audio)
                            closest_similirity = 0
                            closest_user = None
                            for item in user_lists:
                                user_similarity = voice_recognition.verify_speaker(item['embedding'], voice_embed)
                                print(f"{item['user']} similarity:", user_similarity)
                                if user_similarity > closest_similirity:
                                    closest_similirity = user_similarity
                                    closest_user = item['user']

                            if closest_similirity > verify_threshold:
                                text = f'**{closest_user}:**{temp_text}'
                            else:
                                text = f'**Guest:**{temp_text}'

                            keyboard.unhook_all()
                        else:
                            keyboard.unhook_all()

                    else:
                        evt_enter.clear()
                        # only do fast transcribe when text to speech is not playing, so we have more control when to do transcribe(do transcribe and synthesis at the same time can cause low performance)
                        voice_recognition.listen()
                        if context['sleep']:
                            # It is sleeping, we detect if the name appears in the text to exit sleep
                            if not temp_text:
                                temp_text = voice_recognition.transcribe_voice()
                                print('Sleeping:', temp_text)
                            if config['ai_name'] in temp_text:
                                print('Exit sleep')
                                context['sleep'] = False
                        else:
                            # in free talk mode, we verify the speaker
                            voice_embed = voice_recognition.generate_embed(voice_recognition.recorder.audio)

                            closest_similirity = 0
                            closest_user = None
                            for item in user_lists:
                                user_similarity = voice_recognition.verify_speaker(item['embedding'], voice_embed)
                                print(f"{item['user']} similarity:", user_similarity)
                                if user_similarity > closest_similirity:
                                    closest_similirity = user_similarity
                                    closest_user = item['user']

                            if closest_similirity > verify_threshold:
                                if not temp_text:
                                    if context['vision_mode']:
                                        if(upload_handle in scheduler.queue):
                                            # the scheduled upload not fired yet, upload it now
                                            scheduler.cancel(upload_handle)
                                            upload_handle = None
                                            start_vision_mode_photo_thread()
                                    temp_text = voice_recognition.transcribe_voice()
                                text = f'**{closest_user}:**{temp_text}'
                                voice_off_sound.play()
                            else:
                                # If this is the case, ignore the uploading of photo
                                if(upload_handle in scheduler.queue):
                                    # the scheduled upload not fired yet, upload it now
                                    scheduler.cancel(upload_handle)
                                    upload_handle = None
                                # do the AI_NAME match only when it is not talking, as this consumes GPU resource
                                if not text_to_speech.stream.is_playing():
                                    if not temp_text:
                                        temp_text = voice_recognition.transcribe_voice()
                                    print(temp_text)
                                    if (config['ai_name'] in temp_text) or ('to meet you' in temp_text):
                                        print('Update guest embedding')
                                        current_guest_embed = voice_embed
                                        new_speaker_recorded = True
                                        text = f'**Guest:**{temp_text}'
                                        voice_off_sound.play()

                                if not text and new_speaker_recorded:
                                    guest_similarity = voice_recognition.verify_speaker(current_guest_embed, voice_embed)
                                    print('guest similarity:', guest_similarity)
                                    if guest_similarity > verify_threshold:
                                        if not temp_text:
                                            temp_text = voice_recognition.transcribe_voice()
                                        text = f'**Guest:**{temp_text}'
                                        voice_off_sound.play()
                    if text:
                        # backdoor for updating main embedding
                        if config['ai_name'] in text and 'master' in temp_text:
                            print('Update master embedding')
                            item = {
                                "user": 'Master',
                                "embedding": voice_embed
                            }

                            text = f'**{item['user']}:**{temp_text}'
                            
                            master_exists = False
                            for item in user_lists:
                                if item['user'] == 'Master':
                                    item['embedding'] = voice_embed
                                    master_exists = True
                                    break
                            
                            if not master_exists:
                                user_lists.append({'user': 'Master', 'embedding': voice_embed})
                            # sound
                            print('\a')
                        mInputQueue.put(text)
                except Exception as e:
                    print(e)

        load_history()
        load_memory()

        threading.Thread(target=input_thread).start()
        threading.Thread(target=voice_thread).start()
        
        # Main loop
        start_up_sound.play()
        text_to_speech.speak(f"{config['ai_name']}, online. How can I help you?")
        append2log('==================New=====================')
        check_function_file()
        while True:
            try:
                # only fetch the latest text msg
                if not mInputQueue.empty():
                    while(not mInputQueue.empty()):
                        text = mInputQueue.get()
                else:
                    text = mInputQueue.get()
                if text == '':
                    continue

                check_function_file()

                if photo_upload_thread:
                    photo_upload_thread.join()
                    photo_upload_thread = None
                parts = []
                if context['upload_file']:
                    parts.append(context['upload_file'])
                    context['upload_file'] = None
                parts.append(text)
                timestamp = datetime.now().strftime("%H:%M:%S")
                parts.append(f'**System:**{timestamp}')

                talk_header[0]['parts'][2] = context['memory_str']
                temp = talk_header + context['talk']
                temp.append({'role': 'user', 'parts': parts})
                print(f"You: {text}, {timestamp}")

                # Process user's request
                try:
                    response = gemini_ai.generate_response(temp)
                except Exception as e:
                    print(e)
                    text_to_speech.speak("Well, looks like I can't get a response from the server.")
                    continue
                print(f"AI: {response}")
                
                pythoncode = gemini_ai.extract_code(response)
                voice_text = gemini_ai.strip_code(response).strip()
                if voice_text != '':
                    text_to_speech.stop()
                # Update context
                context['talk'].append({'role': 'user', 'parts': parts})
                context['talk'].append({'role': 'model', 'parts': [response]})
                if len(context['talk']) > config['max_history']:
                    context['talk'] = context['talk'][-config['max_history']:]
                # Handle any code execution from the response
                # sometimes the AI generate code with comment only, strip this comment line to avoid trigger code sound effect
                def remove_comment_lines(s):
                    return "\n".join([line for line in s.split('\n') if not line.strip().startswith('#')])
                pythoncode = remove_comment_lines(pythoncode).strip()
                thread = None
                if(pythoncode != ''):
                    print(f'code: {pythoncode}')
                    thread = threading.Thread(target=exec_code, args=(pythoncode,))
                    # Start the thread
                    thread.start()
                else:
                    # no code this round, clear some flags
                    context['system_message_in_a_row'] = 0
                    context['upload_in_a_row'] = 0
                # Speak the response
                if voice_text != '':
                    text_to_speech.speak(voice_text)
                append2log(f"You: {parts}")
                append2log(f"AI: {response}")
                save_history()
                if thread:
                    thread.join()
                
                # conserve energy
                if not context['vision_mode']:
                    cam.stop()

            except Exception as e:
                print(e)
                print('\a')
                continue
    main()