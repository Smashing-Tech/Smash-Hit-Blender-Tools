#!/usr/bin/env python
"""
Binary XML conversion tool

The format can handle any basic XML file.

Format:

0x00 <nulstring: comment> -- Comment
0x01 <nulstring: tag name> (0x01 <nulstring: attrib> <nulstring: value>)* 0x00 -- Start of tag
0x02 <nulstring: tag name> -- End of tag
0x03 <nulstring: text> -- Text in tag
0xff <eof> -- End of stream

Currently this only converts to the format. This is really just meant to
be a bake only format that you implement on the side of the other app!
"""

import xml.etree.ElementTree as et
import sys, os, pathlib

def print_usage_and_exit():
	print(f"Usage:")
	print(f"{sys.argv[0]} to_bin [input] [output]")
	sys.exit(1)

def node_to_bin(node):
	"""
	Convert a XML node to binary
	"""
	
	data = bytearray()
	
	# Node tag name
	data += b"\x01" + node.tag.encode('utf-8') + b"\x00"
	
	# Attributes 
	for a in node.attrib:
		data += b"\x01"
		data += a.encode('utf-8') + b"\x00"
		data += node.attrib[a].encode('utf-8') + b"\x00"
	
	data += b"\x00"
	
	# Subnodes go here!
	for sub in node:
		data += node_to_bin(sub)
	
	# Text if any
	if (node.text):
		data += b"\x03" + node.text.encode('utf-8') + b"\x00"
	
	# Close the node
	data += b"\x02" + node.tag.encode('utf-8') + b"\x00"
	
	return data

def from_string(string):
	"""
	Bake an XML string into a BinaryXML byte string
	"""
	
	root = et.fromstring(string)
	
	data = bytearray()
	data += b"\x00BinaryXML format 1.0 (by Knot126)\x00"
	
	data += node_to_bin(root)
	
	data += b"\xff"
	
	return data

def main():
	if (len(sys.argv) != 4):
		print_usage_and_exit()
	
	# Convert to bin
	if (sys.argv[1] == "to_bin"):
		pathlib.Path(sys.argv[3]).write_bytes(from_string(pathlib.Path(sys.argv[2]).read_text()))
	else:
		print_usage_and_exit()

if (__name__ == "__main__"):
	main()
