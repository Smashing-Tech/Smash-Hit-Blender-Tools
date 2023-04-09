import bpy
import requests
import common
import time
import pathlib
import traceback

TEST_TB_MODULE = (__name__ == "__main__")

def report(message):
	"""
	If the user has not opted out of reporting, send a report.
	"""
	
	message = str(message) # ... because maybe ...
	
	# Log locally
	pathlib.Path(common.TOOLS_HOME_FOLDER + "/Report " + str(int(time.time())) + ".txt").write_text(message)
	
	# Log to the server, if allowed by the user
	if (TEST_TB_MODULE or bpy.context.preferences.addons["blender_tools"].preferences.enable_telemetry):
		try:
			requests.post("https://smashhitlab.000webhostapp.com/crash.php?action=report", {"info": message})
		except:
			print("Failed to report failure :P")

# Inject the custom exception handler
import sys

old_exception_hook = sys.excepthook

def shbt_exception_handler(type, value, trace):
	# Format the traceback
	tmsg = "\n".join(traceback.format_tb(trace))
	
	# Report traceback
	report(tmsg)
	
	# Call the old exception hook
	old_exception_hook(type, value, trace)

sys.excepthook = shbt_exception_handler

if (TEST_TB_MODULE):
	def a():
		raise Exception()
	
	def b():
		a()
	
	def c():
		b()
	
	c()
