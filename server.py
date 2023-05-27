"""
# Quick test server

## Usage

To use the server, you need to have a config at TOOLS_HOME_FOLDER/Quick Test/data.json
which contains the following:

 * [config root]
   * `data`: Path to the data folder, or `null`
   * `room`: Object that contains:
     * `fog`: Fog colour data
     * `music`: Music to use
     * `particles`: Particles
     * `reverb`: Reverb settings
     * `length`: Length of the room
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process
import socket
import tempfile
import xml.etree.ElementTree as et
import common
from urllib.parse import parse_qs
import pathlib
import os
import os.path
import json

# Where any files related to Quick Test 2.0 and later are stored
QUICK_HOME_FOLDER = common.TOOLS_HOME_FOLDER + "/Quick Test"

# The default level data when running without an assets folder
DEFAULT_LEVEL = """<level>
	<room type="http://{}:8000/room?ignore=" distance="1000" start="true" end="true" />
</level>"""

# The legacy temporary directory for segment export
DEFAULT_TEMPDIR = tempfile.gettempdir() + "/shbt-testserver/"

def load_bytes(path):
	"""
	Load a file's bytes.
	"""
	
	return pathlib.Path(path).read_bytes()

def load_text(path):
	"""
	Load a file's bytes.
	"""
	
	return pathlib.Path(path).read_text()

class AssetHandler:
	"""
	Handles everything related to asset finding and loading
	"""
	
	def __init__(self, host):
		self.host = host
		self.load_config(QUICK_HOME_FOLDER + "/data.json")
	
	def load_config(self, path):
		conf = json.loads(pathlib.Path(config_path).read_text())
		
		self.path = conf.get("data", None)
		
		room = conf.get("room", {})
		
		self.fog = room.get("fog", None)
		self.music = room.get("music", None)
		self.particles = room.get("particles", None)
		self.reverb = room.get("reverb", None)
		self.length = room.get("length", None)
	
	def load_segment(self, type = None):
		
	
	def load_room(self, type = None):
		
	
	def load_segment(self, type = None):
		
	
	def load_obstacle(self, type):
		return load_bytes(f"{self.path}/obstacles/{type}.lua.mp3")

def generateRoomText(hostname, options):
	"""
	Generate the content for a room file
	"""
	
	music = options["music"]
	particles = options["particles"]
	reverb = options["reverb"]
	
	music = ("\"" + music + "\"") if music else "tostring(math.random(0, 28))"
	particles = (f"\n\tmgParticles(\"{particles}\")") if particles else ""
	reverb = (f"\n\tmgReverb({reverb})") if reverb else ""
	length = 90
	
	room = f"""function init()
	mgMusic({music})
	mgFogColor({options["fog"]}){reverb}{particles}
	
	confSegment("http://{hostname}:8000/segment?filetype=", 1)
	
	l = 0
	
	local targetLen = {length}
	while l < targetLen do
		s = nextSegment()
		l = l + mgSegment(s, -l)
	end
	
	mgLength(l)
end

function tick()
end"""
	
	return bytes(room, "utf-8")

def updateSegment(text):
	

def doError(self):
	data = bytes("404 File Not Found", "utf-8")
	self.send_response(404)
	self.send_header("Content-Length", str(len(data)))
	self.send_header("Content-Type", "text/plain")
	self.end_headers()
	self.wfile.write(data)

def parsePath(url):
	"""
	Parse the path into parameters and the real URL
	"""
	
	url = url.split("?")
	params = parse_qs(url[1]) if len(url) > 1 else {}
	
	# Only use the first one
	for p in params:
		params[p] = params[p][0]
	
	url = url[0]
	
	return (url, params)

class AdServer(BaseHTTPRequestHandler):
	"""
	The request handler for the test server
	"""
	
	def log_request(self, code = '-', size = '-'):
		pass
	
	def do_GET(self):
		# Log the request
		print(self.client_address[0] + ":" + str(self.client_address[1]), self.command, self.path)
		
		# Set data
		data = b""
		contenttype = "text/xml"
		
		# Parsing parameters
		path, params = parsePath(self.path)
		
		# Get the host's name (that is us!)
		# Taking only the IP makes nonbugged clients (e.g. not SH) work.
		host = self.headers["Host"].split(":")[0]
		
		# Handle what data to return
		try:
			### LEVEL ###
			if (path.endswith("level")):
				data = bytes(CONTENT_LEVEL.format(host), "utf-8")
			
			### ROOM ###
			elif (path.endswith("room")):
				data = generateRoomText(host, getSegmentOptions(TEMPDIR + "segment.xml"))
				contenttype = "text/plain"
			
			### SEGMENT ###
			elif (path.endswith("segment") and (params["filetype"] == ".xml")):
				data = loadFileBytes(TEMPDIR + "segment.xml")
			
			### MESH ###
			elif (path.endswith("segment") and (params["filetype"] == ".mesh")):
				data = loadFileBytes(TEMPDIR + "segment.mesh")
				contenttype = "application/octet-stream"
			
			### MENU UI ###
			elif (path.endswith("menu")):
				data = bytes(f'''<ui texture="menu/start.png" selected="menu/button_select.png"><rect coords="0 0 294 384" cmd="level.start level:http://{host}:8000/level?ignore="/></ui>''', "utf-8")
		except:
			# Error on other files
			return doError(self)
		
		# Send response
		self.send_response(200)
		self.send_header("Content-Length", str(len(data)))
		self.send_header("Content-Type", contenttype)
		self.end_headers()
		self.wfile.write(data)

def makeTestFiles():
	"""
	Create test files
	"""
	
	print("SegServ: Creating test files...")
	
	# Make the folder itself
	os.makedirs(TEMPDIR, exist_ok = True)
	
	# Make test segment
	pathlib.Path(TEMPDIR + "segment.xml").write_text('<segment size="12 10 16"><box pos="0 -1 -1" size="0.5 0.5 0.5" visible="1" color="0.3 0.6 0.9" tile="63"/></segment>')
	
	# Cook mesh for it
	r = os.system(f"python3 ./bake_mesh.py {TEMPDIR + 'segment.xml'} {TEMPDIR + 'segment.mesh'}")
	
	# windows
	if (r):
		os.system(f"py ./bake_mesh.py {TEMPDIR + 'segment.xml'} {TEMPDIR + 'segment.mesh'}")

def runServer(no_blender = False):
	"""
	Run the server
	"""
	
	server = HTTPServer(("0.0.0.0", 8000), AdServer)
	
	if (no_blender):
		makeTestFiles()
	
	print("Smash Hit Quick Test server")
	
	try:
		server.serve_forever()
	except Exception as e:
		print("Quick Test server crashed!\n\n", e)
	
	server.server_close()

def runServerProcess():
	"""
	Run the server in a different process
	"""
	
	p = Process(target = runServer, args = ())
	p.start()
	return p

if (__name__ == "__main__"):
	runServer(no_blender = True)
