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

from sys import stdout
import logging

from Components.config import config, ConfigSubsection, ConfigSelection

from .Version import ID, PLUGIN


logger = None
streamer = None
format_string = ID + ": " + "%(levelname)s: %(filename)s: %(funcName)s: %(message)s"
log_levels = {"ERROR": logging.ERROR, "INFO": logging.INFO, "DEBUG": logging.DEBUG}
plugin = PLUGIN.lower()


if not hasattr(config.plugins, 'piconcockpit'):
	config.plugins.piconcockpit = ConfigSubsection()


log_levels = {
	"ERROR": logging.ERROR,
	"INFO": logging.INFO,
	"DEBUG": logging.DEBUG
}

config.plugins.piconcockpit.debug_log_level = ConfigSelection(
	default="INFO",
	choices=[(k, k) for k in log_levels]
)


logger = None
streamer = None
ID = "PiconCockpit"
format_string = "%(name)s %(levelname)s: %(message)s"


def initLogging():
	global logger, streamer

	if not logger:
		logger = logging.getLogger(ID)
		formatter = logging.Formatter(format_string)
		streamer = logging.StreamHandler(stdout)
		streamer.setFormatter(formatter)
		logger.addHandler(streamer)
		logger.propagate = False

		try:
			level = config.plugins.piconcockpit.debug_log_level.value
			logger.setLevel(log_levels[level])
			logger.info("Logger inizializzato a livello: %s", level)
		except Exception as e:
			logger.setLevel(logging.INFO)
			logger.error("Errore inizializzazione logger: %s", str(e))


def setLogLevel():
	level_name = config.plugins.piconcockpit.debug_log_level.value
	level = log_levels[level_name]
	logger.setLevel(level)
	streamer.setLevel(level)
	logger.log(level, "Livello log impostato a: %s", level_name)
