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
from .__init__ import _
from .FileProgress import FileProgress
from .DelayTimer import DelayTimer


class PiconDownloadProgress(FileProgress):
	skin = """
			<screen name="PICPiconDownloadProgress" position="center,center" size="1220,305" title="">
				<ePixmap pixmap="skin_default/buttons/red.svg" position="10,5" size="300,70"/>
				<ePixmap pixmap="skin_default/buttons/green.svg" position="310,5" size="300,70"/>
				<ePixmap pixmap="skin_default/buttons/yellow.svg" position="610,5" size="300,70"/>
				<ePixmap pixmap="skin_default/buttons/blue.svg" position="910,5" size="300,70"/>
				<widget backgroundColor="#f23d21" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_red" position="10,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
				<widget backgroundColor="#389416" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_green" position="310,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
				<widget backgroundColor="#e6bd00" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_yellow" position="610,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
				<widget backgroundColor="#0064c7" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_blue" position="910,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1"/>
				<eLabel backgroundColor="grey" position="10,75" size="1200,1"/>
				<widget font="Regular;32" halign="left" name="operation" position="10,90" size="1200,43" transparent="1" valign="center"/>
				<widget name="slider1" position="10,150" size="1200,25"/>
				<widget font="Regular;32" halign="left" name="name" position="10,192" size="1200,43" transparent="1" valign="center"/>
				<widget font="Regular;32" halign="left" name="status" position="10,245" size="1200,43" transparent="1" valign="center"/>
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
