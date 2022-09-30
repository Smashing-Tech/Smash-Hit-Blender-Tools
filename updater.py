"""
Blender Tools Updater
"""

import bpy, functools
import requests
import json

CHANNEL = "prerelease"
UPDATE_INFO = "https://knot126.github.io/Smash-Hit-Blender-Tools/update.json"

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

def show_message(title = "Info", message = "", icon = "INFO"):
	"""
	Show a message as a popup
	"""
	
	def draw(self, context):
		self.layout.label(text = message)
	
	bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def check_for_updates(current_version, release_channel):
	"""
	Check the new version against the current version
	"""
	
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

def show_update_dialogue(current_version):
	"""
	Display a popup if there is an update.
	"""
	
	update = check_for_updates(current_version, CHANNEL)
	
	if (update != None):
		message = f"Smash Hit Tools v{update.version[0]}.{update.version[1]}.{update.version[2]} (for {update.release_channel} branch) has been released!\n\nDownload the ZIP file here:\n{update.download}"
		print("Smash Hit Tools: " + message)
		
		# HACK: Defer execution to when blender has actually loaded otherwise 
		# we make it crash!
		bpy.app.timers.register(functools.partial(show_message, "Smash Hit Tools Update", message), first_interval = 4.5)
	else:
		print("Smash Hit Tools: Up to date (or checker failed or disabled)!")
