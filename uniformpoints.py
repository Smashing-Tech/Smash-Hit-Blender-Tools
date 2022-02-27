"""
This file has been adapted from uniformpoints.cpp from the tuxedolabs website.
The original copyright notice is attached below.

Uniform point distribution on sphere or hemisphere
Copyright (C) 2013 Dennis Gustafsson, http://www.tuxedolabs.com

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
   
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
   
3. This notice may not be removed or altered from any source distribution.

Dennis Gustafsson, dennis@tuxedolabs.com
"""

"""
See https://blog.tuxedolabs.com/2013/03/28/uniformly-distributed-points-on-sphere.html
"""

import math
import random

class Point3:
	"""
	Point3
	"""
	
	def __init__(self, x = 0.0, y = 0.0, z = 0.0):
		self.x = x
		self.y = y
		self.z = z
	
	def __neg__(self):
		return Point3(-self.x, -self.y, -self.z)
	
	def __add__(self, other):
		return Point3(self.x + other.x, self.y + other.y, self.z + other.z)
	
	def __sub__(self, other):
		return Point3(self.x - other.x, self.y - other.y, self.z - other.z)
	
	def __mul__(self, scalar):
		return Point3(scalar * self.x, scalar * self.y, scalar * self.z)
	
	def lenSq(self):
		return self.x ** 2 + self.y ** 2 + self.z ** 2
	
	def normalise(self):
		l = math.sqrt(self.lenSq())
		return self * (1 / l)
	
	def __format__(self, _unused):
		return f"{self.x} {self.y} {self.z}"

def distributePointsOnUnitHemisphere(iterationCount = 1000, pointCount = 64):
	"""
	iterationCount  Number of iterations. Larger = better distribution
	pointCount      Number of points in point data
	[returns]       Points on the unit sphere
	"""
	
	points = []
	
	# Create random points on unit sphere
	for i in range(0, pointCount):
		points.append(Point3(2.0 * random.random() - 1.0, random.random(), 2.0 * random.random() - 1.0).normalise())
	
	# Calculate target distance
	targetDist = math.sqrt(8.0 / pointCount)
	limitsq = targetDist ** 2
	
	# Iterate to make points closer
	for i in range(0, iterationCount):
		for a in range(0, pointCount):
			pa = points[a]
			
			for b in range(a + 1, pointCount):
				pb = points[b]
				d = pb - pa
				lsq = d.lenSq()
				
				if (lsq < limitsq and lsq > 0.0):
					# ???
					l = math.sqrt(lsq)
					t = 0.4 * targetDist * (1.0 - (l / targetDist)) / l
					
					# Move the points
					pa.x = pa.x - d.x * t
					pb.x = pb.x + d.x * t
					pa.y = pa.y - d.y * t
					pb.y = pb.y + d.y * t
					pa.z = pa.z - d.z * t
					pb.z = pb.z + d.z * t
					
					# Clamp to y = 0 if has gotten less
					# NOTE: In the original function this was done after
					# normalisation of the vectors, was that a bug or
					# intentional?
					if (pa.y < 0.0):
						pa.y = 0.0
					
					if (pb.y < 0.0):
						pb.y = 0.0
					
					# Normalise vectors
					points[a] = pa.normalise()
					points[b] = pb.normalise()
	
	return points

if (__name__ == "__main__"):
	points = distributePointsOnUnitHemisphere()
	
	f = open("unit_sphere_points.txt", "w")
	
	for p in points:
		f.write(f"{p}\n")
	
	f.close()
