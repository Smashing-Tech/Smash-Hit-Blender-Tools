#!/usr/bin/env python
"""
Tool to sign SHBT updates.
"""

import sys, rsa, random
PrivateKey = rsa.PrivateKey
from pathlib import Path

def generate_keys():
	"""
	Generate a set of private and public keys.
	"""
	
	print("Generating new key pair...")
	
	public, private = rsa.newkeys(4096)
	
	Path("./shbt-public.key").write_text(f"{public}")
	Path(f"../shbt-private-{random.randint(100000, 999999)}.key").write_text(f"{private}")
	
	print("done")

def sign_file(path, key_path):
	"""
	Sign a file's hash
	"""
	
	print("Signing file...\n")
	
	private = eval(Path(key_path).read_text())
	
	signature = rsa.sign(Path(path).read_bytes(), private, "SHA-512")
	
	print("-- BEGIN SIGNATURE --")
	print(f"{signature}")
	print("-- END SIGNATURE --")
	
	Path(path + ".sig").write_bytes(signature)

def main():
	if (len(sys.argv) == 1):
		print(f"{sys.argv[0]} new-keys                            To generate new keys.")
		print(f"{sys.argv[0]} [file to sign] [private key file]   To sign a file.")
		return
	
	p = sys.argv[1]
	
	if (p == "new-keys"):
		generate_keys()
	else:
		sign_file(p, sys.argv[2])

if (__name__ == "__main__"):
	main()
