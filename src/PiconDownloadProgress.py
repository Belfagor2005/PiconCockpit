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

from os import makedirs
from os.path import join, dirname

from twisted.internet import reactor

from .Debug import logger
from . import _
from .FileProgress import FileProgress
from .DelayTimer import DelayTimer


class PiconDownloadProgress(FileProgress):
	skin = """
			<screen name="PiconDownloadProgress" position="5,5" size="851,204" title="PiconDownloadProgress" flags="wfNoBorder">
				<widget source="key_red" render="Label" position="12,144" size="200,45" zPosition="11" font="Regular; 30" valign="center" halign="center" backgroundColor="background" transparent="1" foregroundColor="white" />
				<widget source="key_green" render="Label" position="220,144" size="200,45" zPosition="11" font="Regular; 30" valign="center" halign="center" backgroundColor="background" transparent="1" foregroundColor="white" />
				<widget source="key_yellow" render="Label" position="430,144" size="200,45" zPosition="11" font="Regular; 30" valign="center" halign="center" backgroundColor="background" transparent="1" foregroundColor="white" />
				<widget source="key_blue" render="Label" position="639,144" size="200,45" zPosition="11" font="Regular; 30" valign="center" halign="center" backgroundColor="background" transparent="1" foregroundColor="white" />
				<eLabel backgroundColor="#00ff0000" position="12,190" size="200,8" zPosition="12" />
				<eLabel backgroundColor="#0000ff00" position="218,190" size="200,8" zPosition="12" />
				<eLabel backgroundColor="#00ffff00" position="429,190" size="200,8" zPosition="12" />
				<eLabel backgroundColor="#000000ff" position="640,190" size="200,8" zPosition="12" />
				<eLabel position="30,50" size="800,10" backgroundColor="#202020" transparent="0" zPosition="0" />
				<widget name="name" position="30,60" size="800,40" borderWidth="1" borderColor="#cccccc" zPosition="1" font="Regular; 24" halign="center" />
				<widget name="slider1" position="30,50" size="800,8" borderWidth="1" borderColor="#cccccc" zPosition="2" />
				<widget source="status" render="Label" position="28,102" size="800,36" font="Regular;30" halign="center" valign="bottom" foregroundColor="#ffffff" backgroundColor="#000000" transparent="1" />
				<widget name="operation" position="32,5" size="800,40" borderWidth="1" borderColor="#cccccc" zPosition="1" font="Regular; 24" halign="center" />
			</screen>
			"""

	def __init__(self, session, picon_set_url, picons, picon_dir):

		logger.debug("...")
		self.picon_set_url = picon_set_url
		self.picons = picons
		self.picon_dir = picon_dir
		FileProgress.__init__(self, session)
		self.setTitle(_("Picon Download") + " ...")
		self.execution_list = []
		self.onShow.append(self.onDialogShow)

	def doFileOp(self, entry):
		picon = entry
		self.file_name = picon
		self.status = _("Please wait") + " ..."
		self.updateProgress()

		url = join(self.picon_set_url, picon)
		download_file = join(self.picon_dir, picon)

		if isinstance(url, bytes):
			url = url.decode('utf-8')
		if isinstance(download_file, bytes):
			download_file = download_file.decode('utf-8')

		logger.debug("Starting download: %s -> %s", url, download_file)
		reactor.callInThread(
			self.threadedDownload,
			url,
			download_file,
			lambda: reactor.callFromThread(self.downloadSuccess),
			lambda error: reactor.callFromThread(self.downloadError, error, url)
		)

	def threadedDownload(self, url, dest_path, success_cb, error_cb):
		import requests
		from requests.exceptions import RequestException
		try:
			makedirs(dirname(dest_path), exist_ok=True)

			with requests.get(url, stream=True, timeout=10) as r:
				r.raise_for_status()
				with open(dest_path, 'wb') as f:
					for chunk in r.iter_content(chunk_size=8192):
						if chunk:  # Filtra keep-alive chunks
							f.write(chunk)

			logger.debug("Download completato: %s", dest_path)
			success_cb()
		except RequestException as e:
			logger.error("Download fallito: %s", str(e))
			error_cb(e)
		except Exception as e:
			logger.error("Errore imprevisto: %s", str(e))
			error_cb(e)

	def onDialogShow(self):
		logger.debug("...")
		self.execPiconDownloadProgress()

	def downloadSuccess(self, _result=None):
		# logger.info("...")
		self.nextFileOp()

	def downloadError(self, error, url):
		logger.error("Errore download %s: %s", url, str(error))
		self.nextFileOp()

	def execPiconDownloadProgress(self):
		logger.debug("...")
		self.status = _("Initializing") + " ..."
		self.updateProgress()
		self.execution_list = self.picons
		self.total_files = len(self.execution_list)
		DelayTimer(10, self.nextFileOp)
