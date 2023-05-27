"""
HTTP server for test mod

Notes:

 - Smash Hit does not actually implement the Host header correctly and
   excludes the port. We have to fix that.
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

CONTENT_LEVEL = """<level>
	<room type="http://{}:8000/room?ignore=" distance="1000" start="true" end="true" />
</level>"""

TEMPDIR = tempfile.gettempdir() + "/shbt-testserver/"

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

def loadFileBytes(path):
	"""
	Load a file's bytes.
	"""
	
	return pathlib.Path(path).read_bytes()

def getSegmentOptions(path):
	"""
	Get the segment fog colour, music, particles, reverb strings
	
	TODO: This would break if there are spacing errors. Unlikely, but maybe fix that?
	"""
	
	root = et.fromstring(loadFileBytes(path).decode("utf-8"))
	
	fog = root.attrib.get("fogcolor", "0 0 0 1 1 1").replace(" ", ", ")
	music = root.attrib.get("qt-music", None)
	particles = root.attrib.get("qt-particles", None)
	reverb = root.attrib.get("qt-reverb", "").replace(" ", ", ")
	
	return {"fog": fog, "music": music, "particles": particles, "reverb": reverb}

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

def doError(self):
	data = bytes("404 File Not Found", "utf-8")
	self.send_response(404)
	self.send_header("Content-Length", str(len(data)))
	self.send_header("Content-Type", "text/plain")
	self.end_headers()
	self.wfile.write(data)

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
			doError(self)
			return
		
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
	
	print("** SegServ v1.0 - Smash Hit Quick Test Server **")
	
	try:
		server.serve_forever()
	except Exception as e:
		print("SegServ has crashed!!\n", e)
	
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
