import common
import os
import os.path as ospath
import pathlib
import tempfile
import getpass
import math
import time
import hashlib

def get_time():
	"""
	Get the current UNIX timestamp
	"""
	
	return math.floor(time.time())

def get_hash(data):
	"""
	Compute the SHA1 hash of a utf8 string
	"""
	
	return hashlib.sha1(data.encode('utf-8')).hexdigest()

def get_trace():
	"""
	The user trace is the first two hex digits of the SHA1 hash of the user's
	username. This means there is only 256 possible values of the trace, so it's
	only really useful for confirming that some untampered segments might have
	been made by the same person, with a relatively high probability of error.
	
	It is meant so that someone can tell if some segments in a mod without a
	given creator name are by the same creator, and for tracking segments in
	general, while still trying to minimise privacy risk.
	"""
	
	username = getpass.getuser()
	
	result = get_hash(username)[:2]
	
	return result

def prepare_folders(path):
	"""
	Make the folders for the file of the given name
	"""
	
	os.makedirs(pathlib.Path(path).parent, exist_ok = True)

def find_apk():
	"""
	Find the path to an APK
	"""
	
	# Search for templates.xml (how we find the APK) and set path
	path = ""
	
	# If the user has set an override path, then just return that if it exists
	override = bpy.context.preferences.addons["blender_tools"].preferences.default_assets_path
	
	if (override and ospath.exists(override)):
		return override
	
	### Try to find from APK Editor Studio ###
	
	try:
		# Get the search path
		search_path = tempfile.gettempdir() + "/apk-editor-studio/apk"
		
		# Enumerate files
		dirs = os.listdir(search_path)
		
		for d in dirs:
			cand = str(os.path.abspath(search_path + "/" + d + "/assets/templates.xml.mp3"))
			
			print("Trying the path:", cand)
			
			if ospath.exists(cand):
				path = str(pathlib.Path(cand).parent)
				break
	except FileNotFoundError:
		print("Smash Hit Tools: No APK Editor Studio folder found.")
	
	print("Final apk path:", path)
	
	return path
