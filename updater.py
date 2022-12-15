"""
Blender Tools Updater
"""

import common
import bpy, functools
import requests
import json

from bpy.types import (UILayout)
from multiprocessing import Process

CHANNEL = common.CHANNEL
UPDATE_INFO = common.UPDATE_INFO
TOOLS_HOME_FOLDER = common.TOOLS_HOME_FOLDER

class Update():
	"""
	Class representing an update
	"""
	
	def __init__(self, release_channel, version, download):
		self.release_channel = release_channel
		self.version = version
		self.download = download

def download_json(source):
	"""
	Download JSON file
	"""
	
	return json.loads(requests.get(source).content)

def download_update(source):
	"""
	Download an update
	
	For now we do not install it until I learn how software signing works under
	the hood (and until that is implemented)
	
	ALSO WE DON'T EVER EVER EVER EVER ENABLE THIS BY DEFAULT
	"""
	
	def update_downloader(url):
		import shutil, pathlib, os
		
		data = requests.get(url).content
		path = TOOLS_HOME_FOLDER + "/" + url.split("/")[-1].replace("/", "").replace("\\", "")
		pathlib.Path(path).write_bytes(data)
		
		print("Smash Hit Tools: Downloaded latest update to " + path)
		print("Please check it for malicous code then you can install it.")
		
		os._exit()
	
	p = Process(target = update_downloader, args = (source,))
	
	p.start()

def download_component(source):
	"""
	Download a component of Blender Tools
	"""
	
	import pathlib
	
	pathlib.Path(TOOLS_HOME_FOLDER + "/" + source.split("/")[-1]).write_bytes(requests.get(source).content)

def show_message(title = "Info", message = "", icon = "INFO"):
	"""
	Show a message as a popup
	"""
	
	def draw(self, context):
		self.layout.label(text = message)
	
	bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def get_latest_version(current_version, release_channel):
	"""
	Check the new version against the current version
	"""
	
	# return Update('stable', [2, 1, 0], "https://github.com/Smashing-Tech/Smash-Hit-Blender-Tools/releases/download/2.0.0/bt_2.0.0.zip")
	
	try:
		info = download_json(UPDATE_INFO).get(release_channel, None)
		
		# No info on release channel
		if (info == None):
			return None
		
		new_version = info["version"]
		
		# Do not prompt to update things with version set to null
		if (new_version == None):
			return None
		
		# Create the update object, if we need to use it
		update = Update(release_channel, new_version, info["download"])
		
		# Check for version
		if (new_version[0] > current_version[0]):
			return update
		elif (new_version[0] == current_version[0]):
			if (new_version[1] > current_version[1]):
				return update
			elif (new_version[1] == current_version[1]):
				if (new_version[2] > current_version[2]):
					return update
		
		# No new updates!
		return None
	
	except Exception as e:
		print(f"Smash Hit Tools: Error checking for new versions:\t\t{e}")
		
		return None

def check_for_updates(current_version):
	"""
	Display a popup if there is an update.
	"""
	
	if (not bpy.context.preferences.addons["blender_tools"].preferences.enable_update_notifier):
		return
	
	update = get_latest_version(current_version, CHANNEL)
	
	if (update != None):
		message = f"Smash Hit Tools v{update.version[0]}.{update.version[1]}.{update.version[2]} (for {update.release_channel} branch) has been released! Download the ZIP file here: {update.download}"
		
		if (bpy.context.preferences.addons["blender_tools"].preferences.enable_auto_update):
			download_update(update.download)
			message = f"Smash Hit Tools v{update.version[0]}.{update.version[1]}.{update.version[2]} (for {update.release_channel} branch) has been released. The ZIP file has been downloaded to your SHBT folder, you just need to install it!"
		
		print("Smash Hit Tools: " + message)
		
		# HACK: Defer execution to when blender has actually loaded otherwise 
		# we make it crash!
		bpy.app.timers.register(functools.partial(show_message, "Smash Hit Tools Update", message), first_interval = 4.5)
	else:
		print("Smash Hit Tools: Up to date (or checker failed or disabled)!")
