#!/usr/bin/python
# coding=utf-8
#
# Copyright (C) 2018-2025 by dream-alpha
#
# In case of reuse of this source code please do not remove this copyright.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For more information on the GNU General Public License see:
# <http://www.gnu.org/licenses/>.
#
# 20250328 recoded from @Lululla

import subprocess
from glob import glob
from os.path import splitext

from .Debug import logger


def stripCutNumber(path):
	filename, ext = splitext(path)
	if len(filename) > 3:
		if filename[-4] == "_" and filename[-3:].isdigit():
			filename = filename[:-4]
		path = filename + ext
	return path


def readFile(path):
	data = ""
	try:
		with open(path, "r") as f:
			data = f.read()
	except Exception as e:
		logger.info("path: %s, exception: %s", path, e)
	return data


def writeFile(path, data):
	try:
		with open(path, "w") as f:
			f.write(data)
	except Exception as e:
		logger.error("path: %s, exception: %s", path, e)


def deleteFile(path):
	result = subprocess.run(['rm', '-f', path], capture_output=True, text=True)
	if result.returncode != 0:
		print(f"Error deleting file: {result.stderr}")
	else:
		print(f"File {path} deleted successfully.")


def deleteFiles(path, clear=False):
	for afile in glob(path):
		if clear:
			writeFile(afile, "")
		deleteFile(afile)


def touchFile(path):
	subprocess.run(['touch', path], capture_output=True, text=True)


def copyFile(src_path, dest_path):
	subprocess.run(['cp', src_path, dest_path], capture_output=True, text=True)


def renameFile(src_path, dest_path):
	subprocess.run(['mv', src_path, dest_path], capture_output=True, text=True)


def createDirectory(path):
	subprocess.run(['mkdir', '-p', path], capture_output=True, text=True)


def createSymlink(src, dst):
	logger.info("link: src: %s > %s", src, dst)
	subprocess.run(['ln', '-s', src, dst], capture_output=True, text=True)


def deleteDirectory(path):
	subprocess.run(['rm', '-rf', path], capture_output=True, text=True)
