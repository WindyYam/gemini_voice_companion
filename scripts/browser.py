import io
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
from PIL import Image
import os
import platform

class Browser:
    def __init__(self, user_data_dir, profile_directory, temp_dir='temp/'):
        self.chrome_options = webdriver.ChromeOptions()

        self.chrome_options.add_argument(f"user-data-dir={user_data_dir}")
        self.chrome_options.add_argument(f"profile-directory={profile_directory}")
        self.chrome_options.add_argument("disable-features=HardwareMediaKeyHandling")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = None
        self.temp_dir = temp_dir

    def start_driver(self):
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            # Execute script to remove webdriver property
            #self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except exceptions.SessionNotCreatedException as e:
            print(f"Session not created. Retrying after killing Chrome: {e}")
            # Kill Chrome processes
            system = platform.system().lower()
            if system == "windows":
                os.system("taskkill /im chrome.exe /f")
            elif system == "darwin":
                os.system("pkill -a 'Google Chrome'")
            elif system == "linux":
                os.system("pkill chrome")
            else:
                print(f"Unsupported operating system: {system}")
            time.sleep(2)  # Give the system time to clean up

            # 🔁 RETRY driver start
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def navigate_to(self, url):
        if not self.driver:
            self.start_driver()

        try:
            # Navigate to Spotify Web Player
            self.driver.get(url)
        except TimeoutException:
            print("Timed out waiting for page to load or element to be found")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.close_driver()
            raise

    def play_song(self, song_name):
        if not self.driver:
            self.start_driver()

        try:
            # Navigate to Spotify Web Player
            self.driver.get("https://open.spotify.com/search")
            
            # Wait for the search box to be clickable
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='search-input']"))
            )
            
            # Click the search box, enter the song name, and press Enter
            search_box.click()
            search_box.send_keys(song_name)
            #search_box.send_keys(Keys.RETURN)
            
            # Wait for search results and click the first song
            first_result = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='top-result-card']"))
            )
            
            actions = ActionChains(self.driver)
            
            actions.move_to_element(first_result).perform()
            
            button = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_any_elements_located((By.CSS_SELECTOR, "[data-testid='play-button']"))
            )
            
            button[0].click()
            
            
            print(f"Now playing: {song_name}")
            return True

        except TimeoutException:
            print("Timed out waiting for page to load or element to be found")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.close_driver()
            raise
        
        return False
    
    def play_next(self):
        first_result = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='control-button-skip-forward']"))
            )
        first_result.click()
    
    def play_prev(self):
        self.stop_play()
        first_result = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='control-button-skip-back']"))
            )
        first_result.click()
        time.sleep(0.5)
        first_result.click()

    def stop_play(self):
        first_result = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='control-button-playpause']"))
            )
        first_result.click()

    def locate_in_map(self):
        self.driver.get("https://www.google.com/maps")
        
        try:
            # Wait for the geolocation button to be clickable
            location_button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="From your device"]'))
            )
            # Click the geolocation button
            location_button.click()
        except Exception as e:
            pass
        
        time.sleep(2)

    def snapshot(self):
        # Take screenshot and save as PNG in memory
        png_data = self.driver.get_screenshot_as_png()
        
        # Convert PNG to JPG using PIL
        image = Image.open(io.BytesIO(png_data))
        rgb_image = image.convert('RGB')  # Convert to RGB mode for JPG
        # Calculate new dimensions
        width = int(rgb_image.size[0] * 80 / 100)
        height = int(rgb_image.size[1] * 80 / 100)
        
        # Resize the image
        resized_image = rgb_image.resize((width, height), Image.Resampling.LANCZOS)

        filename = self.temp_dir + 'browser_snapshot.jpg'
        resized_image.save(filename, 'JPEG', quality=50)
        return 'file:'+filename
    
    def search_map(self, query):
        self.locate_in_map()
        # Wait for the search box to be present
        search_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        
        # Clear any existing text and enter the query
        search_box.clear()
        search_box.send_keys(query)
        
        # Press Enter to search
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        self.close_driver()

# Example usage
if __name__ == "__main__":
    # Update these paths to match your system
    player = Browser(
        user_data_dir="C:\\MySource\\gemini_voice_companion\\Chrome_User_Data",
        profile_directory="Default"
    )
    
    try:
        player.start_driver()
        success = player.play_song("Hotel California")
        if success:
            print("Song started successfully")
            time.sleep(60)  # Wait for 1 minute
        else:
            print("Failed to play song")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        player.close_driver()