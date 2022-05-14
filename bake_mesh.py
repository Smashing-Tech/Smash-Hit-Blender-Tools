#!/usr/bin/python3
"""
Tool for baking a Smash Hit mesh
"""

import struct
import zlib
import sys
import xml.etree.ElementTree as et
import random
import math

# Version of mesh baker; this is not used anywhere.
VERSION = (0, 13, 2)

# The number of rows and columns in the tiles.mtx.png file. Change this if you
# have overloaded the file with more tiles; note that you will also need to
# rebake other segments with the same row/column setting.
TILE_ROWS = 8
TILE_COLS = 8

# The amount of a tile that should be clipped off the edges. This mostly done to
# hide hard edges between tile textures.
# 
# I don't know why it's this constant by default specifically, but you can
# find 0.00390625 in LitMesh::addBox which is TILE_BITE_ROW / TILE_ROWS (and
# COLS too)
TILE_BITE_ROW = 0.03125
TILE_BITE_COL = 0.03125

# Disable or enable baking unseen and back faces. Note that unseen faces does
# includes back faces, so both must be enabled for those.
BAKE_UNSEEN_FACES = False

# Ignore the tileSize attribute, defaulting to the single unit tile, which can
# be misinterprted on some segments.
BAKE_IGNORE_TILESIZE = False

# Randomises colours of quads for debugging purposes.
PARTY_MODE = False

# Enable vertex lighting using delta boxes
VERTEX_LIGHT_ENABLED = True

# Half of the size of the delta box when using the delta-box lighting method
VERTEX_LIGHT_DELTA_BOX_SIZE = 0.5

################################################################################
### END OF CONFIGURATION #######################################################
################################################################################

def removeEverythingEqualTo(array, value):
	"""
	Remove everything in an array equal to a value
	"""
	
	while (True):
		try:
			array.remove(value)
		except ValueError:
			return array

class Vector3:
	"""
	(Hopefully) simple implementation of a Vector3
	"""
	
	def __init__(self, x = 0.0, y = 0.0, z = 0.0, a = 1.0):
		self.x = x
		self.y = y
		self.z = z
		self.a = a
	
	@classmethod
	def fromString(self, string, many = False):
		"""
		Convert a vector or list of vectors from a string to a vector object
		"""
		
		cmpnames = ['x', 'y', 'z', 'a']
		
		array = removeEverythingEqualTo(string.split(" "), "")
		array = [float(array[i]) for i in range(len(array))]
		
		# Handle overloaded string array
		if (many and len(array) >= 6 and (len(array) % 3) == 0):
			vectors = []
			
			for i in range(len(array) // 3):
				vectors.append(Vector3(array[i * 3 + 0], array[i * 3 + 1], array[i * 3 + 2]))
			
			return vectors
		
		vec = Vector3()
		
		for i in range(min(len(array), 4)):
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
	
	def __mul__(self, other):
		if (type(other) == Vector3):
			return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)
		else:
			return Vector3(other * self.x, other * self.y, other * self.z)
	
	def __truediv__(self, other):
		return Vector3(self.x / other.x, self.y / other.y, self.z / other.z)
	
	def __format__(self, _unused):
		return f"{self.x} {self.y} {self.z}"
	
	def __eq__(self, other):
		if (type(self) != type(other)): return False
		v = self - other
		d = 0.001
		return (-d <= v.x <= d) and (-d <= v.y <= d) and (-d <= v.z <= d)
	
	def lengthSquared(self):
		return self.x * self.x + self.y * self.y + self.z * self.z
	
	def length(self):
		return math.sqrt(self.lengthSquared())
	
	def normalise(self):
		length = self.length()
		length = (1 / length) if not length <= 0.0 else 0.0
		return Vector3(self.x * length, self.y * length, self.z * length)
	
	def cross(self, other):
		x = self.y * other.z - self.z * other.y
		y = self.z * other.x - self.x * other.z
		z = self.x * other.y - self.y * other.x
		return Vector3(x, y, z)
	
	def copy(self):
		return Vector3(self.x, self.y, self.z)
	
	def diff(self, other):
		return (self.x == other.x, self.y == other.y, self.z == other.z)
	
	def withLight(self, light):
		"""
		Return a copy of self with a component set
		"""
		v = self.copy()
		v.a = light
		return v
	
	def partialOpposite(self, ax, ay, az):
		"""
		Negate part of the vector (only some compnents, those for which aC is True)
		"""
		return Vector3(self.x if not ax else -self.x, self.y if not ay else -self.y, self.z if not az else -self.z)

def parseIntTriplet(string):
	"""
	Parse either a single int or three ints in a string to a tuple of three ints
	"""
	
	array = removeEverythingEqualTo(string.split(" "), "")
	array = [int(array[i]) for i in range(len(array))]
	
	if (len(array) < 3):
		c = len(array) - 1
		
		for _ in range(c, 3):
			array.append(array[c])
	
	return (array[0], array[1], array[2])

def parseFloatTriplet(string):
	"""
	Parse either a single float or three float in a string to a tuple of three floats
	"""
	
	array = removeEverythingEqualTo(string.split(" "), "")
	array = [float(array[i]) for i in range(len(array))]
	
	if (len(array) < 3):
		c = len(array) - 1
		
		for _ in range(c, 3):
			array.append(array[c])
	
	return (array[0], array[1], array[2])

class SegmentInfo:
	"""
	Info about the segment and its global information.
	"""
	
	def __init__(self, attribs, templates = None, boxes = None):
		self.template = attribs.get("template", None)
		
		self.front = float(getFromTemplate(attribs, templates, self.template, "lightFront", "1.0"))
		self.back = float(getFromTemplate(attribs, templates, self.template, "lightBack", "1.0"))
		self.left = float(getFromTemplate(attribs, templates, self.template, "lightLeft", "1.0"))
		self.right = float(getFromTemplate(attribs, templates, self.template, "lightRight", "1.0"))
		self.top = float(getFromTemplate(attribs, templates, self.template, "lightTop", "1.0"))
		self.bottom = float(getFromTemplate(attribs, templates, self.template, "lightBottom", "1.0"))
		
		self.boxes = boxes
	
	def boxcast(self, pos, size):
		"""
		Check for the largest collision (by volume) of a box in a scene in a
		tuple with (accum volume, number intersected)
		"""
		
		total = 0.0
		intersected = 0
		
		for b in self.boxes:
			result = b.testAABB(pos, size)
			
			if (result):
				volume = (2.0 * result[1].x) * (2.0 * result[1].y) * (2.0 * result[1].z)
				
				intersected += 1
				total += volume
		
		return (total, intersected)

def doVertexLights(x, y, z, a, gc, normal):
	"""
	Compute the light at a vertex
	
	The following method is an idea that I had to get percise light information
	about a point very quickly when a scene has only AABBs. Basically, we pick
	a vertex then create a cube of a certian length, width and height around
	that vertex. We then find every intersection with that box and sum the
	volume of the union of those intersections. After this, we take the ratio
	between the volume of half the delta box and the accumulated volume. With
	this, we subtract half of the delta box volume from our accumulated volume,
	max it with 0, divide that by half of the delta box volume and finally cube
	root it which should give us an apprimation of the light that reaches this
	point without preforming many many raycasts.
	
	This has some issues: overlaping boxes can cause the algorithm to overshade
	some point dramatically.
	
	Updated for 0.13: Now it increments the position by normal * deltaboxsize so
	we are closer to just a raycast
	"""
	
	# Find the size and half of the volume of the delta box
	delta_box_size = Vector3(VERTEX_LIGHT_DELTA_BOX_SIZE, VERTEX_LIGHT_DELTA_BOX_SIZE, VERTEX_LIGHT_DELTA_BOX_SIZE)
	delta_box_volume = 8.0 * ((VERTEX_LIGHT_DELTA_BOX_SIZE) ** 3)
	
	# Find the box with largest volume intresecting the box around this vertex
	accum, isect = gc.boxcast(Vector3(x, y, z) + normal * VERTEX_LIGHT_DELTA_BOX_SIZE, delta_box_size)
	
	# Find the light based on the volume taken
	# This is min/max'd to not cause major issues if there is an overlaping box
	shade = min(max(accum, 0), delta_box_volume) / delta_box_volume
	
	return (a ** 2) * (1.0 - 0.47 * shade ** 0.3)

def correctColour(x, y, z, r, g, b, a, gc, normal):
	"""
	Do any final colour correction operations and per-vertex lighting.
	"""
	
	if (VERTEX_LIGHT_ENABLED):
		a = doVertexLights(x, y, z, a, gc, normal)
	
	return r * 0.5, g * 0.5, b * 0.5, a

def meshPointBytes(x, y, z, u, v, r, g, b, a, gc, normal):
	"""
	Return bytes for the point in the mesh
	
	gc is the segment context that contains the box list for lighting
	"""
	
	r, g, b, a = correctColour(x, y, z, r, g, b, a, gc, normal)
	
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

def rotateList(e, n):
	"""
	Rotate n elements of a list e
	"""
	
	n %= len(e)
	
	for i in range(n):
		e.append(e.pop(0))
	
	return e

def getTextureCoords(rows, cols, bite_row, bite_col, rot, tile):
	"""
	Gets the texture coordinates given the tile number.
	
	The tile bite is a small region of the tile that is clipped off.
	
	Returns ((u1, v1), (u2, v2), (u3, v3), (u4, v4))
	"""
	
	bite_row = (bite_row / rows)
	bite_col = (bite_col / cols)
	u = ((tile % rows) / rows) + bite_row
	v = ((tile // rows) / cols) + bite_col
	w = (1 / rows) - (2 * bite_row)
	h = (1 / cols) - (2 * bite_col)
	
	return rotateList([(u, v), (u, v + h), (u + w, v + h), (u + w, v)], rot)

class Quad:
	"""
	Representation of a quadrelaterial (a shape with four sides)
	"""
	
	def __init__(self, p1, p2, p3, p4, colour, tile, tileRot, seg, normal):
		self.p1 = p1
		self.p2 = p2
		self.p3 = p3
		self.p4 = p4
		self.colour = colour if not PARTY_MODE else Vector3.random()
		self.tile = tile
		self.tileRot = tileRot
		self.seg = seg
		self.normal = normal
	
	def __format__(self, _unused):
		return f"{{ {self.p1} {self.p2} {self.p3} {self.p4} }}"
	
	def asData(self, offset = 0):
		"""
		Convert the quad to a mesh, but also computes the index offsets instead of
		just tris. Offset is the current count of verticies in the mesh file.
		
		Returns tuple of (vertex bytes, index bytes, number of vertexes, number of indicies)
		"""
		
		p1, p2, p3, p4, col, gc, normal = self.p1, self.p2, self.p3, self.p4, self.colour, self.seg, self.normal
		tex = getTextureCoords(TILE_ROWS, TILE_COLS, TILE_BITE_ROW, TILE_BITE_COL, self.tileRot, self.tile)
		
		vertexes = b''
		vertexes += meshPointBytes(p1.x, p1.y, p1.z, tex[0][0], tex[0][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1, gc, normal)
		vertexes += meshPointBytes(p2.x, p2.y, p2.z, tex[1][0], tex[1][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1, gc, normal)
		vertexes += meshPointBytes(p3.x, p3.y, p3.z, tex[2][0], tex[2][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1, gc, normal)
		vertexes += meshPointBytes(p4.x, p4.y, p4.z, tex[3][0], tex[3][1], col.x, col.y, col.z, col.a if hasattr(col, "a") else 1, gc, normal)
		
		index = [offset + 0, offset + 1, offset + 2, offset + 0, offset + 2, offset + 3]
		
		# Swap winding order in some situations so triangles don't get culled
		if ((p1.x == p3.x and p1.x > 0) or (p1.y == p3.y and p1.y <= 1)):
			index[0], index[2] = index[2], index[0]
			index[3], index[5] = index[5], index[3]
		
		indexes = b''
		indexes += meshIndexBytes(index[0], index[1], index[2])
		indexes += meshIndexBytes(index[3], index[4], index[5])
		
		return (vertexes, indexes, 4, 6)

def generateSubdividedGeometry(minest, maxest, s_size, t_size, colour, tile, tileRot, seg, normal):
	"""
	Generates subdivided quadrelaterials for any given axis where the min/max
	are not the same. Minest/maxist are the min/max of the quad and ssize and 
	tsize are the size of the subdivisions. Colour and tile are the colour and
	tile. The normal is the normal of the surface.
	"""
	
	minest = minest.copy()
	maxest = maxest.copy()
	
	# Init array for quads
	quads = []
	
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
			quads.append(Quad(p1, p2, p3, p4, colour, tile, tileRot, seg, normal))
			
			# Add new size to total count (for this major axis)
			t_current += t_size
		
		# Count this row as being generated for major axis
		s_current += s_size
	
	return quads

def sgn(x):
	"""
	Sign function
	"""
	
	if (x == None): return 0
	if (x >  0.0): return 1
	if (x == 0.0): return 0
	if (x <  0.0): return -1

def dnz(x, y):
	"""
	Divide with non-panic zero handler
	"""
	
	if (y == 0.0):
		return None
	else:
		return x / y

class Box:
	"""
	Very simple container for box data
	"""
	
	def __init__(self, seg, pos, size, colour = [Vector3(1.0, 1.0, 1.0), Vector3(1.0, 1.0, 1.0), Vector3(1.0, 1.0, 1.0)], tile = (0, 0, 0), tileSize = (1.0, 1.0, 1.0), tileRot = (0, 0, 0)):
		"""
		seg: global segment context
		pos: position
		size: size of the box
		colour: list or tuple of the face colours of the box
		tile: list or tuple of tiles to use
		tileSize: size of the box tiles
		tileRot: rotation of the boxes
		"""
		
		# Expand shorthands for vectors
		if (type(colour) == Vector3):
			colour = [colour]
		
		if (len(colour) == 1):
			colour = [colour[0], colour[0], colour[0]]
		
		# Set attributes
		self.segment_info = seg
		self.pos = pos
		self.size = size
		self.colour = colour
		self.tile = tile
		self.tileSize = tileSize
		self.tileRot = tileRot
	
	def bakeGeometry(self):
		"""
		Convert the box to the split geometry. This is also where a lot of
		fixes occur, like setting the tile index per face and fixing tile
		rotation per side.
		"""
		
		# Tip: When reading this section it helps to draw a diagram of what is
		# happening.
		
		# Shorthands
		pos, tileSize, colour, tile, seg, tileRot = self.pos, self.tileSize, self.colour, self.tile, self.segment_info, self.tileRot
		
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
		# Only some are baked based on config settings
		quads = []
		
		# Right
		if (BAKE_UNSEEN_FACES or pos.x < 0.0):
			quads += generateSubdividedGeometry(
				p1, p3,
				tileSize[2], tileSize[2],
				colour[0].withLight(seg.right),
				tile[0],
				(tileRot[0] + 1) % 4,
				seg,
				Vector3(1.0, 0.0, 0.0)
			)
		
		# Left
		if (BAKE_UNSEEN_FACES or pos.x > 0.0):
			quads += generateSubdividedGeometry(
				p5, p7,
				tileSize[2], tileSize[2],
				colour[0].withLight(seg.left),
				tile[0],
				(tileRot[0] + 1) % 4,
				seg,
				Vector3(-1.0, 0.0, 0.0)
			)
		
		# Top
		if (BAKE_UNSEEN_FACES or pos.y < 1.0):
			quads += generateSubdividedGeometry(
				p1, p6,
				tileSize[1], tileSize[1],
				colour[1].withLight(seg.top),
				tile[1],
				(tileRot[1] + 2) % 4,
				seg,
				Vector3(0.0, 1.0, 0.0)
			)
		
		# Bottom
		if (BAKE_UNSEEN_FACES or pos.y > 1.0):
			quads += generateSubdividedGeometry(
				p4, p7,
				tileSize[1], tileSize[1],
				colour[1].withLight(seg.bottom),
				tile[1],
				(tileRot[1] + 2) % 4,
				seg,
				Vector3(0.0, -1.0, 0.0)
			)
		
		# Front
		quads += generateSubdividedGeometry(
			p1, p8,
			tileSize[0], tileSize[0],
			colour[2].withLight(seg.front),
			tile[2],
			tileRot[2],
			seg, 
			Vector3(0.0, 0.0, 1.0)
		)
		
		# Back
		if (BAKE_UNSEEN_FACES):
			quads += generateSubdividedGeometry(
				p2, p7,
				tileSize[0], tileSize[0],
				colour[2].withLight(seg.back),
				tile[2],
				tileRot[2],
				seg,
				Vector3(0.0, 0.0, -1.0)
			)
		
		# Translation transform
		for q in quads:
			q.p1 += self.pos
			q.p2 += self.pos
			q.p3 += self.pos
			q.p4 += self.pos
		
		return quads
	
	def testAABB(self, other_pos, other_size):
		"""
		Intersect self with another AABB and return origin and size of the
		formed aabb
		"""
		
		def test_aabb_axis(a_min, a_max, b_min, b_max):
			"""
			Test a single aabb axis returning the midpoint and half-difference of two values
			"""
			
			if (a_min > a_max):
				a_min, a_max = a_max, a_min
			
			if (b_min > b_max):
				b_min, b_max = b_max, b_min
			
			if (a_max >= b_min and b_max >= a_min):
				return (0.5 * (b_max + a_min), 0.5 * (min(a_max, b_max) - max(a_min, b_min)))
			else:
				return None
		
		########################################################################
		
		x = test_aabb_axis(self.pos.x - self.size.x, self.pos.x + self.size.x, other_pos.x - other_size.x, other_pos.x + other_size.x)
		y = test_aabb_axis(self.pos.y - self.size.y, self.pos.y + self.size.y, other_pos.y - other_size.y, other_pos.y + other_size.y)
		z = test_aabb_axis(self.pos.z - self.size.z, self.pos.z + self.size.z, other_pos.z - other_size.z, other_pos.z + other_size.z)
		
		if (x != None and y != None and z != None):
			#       Origin                     Size
			return (Vector3(x[0], y[0], z[0]), Vector3(x[1], y[1], z[1]))
		
		return None

def writeMeshBinary(data, path, seg = None):
	f = open(path, "wb")
	
	# Vertex and index data arrays
	vertex = bytearray()
	index = bytearray()
	
	vertex_count = 0
	index_count = 0
	
	i = 1
	l = len(data)
	
	# Convert data to bytes
	for d in data:
		r = d.asData(vertex_count)
		
		# print(f"Exported quad {i} of {l} [{(i / l) * 100.0}% done]"); i += 1;
		
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

def getFromTemplate(boxattr, template_list, template, attr, default):
	"""
	Get an attribute from the template or object
	"""
	
	res = boxattr.get(attr, template_list.get(template, {}).get(attr, default))
	
	return res

def parseXml(data, templates = {}):
	"""
	Parse a segment XML document for boxes. Templates are resolved at this point.
	Even if there are no templates to be loaded, templates must be a dictionary.
	"""
	
	root = et.fromstring(data)
	boxes = []
	
	if (root.tag != "segment"):
		return None
	
	seg = SegmentInfo(root.attrib, templates, boxes)
	
	# Create a box for each box in the segment
	for e in root:
		if (e.tag == "box"):
			a = e.attrib
			t = a.get("template", None)
			
			if (getFromTemplate(a, templates, t, "visible", "1") != "0"):
				# Get properties
				
				# Position -- x y z
				pos = Vector3.fromString(getFromTemplate(a, templates, t, "pos", "0 0 0"))
				
				# Size -- x y z
				size = Vector3.fromString(getFromTemplate(a, templates, t, "size", "0.5 0.5 0.5"))
				
				# Colour -- r1 g1 b1   [r2 g2 b2   r3 g3 b3]
				colour = Vector3.fromString(getFromTemplate(a, templates, t, "color", "1 1 1"), True)
				
				# Tile -- tile1 [tile2 tile3]
				tile = parseIntTriplet(getFromTemplate(a, templates, t, "tile", "0"))
				
				# Tile size -- size1 [size2 size3]
				tileSize = parseFloatTriplet(getFromTemplate(a, templates, t, "tileSize", "1"))
				
				# Tile rotation -- rot1 [rot2 rot3]
				tileRot = parseIntTriplet(getFromTemplate(a, templates, t, "tileRot", "1"))
				
				boxes.append(Box(seg, pos, size, colour, tile, tileSize, tileRot))
	
	return seg

def parseTemplatesXml(path):
	"""
	Load templates from a file
	"""
	
	result = {}
	
	tree = et.parse(path)
	root = tree.getroot()
	
	assert("templates" == root.tag)
	
	# Loop over templates in XML file and load them
	for child in root:
		assert("template" == child.tag)
		
		name = child.attrib["name"]
		attribs = child[0].attrib
		
		result[name] = attribs
	
	return result

def bakeMesh(data, path, templates_path = None):
	"""
	Bake a mesh from Smash Hit segment data
	"""
	
	seg = parseXml(data, parseTemplatesXml(templates_path) if templates_path else {})
	boxes = seg.boxes
	
	meshData = []
	
	for box in boxes:
		meshData += box.bakeGeometry()
	
	writeMeshBinary(meshData, path, seg)

def main(input_file, output_file, template_file = None):
	f = open(input_file, "r")
	data = f.read()
	f.close()
	
	bakeMesh(data, output_file, template_file)

if (__name__ == "__main__"):
	main(sys.argv[1], sys.argv[2], sys.argv[3] if (len(sys.argv) >= 4) else None)
