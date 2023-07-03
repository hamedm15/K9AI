import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
from movement.quadruped import Quadruped
import time
from collections import deque
from imutils.video import VideoStream
import numpy as np
import cv2
import threading
import imutils

forwards = False
backwards = False
tracking_value  = False

# Initialize the joystick module
pygame.joystick.init()

# Check for connected gamepad controllers
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("No gamepad found.")
    #quit()

# Select the first gamepad controller
gamepad = pygame.joystick.Joystick(0)
gamepad.init()
print("Gamepad connected:", gamepad.get_name())

# Store the previous state of the left joystick axis
prev_buttons = [False] * gamepad.get_numbuttons()
button_names = {
    0: "A",
    1: "B",
    2: "X",
    3: "Y",
    4: "L_Option",
    5: "Guide",
    6: "R_Option",
    7: "L_Stick",
    8: "R_Stick",
    9: "LB",
    10: "RB",
    11: "UP",
    12: "DOWN",
    13: "LEFT",
    14: "RIGHT"
}

# Variables for tracker
greenLower = (29, 86, 6)
greenUpper = (64, 255, 255)
pts = deque(maxlen=64)
tracking_value = True
# define the screen segments
screen_width = 600
first_third = screen_width // 3
last_third = first_third * 2

current_dir = "None"

def draw_green_bars(frame, center):
    global current_dir
    if center is not None:
        ball_x = center[0]

        if ball_x < first_third:
            # Draw green bar for the first third
            cv2.rectangle(frame, (0, 0), (first_third, 10), (0, 255, 0), cv2.FILLED)
            current_dir = "Left"
        elif ball_x > last_third:
            # Draw green bar for the last third
            cv2.rectangle(frame, (last_third, 0), (screen_width, 10), (0, 255, 0), cv2.FILLED)
            current_dir = "Right"
        else:
            # Draw green bar for the middle third
            cv2.rectangle(frame, (first_third, 0), (last_third, 10), (0, 255, 0), cv2.FILLED)
            current_dir = "Forward"
    else:
        current_dir = "None"
def draw_size(frame, radius, x, y):
    cv2.putText(frame, f"Size: {radius}", (int(x - radius), int(y - radius - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

def process_frame(frame, headless_mode=False):
    # resize the frame, blur it, and convert it to the HSV
    # color space
    frame = imutils.resize(frame, width=screen_width)
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    
    mask = cv2.inRange(hsv, greenLower, greenUpper)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    center = None

    # only proceed if at least one contour was found
    if len(cnts) > 0:
        # find the largest contour in the mask
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

        # only proceed if the radius meets a minimum size
        if radius > 10 and not headless_mode:
            draw_size(frame, radius, x, y)
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
            cv2.circle(frame, center, 5, (0, 0, 255), -1)
    
    draw_green_bars(frame, center)
    
    # update the points queue
    pts.appendleft(center)

    # loop over the set of tracked points
    for i in range(1, len(pts)):
        if pts[i - 1] is None or pts[i] is None:
            continue
        thickness = int(np.sqrt(64 / float(i + 1)) * 2.5)
        cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

    # show the frame if not in headless mode
    if not headless_mode:
        cv2.imshow("Frame", frame)

def start_tracking(headless_mode=True):
    # initialize the video stream
    vs = VideoStream(src=0).start()
    time.sleep(1.0)
    
    if not headless_mode:
        # create a named window to display the video
        cv2.namedWindow("Frame")

    # keep looping
    while True:
        frame = vs.read()
        process_frame(frame, headless_mode)
        if tracking_value == False:
            break
    # stop the camera video stream
    vs.stop()
    cv2.destroyAllWindows()

def controller(momentum, sit, accel=0.7, bound=5):
    if tracking_value == False:
        begin = False
        forwards = False
        backwards = False
        head = ""
        pygame.event.pump()
        buttons = [gamepad.get_button(i) for i in range(gamepad.get_numbuttons())]
        for i, button in enumerate(buttons):
            if button and not prev_buttons[i]:
                print("Button [P]:", button_names[i], i)
                if i == 1:
                    sit.value = not sit.value  # Toggle the sitting value
                    print(sit.value)
            if not button and prev_buttons[i]:
                print("Button [R]:", button_names[i], i)
            prev_buttons[i] = button

        axes = [gamepad.get_axis(i) for i in range(gamepad.get_numaxes())]
        for i, axis in enumerate(axes):
            if i == 0:  # Check if it's the left joystick axis
                if axis > 0.2:
                    direction = "Right"
                    momentum[1] = min(momentum[1] + accel, bound)
                    forwards = True
                elif axis < -0.2:
                    direction = "Left"
                    momentum[1] = max(momentum[1] - accel, -bound)
                    forwards = True
                else:
                    direction = "Center"
            # Right Joystick
            if i == 2:
                if axis > 0.2:
                    head = "R"
                elif axis < -0.2:
                    head = "L"
            if i == 3:
                if axis > 0.2:
                    head = "D"
                elif axis < -0.2:
                    head = "U"
 
            elif i == 4 or i == 5:
                if axis > 0.9:
                    if i == 4:
                        momentum[0] = min(momentum[0] + accel, bound)
                        forwards = True
                    else:
                        momentum[0] = max(momentum[0] - accel, -bound)
                        backwards = True

    if tracking_value == True:
        if not begin:
            thread = threading.Thread(target=start_tracking)
            thread.start()
            begin = True
        if current_dir == "Left":
            momentum[1] = max(momentum[1] - accel, -bound)
            forwards = True
        elif current_dir == "Right":
            momentum[1] = min(momentum[1] + accel, bound)
            forwards = True
        elif current_dir == "Forward":
            momentum[0] = min(momentum[0] + accel, bound)
            forwards = True

    pygame.time.wait(10)
    return momentum, forwards, backwards, sit, head

def command_sit(sit):
    sit.value = True
    print("Sit: ", sit.value)
    
def command_stand(sit):
    sit.value = False
    print("Sit: ", sit.value)

def command_track(sit):
    sit.value = True

def command_stop_track(sit):
    sit.value = False
