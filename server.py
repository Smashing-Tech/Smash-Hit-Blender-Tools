"""
HTTP server for test mod
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process
import socket
import tempfile
import xml.etree.ElementTree as et
import common
import os

CONTENT_LEVEL = """<level>
	<room type="http://{}:8000/room?youare={}&amp;ignore=" distance="1000" start="true" end="true" />
</level>"""

TEMPDIR = tempfile.gettempdir() + "/shbt-testserver/"

def parsePath(url):
	"""
	Parse the path into parameters and the real URL
	"""
	
	url = url.split("?")
	params = {}
	
	if (len(url) >= 2):
		url[1] = url[1].split("&")
		
		for param in url[1]:
			p = param.split("=")
			key = p[0]
			value = p[1]
			params[key] = value
	
	url = url[0]
	
	return (url, params)

def loadFileBytes(path):
	"""
	Load a file's bytes.
	"""
	
	f = open(path, "rb")
	content = f.read()
	f.close()
	
	return content

def log(*args):
	"""
	Write content to a log file
	"""
	
	content = ""
	
	for a in args:
		content += format(a) + (" " if a != args[-1] else "")
	
	if (common.PRINT_LOGGING):
		print(content)
	
	if (common.FILE_LOGGING):
		f = open(TEMPDIR + "server.log", "a")
		f.write(content + "\n")
		f.close()

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
	
	room = f"""function init()
	mgMusic({music})
	mgFogColor({options["fog"]}){reverb}{particles}
	
	confSegment("http://{hostname}:8000/segment?youare={hostname}&filetype=", 1)
	
	l = 0
	
	local targetLen = 90
	while l < targetLen do
		s = nextSegment()
		l = l + mgSegment(s, -l)
	end
	
	mgLength(l)
end

function tick()
end"""
	
	return bytes(room, "utf-8")

class AdServer(BaseHTTPRequestHandler):
	"""
	The request handler for the test server
	"""
	
	def log_request(self, code = '-', size = '-'):
		pass
	
	def do_GET(self):
		# Set data
		data = b""
		contenttype = "text/xml"
		
		# Hacky way of parsing parameters
		path, params = parsePath(self.path)
		
		# Handle what data to return
		try:
			### LEVEL ###
			if (path.endswith("level")):
				data = bytes(CONTENT_LEVEL.format(params["youare"], params["youare"]), "utf-8")
			
			### ROOM ###
			elif (path.endswith("room")):
				data = generateRoomText(params["youare"], getSegmentOptions(TEMPDIR + "segment.xml"))
				contenttype = "text/plain"
			
			### SEGMENT ###
			elif (path.endswith("segment") and (params["filetype"] == ".xml")):
				data = loadFileBytes(TEMPDIR + "segment.xml")
			
			### MESH ###
			elif (path.endswith("segment") and (params["filetype"] == ".mesh")):
				data = loadFileBytes(TEMPDIR + "segment.mesh")
				contenttype = "application/octet-stream"
		except:
			# Error on other files
			data = bytes("<html><head><title>404 File Not Found</title></head><body><h1>404 File Not Found</h1><p><i>Smash Hit Blender Tools - Test Server Module</i></p></body></html>", "utf-8")
			self.send_response(404)
			self.send_header("Content-Length", str(len(data)))
			self.send_header("Content-Type", "text/html")
			self.end_headers()
			self.wfile.write(data)
			return
		
		# Send response
		self.send_response(200)
		self.send_header("Content-Length", str(len(data)))
		self.send_header("Content-Type", contenttype)
		self.end_headers()
		self.wfile.write(data)
		
		# Log the request
		log(self.client_address[0] + ":" + str(self.client_address[1]), self.command, self.path, "-> 200 OK")
		log(" ------------------------------------------------------------- ")
		log(format(data))
		log("\n\n\n")

def debug_generate_room():
	f = open(TEMPDIR + "/room.lua", "wb")
	f.write(generateRoomText("owo", getSegmentOptions(TEMPDIR + "segment.xml")))
	f.close()

def runServer():
	"""
	Run the server
	"""
	
	server = HTTPServer(("0.0.0.0", 8000), AdServer)
	
	log("Smash Hit Tools: Server running!")
	
	try:
		server.serve_forever()
	except Exception as e:
		log("Smash Hit Tools: Test server is down:\n\n", e)
	
	server.server_close()

def runServerProcess():
	"""
	Run the server in a different process
	"""
	
	p = Process(target = runServer, args = ())
	p.start()
	return p

if (__name__ == "__main__"):
	runServer()
