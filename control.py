import os
from time import sleep
from pynput.mouse import Button, Controller, Listener
import socket

BND_RFRSH_CNT = 200

# touch event types
TOUCH_UP = 0
TOUCH_DOWN = 1
TOUCH_MOVE = 2
SET_SCREEN_SIZE = 9

CLICK_COORDS = (0, 0)
CAN_MOVE = False
SCROLLING = False

def run_cmd(cmd):
	return os.popen(cmd).read()

def update_bounds():

	global BOUNDS

	cmd = "osascript -e 'tell application \"QuickTime Player\" to get the bounds of the front window'"

	bounds = run_cmd(cmd)

	BOUNDS = tuple(int(i) for i in bounds.split(", "))

BOUNDS = ()
update_bounds()

def get_bounds():

	return BOUNDS

def set_bounds(x1, y1, x2, y2):

	cmd = "osascript -e 'tell application \"QuickTime Player\" to set the bounds of the front window to \{{0}, {1}, {2}, {3}\}'".format((x1, y1, x2, y2))

	return run_cmd(cmd)

def is_qt_focused():

	return "true" in run_cmd("osascript -e 'frontmost of application \"QuickTime Player\"'")

def focus_qt():

	return run_cmd("osascript -e 'tell application \"QuickTime Player\" to activate'")

def select_camera(cam_name):

	# might need to add sleep later on

	return run_cmd("""osascript -e '
		tell application "System Events" to tell process "QuickTime Player"
			#To open dialog to show available cameras
			click button 3 of window 1
			#To select our device
			click menu item "{0}" of menu 1 of button 3 of window 1
			activate
		end tell'""".format(cam_name))

def setup_qt(device_name):

	# run_cmd("open -a 'QuickTime Player'")

	script = """tell application "QuickTime Player"
	    activate
		new movie recording
		end tell
		"""

	run_cmd("osascript -e '{0}'".format(script))

	select_camera(device_name)

	# focus_qt()

def inWindow(x, y):

    x1, y1, x2, y2 = get_bounds()

    return (x1 < x and x < x2) and (y1 < y and y < y2)

def on_move(device, x, y):

	# print(CAN_MOVE, CLICK_COORDS, (x, y))

	if CAN_MOVE and CLICK_COORDS != (x, y):

		device.send(("101"+formatSocketData(TOUCH_MOVE, 7, *rel_mouse_pos(x, y))).encode())

def on_click(device, x, y, button, pressed):

	global CAN_MOVE, CLICK_COORDS

	if not inWindow(x, y):
		# Stop listener
		print("Stopping Listener")
		return False

	# if is_qt_focused():

		# print('{0} at {1}'.format(
		# 	'Pressed' if pressed else 'Released',
		# 	rel_mouse_pos(x, y)))

	if pressed:
		CLICK_COORDS = (x, y)
		CAN_MOVE = True
	else:
		CAN_MOVE = False
		tap(device, *rel_mouse_pos(x, y))

def on_scroll(device, x, y, dx, dy):

	global SCROLLING

	if inWindow(x, y) and dy != 0 and not SCROLLING:

		SCROLLING = True

		f5_y = y-dy

		device.send(("101" + formatSocketData(TOUCH_DOWN, 6, x+20, y)).encode())
		device.send(("101" + formatSocketData(TOUCH_DOWN, 5, x-20, f5_y)).encode())

		sleep(0.001)

		while f5_y < y+100:

			f5_y += 5

			device.send(("101" + formatSocketData(TOUCH_MOVE, 5, x-20, f5_y)).encode())

			sleep(0.001)

		device.send(("101" + formatSocketData(TOUCH_UP, 5, x-20, f5_y)).encode())
		device.send(("101" + formatSocketData(TOUCH_UP, 6, x+20, y)).encode())

		SCROLLING = False

def rel_mouse_pos(x, y):

	bounds = get_bounds()

	unscaled_rel_mouse = (
					x - bounds[0],
					y - bounds[1]
				)

	window_height = max(abs(bounds[2]-bounds[0]), abs(bounds[3]-bounds[1]))

	screen_height = 736*3

	scale_factor =  screen_height / window_height

	if is_portrait():

		rel_mouse = tuple(i*scale_factor for i in unscaled_rel_mouse)

	else:

		rel_mouse = (unscaled_rel_mouse[1]*scale_factor, screen_height - unscaled_rel_mouse[0]*scale_factor)

	return rel_mouse

def is_portrait():

	bounds = get_bounds()

	return abs(bounds[2]-bounds[0]) < abs(bounds[3]-bounds[1])

# you can copy and paste these methods to your code
def formatSocketData(type, index, x, y):
    return '{}{:02d}{:05d}{:05d}'.format(type, index, int(x*10), int(y*10))


def performTouch(socket, event_array):
    """Perform touch events

    Perform touch events in event_array. event_array should be an array containing dictionaries of touch events. The format of the dictionaries: {"type": touch type, "index": finger index, "x": x coordinate, "y": y coordinate}

    Args:
        socket: socket instance that connects to ZJXTouchSimulation tweak
        event_array: array of touch event dictionaries

    Returns:
        None

    Demo usage:
        performTouch(s, [{"type": 1, "index": 3, "x": 100, "y": 200}]) # touch down at (100, 300) with finger "3"
    """
    event_data = ''
    for touch_event in event_array:
        event_data += formatSocketData(touch_event['type'], touch_event['index'], touch_event['x'], touch_event['y'])
    socket.send('10{}{}'.format(len(event_array), event_data))

def switchAppToForeground(socket, app_identifier):
    """Bring application to foregound

    Args:
        socket: socket instance that connects to ZJXTouchSimulation tweak
        app_identifier: iOS application bundle identifier.

    Returns:
        None

    Demo Usage:
        switchAppToForeground(s, "com.apple.springboard") # returns to home screen
    """
    socket.send('11{}'.format(app_identifier).encode())

def showAlertBox(socket, title, content):
    """Show a system wide alert box

    Args:
        socket: socket instance that connects to ZJXTouchSimulation tweak
        title: title of the alert box
        content: content of the alert box

    Returns:
        None

    Demo Usage:
        showAlertBox(s, "Low Battery", "10% of battery remaining") # just a joke
    """
    socket.send('12{};;{}'.format(title, content).encode())

def executeCommand(socket, command_to_run):
    """Execute shell command with root privileges

    Args:
        socket: socket instance that connects to ZJXTouchSimulation tweak
        command_to_run: command that you want to execute

    Returns:
        None

    Demo Usage:
        executeCommand(s, "reboot") # reboot your device
    """
    socket.send('13{}'.format(command_to_run).encode())

def tap(socket, x, y):

	socket.send(("101" + formatSocketData(TOUCH_DOWN, 7, x, y)).encode())

	sleep(0.01)

	socket.send(("101" + formatSocketData(TOUCH_UP, 7, x, y)).encode())

if __name__ == "__main__":

	device_name = run_cmd("ideviceinfo -k DeviceName").replace("\n", "")
	device_ip = device_name.lower().replace(" ", "-")

	device_ip = ''.join([i for i in device_ip if i.isalnum() or i == "-"]) + ".local"

	print("Connecting to " + device_ip + " (" + device_name + ")")

	setup_qt(device_name)

	device = socket.socket()
	device.connect((device_ip, 6000))  # connect to the tweak
	sleep(0.1)  # please sleep after connection.

	mouse = Controller()

	# bounds = get_bounds()
	#
	# print("b", bounds)
	#
	# refresh_bound = BND_RFRSH_CNT
	#
	# while True:
	#
	# 	unscaled_rel_mouse = (
	# 					mouse.position[0] - bounds[0],
	# 					mouse.position[1] - bounds[1]
	# 				)
	#
	# 	window_height = max(abs(bounds[2]-bounds[0]), abs(bounds[3]-bounds[1]))
	#
	# 	rel_mouse = tuple(i * (1920/window_height) for i in unscaled_rel_mouse)
	#
	# 	print("m", rel_mouse, " "*20, end="\r")
	# 	sleep(0.1)
	#
	# 	if refresh_bound < 0:
	# 		refresh_bound = BND_RFRSH_CNT
	# 		bounds = get_bounds()
	# 	else:
	# 		refresh_bound -= 1

	with Listener(
		on_move=lambda *args: on_move(device, *args),
		on_click=lambda *args: on_click(device, *args),
		on_scroll=lambda *args: on_scroll(device, *args),
		suppress=True) as listener:

		print("Listener Started")

		listener.join()
