import pygame
import math
import time
import threading
# Initialize Pygame
pygame.init()

# Set up the display
width, height = 800, 600

# Colors
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
BROWN = (139, 69, 19)
DARK_BROWN = (60, 40, 20)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Door properties
door_width = 200
door_height = 300
door_x = (width - door_width) // 2
door_y = (height - door_height) - 20
max_angle = 180

# Animation properties
angle = 0
animation_speed = 1

# Light properties
light_on = False
light_radius = 30
light_x = width / 2
light_y = 100

# Fan properties
fan_center = (150, 150)
fan_radius = 100
fan_angle = 0
fan_speed = 0  # Current speed
target_fan_speed = 0  # Target speed
fan_acceleration = 0.5  # Speed change per frame

# Air conditioner properties
ac_width, ac_height = 100, 60
ac_x, ac_y = width / 2 - ac_width / 2, 200
ac_temp = 22  # Starting temperature in Celsius
target_ac_temp = 22

# Clock properties
clock_center = (width - 100, 100)
clock_radius = 50

def draw_door(angle):
    # Draw the door frame
    pygame.draw.rect(screen, DARK_BROWN, (door_x - 10, door_y - 10, door_width + 20, door_height + 10))

    # Calculate the visible part of the door
    visible_width = int(door_width * math.cos(math.radians(angle)))

    # Draw the door
    if visible_width > 0:
        door_rect = pygame.Rect(door_x, door_y, visible_width, door_height)
    else:
        door_rect = pygame.Rect(door_x+visible_width, door_y, -visible_width, door_height)
    pygame.draw.rect(screen, BROWN, door_rect)

    # Draw the edge of the door
    edge_x = door_x + visible_width - 1
    pygame.draw.line(screen, DARK_BROWN, (edge_x, door_y), (edge_x, door_y + door_height), 2)

    # Draw door handle
    handle_x = door_x + visible_width - 20
    handle_y = door_y + door_height // 2
    if visible_width > 20:
        pygame.draw.circle(screen, DARK_BROWN, (handle_x, handle_y), 5)

def set_door(on: bool):
    global is_opening
    is_opening = on

def open_door():
    global angle
    if angle < max_angle:
        angle += animation_speed
    return angle >= max_angle

def close_door():
    global angle
    if angle > 0:
        angle -= animation_speed
    return angle <= 0

def draw_light():
    if light_on:
        pygame.draw.circle(screen, YELLOW, (light_x, light_y), light_radius)
    else:
        pygame.draw.circle(screen, DARK_GRAY, (light_x, light_y), light_radius)
    # Draw light outline
    pygame.draw.circle(screen, LIGHT_GRAY, (light_x, light_y), light_radius, 2)

def set_light(on:bool):
    global light_on
    light_on = on

def draw_fan():
    global fan_angle
    fan_angle += fan_speed / 5  # Adjust fan rotation speed
    
    # Draw fan base
    #pygame.draw.circle(screen, DARK_GRAY, fan_center, fan_radius + 5)
    
    # Draw fan blades
    for i in range(3):
        angle = math.radians(fan_angle + i * 120)
        end_x = fan_center[0] + fan_radius * math.cos(angle)
        end_y = fan_center[1] + fan_radius * math.sin(angle)
        pygame.draw.line(screen, BLACK, fan_center, (end_x, end_y), 5)
    
    # Draw fan center
    pygame.draw.circle(screen, BLACK, fan_center, 10)

def set_target_fan_speed(speed):
    global target_fan_speed
    target_fan_speed = max(0, min(100, speed))  # Ensure speed is between 0 and 100

def update_fan_speed():
    global fan_speed
    if fan_speed < target_fan_speed:
        fan_speed = min(fan_speed + fan_acceleration, target_fan_speed)
    elif fan_speed > target_fan_speed:
        fan_speed = max(fan_speed - fan_acceleration, target_fan_speed)

def draw_ac():
    pygame.draw.rect(screen, LIGHT_GRAY, (ac_x, ac_y, ac_width, ac_height))
    pygame.draw.rect(screen, DARK_GRAY, (ac_x, ac_y, ac_width, ac_height), 2)
    
    # Draw temperature display
    font = pygame.font.Font(None, 32)
    temp_text = font.render(f"{ac_temp}°C", True, BLUE)
    text_rect = temp_text.get_rect(center=(ac_x + ac_width // 2, ac_y + ac_height // 2))
    screen.blit(temp_text, text_rect)

def set_ac_temp(temp):
    global target_ac_temp
    target_ac_temp = max(16, min(30, temp))  # Limit temperature between 16°C and 30°C

def update_ac_temp():
    global ac_temp
    if ac_temp < target_ac_temp:
        ac_temp = min(ac_temp + 0.1, target_ac_temp)
    elif ac_temp > target_ac_temp:
        ac_temp = max(ac_temp - 0.1, target_ac_temp)
    ac_temp = round(ac_temp, 1)  # Round to one decimal place

def draw_clock():
    # Draw clock face
    pygame.draw.circle(screen, WHITE, clock_center, clock_radius)
    pygame.draw.circle(screen, BLACK, clock_center, clock_radius, 2)

    # Draw hour marks
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        start_pos = (clock_center[0] + (clock_radius - 10) * math.cos(angle),
                     clock_center[1] + (clock_radius - 10) * math.sin(angle))
        end_pos = (clock_center[0] + clock_radius * math.cos(angle),
                   clock_center[1] + clock_radius * math.sin(angle))
        pygame.draw.line(screen, BLACK, start_pos, end_pos, 2)

    # Get current time
    current_time = time.localtime()
    hours, minutes, seconds = current_time.tm_hour, current_time.tm_min, current_time.tm_sec

    # Draw hour hand
    hour_angle = math.radians((hours % 12 + minutes / 60) * 30 - 90)
    hour_hand_length = clock_radius * 0.5
    hour_hand = (clock_center[0] + hour_hand_length * math.cos(hour_angle),
                 clock_center[1] + hour_hand_length * math.sin(hour_angle))
    pygame.draw.line(screen, BLACK, clock_center, hour_hand, 4)

    # Draw minute hand
    minute_angle = math.radians(minutes * 6 - 90)
    minute_hand_length = clock_radius * 0.7
    minute_hand = (clock_center[0] + minute_hand_length * math.cos(minute_angle),
                   clock_center[1] + minute_hand_length * math.sin(minute_angle))
    pygame.draw.line(screen, BLACK, clock_center, minute_hand, 3)

    # Draw second hand
    second_angle = math.radians(seconds * 6 - 90)
    second_hand_length = clock_radius * 0.8
    second_hand = (clock_center[0] + second_hand_length * math.cos(second_angle),
                   clock_center[1] + second_hand_length * math.sin(second_angle))
    pygame.draw.line(screen, RED, clock_center, second_hand, 2)

    # Draw center dot
    pygame.draw.circle(screen, BLACK, clock_center, 5)

# Game loop
running = False
clock = pygame.time.Clock()
is_opening = False

def game_loop():
    global running, screen
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Door, Light, and Fan Animation")
    while time.time() - start_time < 60:
        for event in pygame.event.get():
            pass
            # if event.type == pygame.QUIT:
            #     running = False
            # elif event.type == pygame.KEYDOWN:
            #     if event.key == pygame.K_SPACE:
            #         is_opening = not is_opening
            #     elif event.key == pygame.K_l:
            #         set_light(not light_on)
            #     elif event.key == pygame.K_UP:
            #         set_target_fan_speed(fan_speed + 10)
            #     elif event.key == pygame.K_DOWN:
            #         set_target_fan_speed(fan_speed - 10)

        # Update fan speed
        update_fan_speed()
        update_ac_temp()

        # Set the background based on light state
        if light_on:
            screen.fill(LIGHT_GRAY)
        else:
            screen.fill(DARK_GRAY)

        # Perform door animation
        if is_opening:
            open_door()
        else:
            close_door()

        # Draw the scene
        draw_door(angle)
        draw_light()
        draw_fan()
        draw_ac()
        draw_clock()

        # Display fan speed
        font = pygame.font.Font(None, 36)
        speed_text = font.render(f"Fan Speed: {fan_speed}", True, BLACK)
        screen.blit(speed_text, (10, 10))

        # Update the display
        pygame.display.flip()

        # Control the frame rate
        clock.tick(60)
    pygame.display.quit()
    running = False

def refresh():
    global start_time, running
    start_time = time.time()
    if not running:
        print("Start GUI")
        running = True
        threading.Thread(target=game_loop).start()

if __name__ == "__main__":
    refresh()
    while True:
        time.sleep(0.1)
        pass