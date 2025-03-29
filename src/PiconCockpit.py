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

from os import makedirs, popen, remove, rename
import uuid
import glob
from os.path import exists, join, dirname
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config, configfile
from Tools.LoadPixmap import LoadPixmap

import requests
from requests.exceptions import RequestException
from twisted.internet import reactor

from . import _
from .FileUtils import readFile, createDirectory
from .ConfigScreen import ConfigScreen
from .PiconDownloadProgress import PiconDownloadProgress
from .ConfigInit import ConfigInit
from .List import List
from .ServiceData import getServiceList, getTVBouquets, getRadioBouquets
from .Debug import logger

picon_info_file = "picon_info.txt"
picon_list_file = "zz_picon_list.txt"


class PiconCockpit(Screen):

	skin = """
		<screen name="PICPiconCockpit" position="0,0" size="1920,1080" title="" flags="wfNoBorder">
			<widget source="session.VideoPicture" render="Pig" position="1406,119" zPosition="20" size="491,319" backgroundColor="transparent" transparent="0" cornerRadius="14" />
			<eLabel backgroundColor="#00ff0000" position="11,74" size="300,8" zPosition="12" />
			<eLabel backgroundColor="#0000ff00" position="307,74" size="300,8" zPosition="12" />
			<eLabel backgroundColor="#00ffff00" position="612,74" size="300,8" zPosition="12" />
			<eLabel backgroundColor="#000000ff" position="915,74" size="300,8" zPosition="12" />
			<widget backgroundColor="#f23d21" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_red" position="10,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
			<widget backgroundColor="#389416" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_green" position="310,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
			<widget backgroundColor="#e6bd00" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_yellow" position="610,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
			<widget backgroundColor="#0064c7" font="Regular;30" foregroundColor="#ffffff" halign="center" name="key_blue" position="910,5" shadowColor="#000000" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
			<widget font="Regular;34" halign="right" position="1239,5" render="Label" size="400,70" source="global.CurrentTime" valign="center">
				<convert type="ClockToText">Date</convert>
			</widget>
			<widget font="Regular;34" halign="right" position="1650,5" render="Label" size="120,70" source="global.CurrentTime" valign="center">
				<convert type="ClockToText">Default</convert>
			</widget>
			<eLabel backgroundColor="#aaaaaa" position="10,75" size="1780,1" />
			<widget name="preview" position="1411,504" scale="aspect" size="467,302" zPosition="5" />
			<widget font="Regular;30" itemHeight="40" name="list" position="5,105" scrollbarMode="showOnDemand" size="1387,880" transparent="1" />
		</screen>
		"""

	def __init__(self, session):

		logger.info("...")
		Screen.__init__(self, session)
		self["list"] = List()
		self["actions"] = ActionMap(
			["OkCancelActions", "SetupActions", "ColorActions", "MenuActions", "EPGSelectActions"],
			{
				"menu":     self.openConfigScreen,  # openContextMenu,
				"cancel":   self.exit,
				"red":      self.exit,
				"green":    self.green,
				"info":     self.infoAb,

				"left": self.keyLeft,
				"down": self.keyDown,
				"up": self.keyUp,
				"right": self.keyRight,
			},
			-1
		)

		# self.onChangedEntry = []
		self.current_preview_path = None
		self.last_picon_set = config.plugins.piconcockpit.last_picon_set.value
		self.setTitle(_("PiconCockpit"))
		# self["list"].onSelectionChanged.append(self.onSelectionChanged)
		self["preview"] = Pixmap()
		self["key_green"] = Button(_("Download"))
		self["key_red"] = Button(_("Exit"))
		self["key_yellow"] = Button()
		self["key_blue"] = Button()
		self.first_start = True
		self.onLayoutFinish.append(self.__onLayoutFinish)

	def move(self, direction):
		self['list'].instance.moveSelection(direction)
		self.createList(True)

	def keyUp(self):
		self.move(self['list'].instance.moveUp)

	def keyDown(self):
		self.move(self['list'].instance.moveDown)

	def keyLeft(self):
		self.move(self['list'].instance.pageUp)

	def keyRight(self):
		self.move(self['list'].instance.pageDown)

	def __onLayoutFinish(self):
		logger.info("...")
		self.picon_dir = config.usage.picon_dir.value
		if not exists(self.picon_dir):
			createDirectory(self.picon_dir)
		if self.first_start:
			self.first_start = False
			self.getPiconSetInfo()
		else:
			self.createList(False)

	def getPiconSetInfo(self):
		logger.info("...")
		url = join(config.plugins.piconcockpit.picon_server.value, "picons", picon_info_file)
		download_file = join(self.picon_dir, picon_info_file)

		if isinstance(url, bytes):
			url = url.decode('utf-8')
		if isinstance(download_file, bytes):
			download_file = download_file.decode('utf-8')

		logger.debug("url: %s, download_file: %s", url, download_file)

		try:
			from twisted.internet import reactor
			reactor.callInThread(
				self.threadDownloadFile,
				url,
				download_file,
				self.gotPiconSetInfo,
				self.downloadError
			)
		except Exception as e:
			logger.error("Error in getPiconSetInfo: %s", str(e))
			self.downloadError(e, url)

	def threadDownloadFile(self, url, destination, success_callback, error_callback):
		try:
			logger.debug("Starting download from %s to %s", url, destination)
			makedirs(dirname(destination), exist_ok=True)
			response = requests.get(url, stream=True, timeout=(3.05, 6))
			response.raise_for_status()

			with open(destination, 'wb') as f:
				for chunk in response.iter_content(chunk_size=8192):
					if chunk:
						f.write(chunk)

			logger.debug("Download completed successfully")
			reactor.callFromThread(success_callback, destination)

		except RequestException as e:
			logger.error("Download failed: %s", str(e))
			reactor.callFromThread(error_callback, e, url)
		except Exception as e:
			logger.error("Unexpected error: %s", str(e))
			reactor.callFromThread(error_callback, e, url)

	def gotPiconSetInfo(self, result):
		logger.info("Download complete: %s", result)
		self.createList(True)

	def downloadError(self, error, url):
		logger.error("Download failed for %s: %s", url, str(error))
		self.session.open(
			MessageBox,
			_("Download failed: %s") % str(error),
			type=MessageBox.TYPE_ERROR
		)

	def openConfigScreen(self):
		logger.info("...")
		picon_set = self["list"].getCurrent()
		if picon_set:
			self.last_picon_set = picon_set[4]
		self.session.openWithCallback(self.openConfigScreenCallback, ConfigScreen, config.plugins.piconcockpit)

	def infoAb(self):
		try:
			from .Version import PLUGIN, VERSION, COPYRIGHT, LICENSE
			about_text = (
				_("Plugin") + ": " + PLUGIN + "\n\n" +
				_("Versione") + ": " + VERSION + "\n\n" +
				_("Copyright") + ": " + COPYRIGHT + "\n\n" +
				_("Licenza") + ": " + LICENSE
			)

			self.session.open(
				MessageBox,
				about_text,
				MessageBox.TYPE_INFO,
				timeout=10
			)
		except Exception as e:
			logger.error("Errore nell'apertura delle informazioni: %s", str(e))
			self.session.open(
				MessageBox,
				_("Informazioni sul plugin non disponibili"),
				MessageBox.TYPE_ERROR,
				timeout=5
			)

	def openConfigScreenCallback(self, _result=None):
		logger.info("...")
		self.first_start = True
		self.__onLayoutFinish()

	def exit(self):
		logger.info("...")
		self['list'].onSelectionChanged = []
		picon_set = self["list"].getCurrent()
		if picon_set:
			logger.debug("last_picon_set: %s", picon_set[4])
			config.plugins.piconcockpit.last_picon_set.value = picon_set[4]
			config.plugins.piconcockpit.last_picon_set.save()
			configfile.save()
			popen("rm /tmp/*.png")
		self.close()

	def green(self):
		picon_set = self["list"].getCurrent()
		logger.debug("picon_set: %s", str(picon_set))
		if picon_set:
			try:
				url = join(picon_set[1], picon_list_file)
				download_file = join(self.picon_dir, picon_list_file)

				if isinstance(url, bytes):
					url = url.decode('utf-8')
				if isinstance(download_file, bytes):
					download_file = download_file.decode('utf-8')
				logger.debug("url: %s, download_file: %s", url, download_file)
				reactor.callInThread(
					self.threadDownloadFile,
					url,
					download_file,
					lambda result=None: self.downloadPicons(download_file, picon_set),
					lambda error, url=url: self.downloadError(error, url)
				)
			except Exception as e:
				logger.error("Error in green(): %s", str(e))
				self.session.open(
					MessageBox,
					_("Failed to start download: %s") % str(e),
					type=MessageBox.TYPE_ERROR
				)

	def listBouquetServices(self):
		logger.info("...")
		bouquets = getTVBouquets()
		bouquets += getRadioBouquets()
		logger.debug("bouquets: %s", bouquets)
		services = []
		for bouquet in bouquets:
			if "Last Scanned" not in bouquet[1]:
				services += getServiceList(bouquet[0])
		logger.debug("services: %s", services)
		return services

	def getUserBouquetPicons(self):
		logger.info("...")
		picons = []
		services = self.listBouquetServices()
		for service in services:
			logger.debug("service: %s", service)
			ref = service[0]
			ref = ref.replace(":", "_")
			ref = ref[:len(ref) - 1]
			picon = ref + ".png"
			logger.debug("picon: %s", picon)
			if picon.startswith("1_"):
				picons.append(picon)
			else:
				logger.debug("skipping picon: %s", picon)
		return picons

	def onSelectionChanged(self):
		logger.info("...")
		self.downloadPreview()

	def downloadPicons(self, _result=None, picon_set=None):
		logger.info("...")
		if config.plugins.piconcockpit.all_picons.value:
			picons = readFile(join(self.picon_dir, picon_list_file)).splitlines()
		else:
			picons = self.getUserBouquetPicons()
		logger.debug("picons: %s", picons)
		if picons:
			if config.plugins.piconcockpit.delete_before_download:
				popen("rm " + join(self.picon_dir, "*.png"))
			self.session.open(PiconDownloadProgress, picon_set[1], picons, self.picon_dir)

	def createList(self, fill):
		logger.info("fill: %s", fill)
		self['list'].onSelectionChanged = []
		self["preview"].hide()
		picon_list = []
		# start_index = -1
		if fill:
			try:
				picon_set_list = readFile(join(self.picon_dir, picon_info_file)).splitlines()
				self.parseSettingsOptions(picon_set_list)
				picon_list = self.parsePiconSetList(picon_set_list)
				picon_list.sort(key=lambda x: x[0])
				for i, picon_set in enumerate(picon_list):
					picon_set = picon_set[0]
					if picon_set[4] == self.last_picon_set:
						# start_index = i
						break
			except Exception as e:
				logger.error("Error creating list: %s", str(e))

		self["list"].setList(picon_list)
		self['list'].onSelectionChanged.append(self.onSelectionChanged)
		"""
		if start_index >= 0:
			self["list"].moveToIndex(start_index)
		"""
		self.onSelectionChanged()

	def parseSettingsOptions(self, picon_set_list):
		logger.info("...")
		size_list = {"all"}
		bit_list = {"all"}
		creator_list = {"all"}
		satellite_list = {"all"}
		for picon_set in picon_set_list:
			if not picon_set.startswith('<meta'):
				info_list = picon_set.split(';')
				if len(info_list) >= 9:
					satellite_list.add(info_list[4])
					creator_list.add(info_list[5])
					bit_list.add(info_list[6].replace(' ', '').lower().replace('bit', ' bit'))
					size_list.add(info_list[7].replace(' ', '').lower())
		if picon_set_list:
			ConfigInit(list(size_list), list(bit_list), list(creator_list), list(satellite_list))

	def parsePiconSetList(self, picon_set_list):
		logger.info("...")
		logger.debug("last_picon_set: %s", config.plugins.piconcockpit.last_picon_set.value)
		picon_list = []
		for picon_set in picon_set_list:
			if not picon_set.startswith('<meta'):
				info_list = picon_set.split(';')
				if len(info_list) >= 9:
					dir_url = join(config.plugins.piconcockpit.picon_server.value, info_list[0])
					pic_url = join(config.plugins.piconcockpit.picon_server.value, info_list[0], info_list[1])
					date = info_list[2]
					name = info_list[3]
					satellite = info_list[4]
					creator = info_list[5]
					bit = (info_list[6].replace(' ', '').lower()).replace('bit', ' bit')
					size = info_list[7].replace(' ', '').lower()
					uploader = info_list[8]
					identifier = str(uuid.uuid4())
					signature = "%s | %s - %s | %s | %s | %s" % (satellite, creator, name, size, bit, uploader)
					name = signature + " | %s" % date
					if config.plugins.piconcockpit.satellite.value in ["all", satellite] and\
							config.plugins.piconcockpit.creator.value in ["all", creator] and\
							config.plugins.piconcockpit.size.value in ["all", size] and\
							config.plugins.piconcockpit.bit.value in ["all", bit]:
						picon_list.append(((name, dir_url, pic_url, identifier, signature), ))
		# logger.debug("picon_list: %s", picon_list)
		return picon_list

	def downloadPreview(self):
		logger.info("...")
		self["preview"].hide()
		current_item = self['list'].getCurrent()
		if not current_item:
			return

		logger.debug("current: %s", current_item)
		url = current_item[2]
		if isinstance(url, bytes):
			url = url.decode('utf-8')

		print('current_item=', current_item)

		if isinstance(url, bytes):
			url = url.decode('utf-8')
		url = url.replace(" ", "%20") if url else ""

		if not url or not isinstance(url, str):
			logger.error("URL non valido: %s", url)
			return

		print('url=', url)

		picon_filename = f"{hash(url)}.png"
		picon_path = join("/tmp", picon_filename)

		# DEBUG - Verifica se il file esiste
		logger.debug("Verifico se esiste: %s", picon_path)
		if exists(picon_path):
			logger.debug("Trovato file esistente, mostro preview")
			self.showPreview(picon_path)
			return

		logger.debug("Avvio download...")
		reactor.callInThread(
			self._downloadPicon,
			url,
			picon_path
		)

	def _downloadPicon(self, url, picon_path):
		try:
			self.removeAllPng()

			makedirs(dirname(picon_path), exist_ok=True)
			response = requests.get(url, stream=True, timeout=20)
			response.raise_for_status()

			temp_path = f"{picon_path}.download"
			with open(temp_path, 'wb') as f:
				for chunk in response.iter_content(8192):  # Buffer più grande
					if chunk:  # Filtra keep-alive chunks
						f.write(chunk)

			if exists(temp_path):
				rename(temp_path, picon_path)
				reactor.callFromThread(self.showPreview, picon_path)
			else:
				raise Exception("Download file not created")

		except requests.exceptions.RequestException as e:
			logger.error(f"Download error: {str(e)}")
			fallback = "/usr/lib/enigma2/python/Plugins/Extensions/PiconCockpit/3.png"
			reactor.callFromThread(self.showPreview, fallback)
		except Exception as e:
			logger.error(f"Unexpected error: {str(e)}")
			fallback = "/usr/lib/enigma2/python/Plugins/Extensions/PiconCockpit/3.png"
			reactor.callFromThread(self.showPreview, fallback)

	def showPreview(self, path):
		fallback_path = "/usr/lib/enigma2/python/Plugins/Extensions/PiconCockpit/3.png"

		if not path or not exists(path):
			path = fallback_path

		logger.info("Mostro anteprima: %s", path)
		try:
			pixmap = LoadPixmap(path, cached=False)
			if pixmap:
				self["preview"].instance.setPixmap(pixmap)
				self["preview"].show()
			else:
				logger.error("Pixmap non valida da %s", path)
				self.showPreview(fallback_path)
		except Exception as e:
			logger.error("Errore caricamento preview: %s", str(e))
			self.showPreview(fallback_path)

	def removeAllPng(self):
		try:
			for png_file in glob.glob('/tmp/*.png'):
				try:
					remove(png_file)
					logger.debug("Rimosso: %s", png_file)
				except OSError as e:
					logger.warning("Errore rimozione %s: %s", png_file, str(e))
		except Exception as e:
			logger.error("Errore pulizia file PNG: %s", str(e))
