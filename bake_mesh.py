#!/usr/bin/python3
"""
Dataverktyg för konvertera Smash Hit segment till meshfil
"""

import struct
import zlib
import sys
import xml.etree.ElementTree as et
import random # temporary

defaults = {}
TILE_ROWS = 8
TILE_COLS = 8

class Vector3:
	"""
	(Hopefully) simple implementation of a Vector3
	"""
	
	def __init__(self, x = 0.0, y = 0.0, z = 0.0):
		self.x = x
		self.y = y
		self.z = z
	
	@classmethod
	def fromString(self, string):
		cmpnames = ['x', 'y', 'z', 'a']
		
		array = string.split(" ")
		array = [float(array[i]) for i in range(len(array))]
		
		vec = Vector3()
		
		for i in range(len(array)):
			setattr(vec, cmpnames[i], array[i])
		
		return vec
	
	@classmethod
	def random(self):
		return Vector3(random.random(), random.random(), random.random())
	
	def __neg__(self):
		return Vector3(-self.x, -self.y, -self.z)
	
	def __add__(self, other):
		return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
	
	def __sub__(self, other):
		return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
	
	def __mul__(self, scalar):
		return Vector3(scalar * self.x, scalar * self.y, scalar * self.z)
	
	def __format__(self, _unused):
		return f"[{self.x} {self.y} {self.z}]"
	
	def copy(self):
		return Vector3(self.x, self.y, self.z)
	
	def diff(self, other):
		return (self.x == other.x, self.y == other.y, self.z == other.z)
	
	def partialOpposite(self, ax, ay, az):
		"""
		Negate part of the vector (only some compnents, those for which aC is True)
		"""
		return Vector3(self.x if not ax else -self.x, self.y if not ay else -self.y, self.z if not az else -self.z)

class SegmentInfo:
	"""
	Info about the segment and its global information.
	"""
	
	def __init__(self, attribs):
		self.front = float(attribs.get("lightFront", "1.0"))
		self.back = float(attribs.get("lightBack", "1.0"))
		self.left = float(attribs.get("lightLeft", "1.0"))
		self.right = float(attribs.get("lightRight", "1.0"))
		self.top = float(attribs.get("lightTop", "1.0"))
		self.bottom = float(attribs.get("lightBottom", "1.0"))

def meshPointBytes(x, y, z, u, v, r, g, b, a):
	"""
	Return bytes for the point in the mesh
	"""
	
	c = b''
	
	c += struct.pack('f', x)
	c += struct.pack('f', y)
	c += struct.pack('f', z)
	c += struct.pack('f', u)
	c += struct.pack('f', v)
	c += struct.pack('B', int(max(min(r, 1.0), 0.0) * 255))
	c += struct.pack('B', int(max(min(g, 1.0), 0.0) * 255))
	c += struct.pack('B', int(max(min(b, 1.0), 0.0) * 255))
	c += struct.pack('B', int(max(min(a, 1.0), 0.0) * 255))
	
	return c

def meshIndexBytes(i0, i1, i2):
	"""
	Return the bytes for an index in the mesh
	"""
	
	c = b''
	
	c += struct.pack('I', i0)
	c += struct.pack('I', i1)
	c += struct.pack('I', i2)
	
	return c

def getTextureCoords(rows, cols, tile):
	"""
	Gets the texture coordinates given the tile number
	
	Returns ((u1, v1), (u2, v2), (u3, v3), (u4, v4))
	"""
	
	u = (tile % rows) / rows
	v = (tile // rows) / cols
	w = 1 / rows
	h = 1 / cols
	
	return ((u, v), (u, v + h), (u + w, v + h), (u + w, v))

class Quad:
	"""
	Representation of a quadrelaterial (a shape with four sides)
	"""
	
	def __init__(self, p1, p2, p3, p4, colour = None, tile = 0):
		self.p1 = p1
		self.p2 = p2
		self.p3 = p3
		self.p4 = p4
		self.colour = colour if colour else Vector3.random()
		self.tile = tile
	
	def __format__(self, _unused):
		return f"{{ {self.p1} {self.p2} {self.p3} {self.p4} }}"
	
	def asData(self, offset = 0):
		"""
		Convert the quad to a mesh, but also computes the index offsets instead of
		just tris. Offset is the current count of verticies in the mesh file.
		
		Returns tuple of (vertex bytes, index bytes, number of vertexes, number of indicies)
		"""
		
		p1, p2, p3, p4, col = self.p1, self.p2, self.p3, self.p4, self.colour
		tex = getTextureCoords(TILE_ROWS, TILE_COLS, self.tile)
		
		vertexes = b''
		vertexes += meshPointBytes(p1.x, p1.y, p1.z, tex[0][0], tex[0][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1)
		vertexes += meshPointBytes(p2.x, p2.y, p2.z, tex[1][0], tex[1][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1)
		vertexes += meshPointBytes(p3.x, p3.y, p3.z, tex[2][0], tex[2][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1)
		vertexes += meshPointBytes(p4.x, p4.y, p4.z, tex[3][0], tex[3][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1)
		
		index = [offset + 0, offset + 1, offset + 2, offset + 0, offset + 2, offset + 3]
		
		# Swap winding order in some situations so triangles don't get culled
		# 
		if ((p1.x == p3.x and p1.x > 0) or (p1.y == p3.y and p1.y <= 1)):
			index[0], index[2] = index[2], index[0]
			index[3], index[5] = index[5], index[3]
		
		indexes = b''
		indexes += meshIndexBytes(index[0], index[1], index[2])
		indexes += meshIndexBytes(index[3], index[4], index[5])
		
		return (vertexes, indexes, 4, 6)

def generateSubdividedGeometry(minest, maxest, s_size, t_size, colour, tile = 0, swap = False):
	"""
	Generates subdivided quadrelaterials for any given axis where the min/max
	are not the same. Minest/maxist are the min/max of the quad and ssize and 
	tsize are the size of the subdivisions. Swap controls if the s and t size
	components should be swapped.
	
	In the future this will need to handle textures and colours (colours can
	be done very easily I think).
	"""
	
	minest = minest.copy()
	maxest = maxest.copy()
	
	# Init array for quads
	quads = []
	
	# Swap axis sizes
	if (swap):
		ssize, tsize = tsize, ssize
	
	ax_e = "Axis was not property selected if this value is used." # e for Excluded axis
	ax_s = 's'
	ax_t = 't'
	
	# Find which axes should be used
	for a in ['x', 'y', 'z']:
		if (getattr(minest, a) == getattr(maxest, a)):
			ax_e = a
			axes = ['x', 'y', 'z']
			axes.remove(a)
			ax_s = axes[0]
			ax_t = axes[1]
			break
	else:
		print("Similar axis was not found!!")
		return None
	
	# Swap the axis's directions if not in the expected direction
	# After this, min.s <= max.s and min.t <= max.t so it is safe to just add or
	# subtract from s and t directly.
	if (getattr(minest, ax_s) > getattr(maxest, ax_s)):
		temp = getattr(maxest, ax_s)
		setattr(maxest, ax_s, getattr(minest, ax_s))
		setattr(minest, ax_s, temp)
	
	if (getattr(minest, ax_t) > getattr(maxest, ax_t)):
		temp = getattr(maxest, ax_t)
		setattr(maxest, ax_t, getattr(minest, ax_t))
		setattr(minest, ax_t, temp)
	
	# Create the unit vector for each axis
	s_unit = Vector3(0, 0, 0)
	setattr(s_unit, ax_s, 1.0)
	
	t_unit = Vector3(0, 0, 0)
	setattr(t_unit, ax_t, 1.0)
	
	# And the scaled vector too...
	s_scunit = s_unit * s_size
	t_scunit = t_unit * t_size
	
	# Get the constant component that the e axis should always use
	e_location = getattr(minest, ax_e)
	
	# Generate the major axis (s)
	s_current = getattr(minest, ax_s)
	s_max = getattr(maxest, ax_s)
	
	while (s_current < s_max):
		# Generate the minor axis (t)
		t_current = getattr(minest, ax_t)
		t_max = getattr(maxest, ax_t)
		
		while (t_current < t_max):
			# Set the actual unit to be used
			s_scunitpart = s_scunit.copy()
			t_scunitpart = t_scunit.copy()
			
			# Check that there is enough space, if not, truncate the tile (for s and t axis)
			# How this works:
			#   - check if the next tile location is greater than max
			#   - if so, then compute the length of the box and modulo it with its size (get remainder)
			#   - set that new value as the tile size
			if (s_current + s_size > s_max):
				setattr(s_scunitpart, ax_s, abs(getattr(maxest, ax_s) - getattr(minest, ax_s)) % s_size)
			
			if (t_current + t_size > t_max):
				setattr(t_scunitpart, ax_t, abs(getattr(maxest, ax_t) - getattr(minest, ax_t)) % t_size)
			
			# Create first point (hardest one!)
			p1 = Vector3(0, 0, 0)
			setattr(p1, ax_e, e_location)
			setattr(p1, ax_s, s_current)
			setattr(p1, ax_t, t_current)
			
			# Create other points based on first point (using transformed unit vectors)
			p2 = p1 + s_scunitpart
			p3 = p1 + s_scunitpart + t_scunitpart
			p4 = p1                + t_scunitpart
			
			# Finally make the quad
			quads.append(Quad(p1, p2, p3, p4, colour, tile))
			
			# Add new size to total count (for this major axis)
			t_current += t_size
		
		# Count this row as being generated for major axis
		s_current += s_size
	
	return quads

class Box:
	"""
	Very simple container for box data
	"""
	
	def __init__(self, seg, pos, size, colour = Vector3(1.0, 1.0, 1.0), tile = 0, tileSize = Vector3(1.0, 1.0, 0.0)):
		self.segment_info = seg
		self.pos = pos
		self.size = size
		self.colour = colour
		self.tile = tile
		self.tileSize = tileSize
	
	def bakeGeometry(self):
		"""
		Convert the box to the split geometry
		"""
		
		# Tip: When reading this section it helps to draw a diagram of what is
		# happening.
		
		# Shorthands
		tileSize, colour, tile, seg = self.tileSize, self.colour, self.tile, self.segment_info
		
		# Get the eight points (verticies) of the cube
		p1 = self.size.partialOpposite(False, False, False)
		p2 = self.size.partialOpposite(False, False, True )
		p3 = self.size.partialOpposite(False, True , True )
		p4 = self.size.partialOpposite(False, True , False)
		p5 = self.size.partialOpposite(True , False, False)
		p6 = self.size.partialOpposite(True , False, True )
		p7 = self.size.partialOpposite(True , True , True )
		p8 = self.size.partialOpposite(True , True , False)
		
		# Compute the quads (note the min/max don't matter so long as its a square)
		quads  = generateSubdividedGeometry(p1, p6, tileSize.x, tileSize.y, colour * seg.top, tile) # top
		quads += generateSubdividedGeometry(p4, p7, tileSize.x, tileSize.y, colour * seg.bottom, tile) # bottom
		quads += generateSubdividedGeometry(p1, p3, tileSize.x, tileSize.y, colour * seg.left, tile) # left
		quads += generateSubdividedGeometry(p5, p7, tileSize.x, tileSize.y, colour * seg.right, tile) # right
		quads += generateSubdividedGeometry(p2, p7, tileSize.x, tileSize.y, colour * seg.front, tile) # front
		quads += generateSubdividedGeometry(p1, p8, tileSize.x, tileSize.y, colour * seg.back, tile) # back
		
		# Translation transform
		for q in quads:
			q.p1 += self.pos
			q.p2 += self.pos
			q.p3 += self.pos
			q.p4 += self.pos
		
		#print("\n\n\n")
		
		return quads

def writeMeshBinary(data, path):
	f = open(path, "wb")
	
	# Vertex and index data arrays
	vertex = bytearray()
	index = bytearray()
	
	vertex_count = 0
	index_count = 0
	
	# Convert data to bytes
	for d in data:
		r = d.asData(vertex_count)
		
		vertex += r[0]
		index += r[1]
		vertex_count += r[2]
		index_count += r[3]
	
	# Write out final data
	outdata = bytearray()
	outdata += struct.pack('I', vertex_count)
	outdata += vertex
	outdata += struct.pack('I', index_count)
	outdata += index
	
	outdata = zlib.compress(outdata, -1)
	
	f.write(outdata)
	f.close()

def parseXml(data):
	"""
	Parse a segment XML document for boxes
	"""
	
	root = et.fromstring(data)
	boxes = []
	
	if (root.tag != "segment"):
		return None
	
	seg = SegmentInfo(root.attrib)
	
	for e in root:
		if (e.tag == "box"):
			a = e.attrib
			if (a.get("visible", "0") != "0"):
				boxes.append(
					Box(
						seg,
						Vector3.fromString(a.get("pos", "0 0 0")),
						Vector3.fromString(a.get("size", "1 1 1")),
						Vector3.fromString(a.get("color", "1 1 1")),
						int(a.get("tile", "0")),
						Vector3.fromString(a.get("tileSize", "1 1")),
					)
				)
	
	return boxes

def bakeMesh(data, path):
	"""
	Bake a mesh from Smash Hit segment data
	"""
	
	boxes = parseXml(data)
	
	meshData = []
	
	for box in boxes:
		meshData += box.bakeGeometry()
	
	writeMeshBinary(meshData, path)

def main(input_file, output_file):
	f = open(input_file, "r")
	content = f.read()
	f.close()
	
	bakeMesh(content, output_file)

if (__name__ == "__main__"):
	main(sys.argv[1], sys.argv[2])
