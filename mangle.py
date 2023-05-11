"""
This helps obfuscate a segment and make it harder to load in another libsmashhit.
It should stop more casual copying of segments, or at least make it so it's harder
to copy segments especially for people who cannot write scripts.
"""

import common
import secrets

REPLACEABLE_STRINGS = [""]

class MangleConfig:
	"""
	A lock information file
	"""
	
	def __init__(self, filename = None):
		self.path = (common.TOOLS_HOME_FOLDER + "/magle.slk") if not filename else filename
		self.table = {}
	
	def generate(self):
		

class ManglePatcher:
	"""
	A libsmashhit.so patcher
	"""
	
	def __init__(self, path):
		"""
		Initialise the file context
		"""
		
		pass
