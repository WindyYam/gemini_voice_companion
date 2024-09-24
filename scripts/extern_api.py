# This file contains python APIs to be used in code snippet for execution

import requests
from bs4 import BeautifulSoup
import json
import test_game

player = None

house = {
    'light_state' : False,
    'door_state' : False,
    'air_conditioner_set_temp' : 22,
    'fan_speed' : 0,
    }

# control light on and off
def light(on:bool):
    house['light_state'] = on
    test_game.set_light(on)
    test_game.refresh()
    print(f'light is {on}')

# control door open and close
def door(open:bool):
    house['door_state'] = open
    test_game.set_door(open)
    test_game.refresh()
    print(f'door is {open}')

# control the air conditioner in celsius degree
def setAirConditioner(temp:float):
    house['air_conditioner_set_temp'] = temp
    test_game.set_ac_temp(temp)
    test_game.refresh()
    print(f'set air conditioner to {temp}')

# set fan speed, range from 0 to 100
def setFanSpeed(speed:int):
    house['fan_speed'] = speed
    test_game.set_target_fan_speed(speed)
    test_game.refresh()
    print(f'set fan speed {speed}')

# check for all house smart appliance status
def getHouseStatus()->str:
    test_game.refresh()
    return json.dumps(house)

# get the current city name
def getCity()->str:
    res = requests.get('https://ipinfo.io/')
    data = res.json()
    citydata = data['city']
    return(citydata)

# online search for any information you don't know from bing search engine 
def bingSearch(query:str)->str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    }
    url = f'https://bing.com/search?q={query.replace(" ","+")}'

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    search_results = []

    for result in soup.find_all('li', class_='b_algo'):
        anchor = result.find('a')
        title = anchor.text
        url = result.find('a')['href']
        desc = result.find('p') or anchor
        description= desc.text
        
        search_results.append({
            'title': title,
            'description': description,
            'url': url
        })
    
    return json.dumps(search_results)

# get webpage context in plain text
def get_webpage_text(url):
    # Default headers with a common user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    }

    try:
        # Fetch the webpage content with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Try to detect the encoding, fallback to UTF-8 if not detected
        if response.encoding is None:
            response.encoding = 'utf-8'

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove all script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    except requests.RequestException as e:
        return f"An error occurred: {e}"

def set_browser_data_path(path):
    global USER_CHROME_DATA_PATH
    USER_CHROME_DATA_PATH = path

def check_browser():
    global player
    if not player:
        try:
            from browser import Browser
        
            # spotify player
            player = Browser(
                user_data_dir=USER_CHROME_DATA_PATH,
                profile_directory="Default"
            )
            player.start_driver()
        except Exception as e:
            # No chrome or the library selemium is not installed
            print(e)

def navigate_to(url:str):
    check_browser()
    player.navigate_to(url)

def play_music(name:str):
    check_browser()
    player.play_song(name)

def stop_music():
    global player
    try:
        player.stop_play()
        #player.close_driver()
    finally:
        #player = None
        pass

def play_next_music():
    try:
        player.play_next()
    finally:
        pass

def play_prev_music():
    try:
        player.play_prev()
    finally:
        pass

def keyboard_type_text(text: str):
    import keyboard
    keyboard.write(text)

def get_clipboard_text() -> str:
    import pyperclip
    s = pyperclip.paste()
    return s

if __name__ == "__main__":
    ret = bingSearch('News update')
    print(ret)