#! /usr/bin/env python
"""
This page is in the table of contents.
Preface converts the svg slices into gcode extrusion layers, optionally prefaced with some gcode commands.

The preface manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Preface

==Settings==
===Meta===
Default is empty.

The 'Meta' field is to add meta tags or a note to all your files.  Whatever is in that field will be added in a meta tagged line to the output.

===Name of Alteration Files===
Preface looks for alteration files in the alterations folder in the .skeinforge folder in the home directory.  Preface does not care if the text file names are capitalized, but some file systems do not handle file name cases properly, so to be on the safe side you should give them lower case names.  If it doesn't find the file it then looks in the alterations folder in the skeinforge_plugins folder.

====Name of End File====
Default is end.gcode.

If there is a file with the name of the "Name of End File" setting, it will be added to the very end of the gcode.

====Name of Start File====
Default is start.gcode.

If there is a file with the name of the "Name of Start File" setting, it will be added to the very beginning of the gcode.

===Set Positioning to Absolute===
Default is on.

When selected, preface will add the G90 command to set positioning to absolute.

===Set Units to Millimeters===
Default is on.

When selected, preface will add the G21 command to set the units to millimeters.

===Start at Home===
Default is off.

When selected, the G28 go to home gcode will be added at the beginning of the file.

===Turn Extruder Off===
====Turn Extruder Off at Shut Down====
Default is on.

When selected, the M103 turn extruder off gcode will be added at the end of the file.

====Turn Extruder Off at Start Up====
Default is on.

When selected, the M103 turn extruder off gcode will be added at the beginning of the file.

==Examples==
The following examples preface the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and preface.py.

> python preface.py
This brings up the preface dialog.

> python preface.py Screw Holder Bottom.stl
The preface tool is parsing the file:
Screw Holder Bottom.stl
..
The preface tool has created the file:
.. Screw Holder Bottom_preface.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from datetime import date
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.svg_reader import SVGReader
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, text='', repository = None ):
	"""Preface and convert an svg file or text."""
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText( text, repository = None ):
	"""Preface and convert an svg text."""
	if gcodec.isProcedureDoneOrFileIsEmpty( text, 'preface'):
		return text
	if repository is None:
		repository = settings.getReadRepository(PrefaceRepository())
	return PrefaceSkein().getCraftedGcode(repository, text)

def getNewRepository():
	"""Get new repository."""
	return PrefaceRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"""Preface the carving of a gcode file."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'preface', shouldAnalyze)


class PrefaceRepository:
	"""A class to handle the preface settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.preface.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Preface', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Preface')
		self.meta = settings.StringSetting().getFromValue('Meta:', self, '')
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Name of Alteration Files -', self )
		self.nameOfEndFile = settings.StringSetting().getFromValue('Name of End File:', self, 'end.gcode')
		self.nameOfStartFile = settings.StringSetting().getFromValue('Name of Start File:', self, 'start.gcode')
		settings.LabelSeparator().getFromRepository(self)
		self.setPositioningToAbsolute = settings.BooleanSetting().getFromValue('Set Positioning to Absolute', self, True )
		self.setUnitsToMillimeters = settings.BooleanSetting().getFromValue('Set Units to Millimeters', self, True )
		self.startAtHome = settings.BooleanSetting().getFromValue('Home before Print', self, False )
		self.resetExtruder = settings.BooleanSetting().getFromValue('Reset Extruder before Print', self, True )
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Preface'

	def execute(self):
		"""Preface button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class PrefaceSkein:
	"""A class to preface a skein of extrusions."""
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.extruderActive = False
		self.lineIndex = 0
		self.oldLocation = None
		self.svgReader = SVGReader()



	def addFromUpperLowerFile(self, fileName):
		"""Add lines of text from the fileName or the lowercase fileName, if there is no file by the original fileName in the directory."""
		self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(settings.getLinesInAlterationsOrGivenDirectory(fileName))

	def addInitializationToOutput(self):
		"""Add initialization gcode to the output."""
		self.addFromUpperLowerFile(self.repository.nameOfStartFile.value) # Add a start file if it exists.
		self.distanceFeedRate.addTagBracketedLine('creation', 'skeinforge') # GCode formatted comment
		absoluteFilePathUntilDot = os.path.abspath(__file__)[: os.path.abspath(__file__).rfind('.')]
		if absoluteFilePathUntilDot == '/home/enrique/Desktop/backup/babbleold/script/reprap/fabmetheus/skeinforge_application/skeinforge_plugins/craft_plugins/preface': #is this script on Enrique's computer?
			archive.writeFileText(archive.getVersionFileName(), date.today().isoformat().replace('-', '.')[2 :])
		versionText = archive.getFileText(archive.getVersionFileName())
		self.distanceFeedRate.addTagBracketedLine('version', versionText) # GCode formatted comment
		self.distanceFeedRate.addLine('(<extruderInitialization>)') # GCode formatted comment
		if self.repository.setPositioningToAbsolute.value:
			self.distanceFeedRate.addLine('G90 ;set positioning to absolute') # Set positioning to absolute.
		if self.repository.setUnitsToMillimeters.value:
			self.distanceFeedRate.addLine('G21 ;set units to millimeters') # Set units to millimeters.
		if self.repository.startAtHome.value:
			self.distanceFeedRate.addLine('G28 ;start at home') # Start at home.
		if self.repository.resetExtruder.value:
			self.distanceFeedRate.addLine('G92 E0 ;reset extruder distance') # Start at home.
		craftTypeName = skeinforge_profile.getCraftTypeName()
		self.distanceFeedRate.addTagBracketedLine('craftTypeName', craftTypeName)
		self.distanceFeedRate.addTagBracketedLine('decimalPlacesCarried', self.distanceFeedRate.decimalPlacesCarried)
		layerThickness = float(self.svgReader.sliceDictionary['layerThickness'])
		self.distanceFeedRate.addTagRoundedLine('layerThickness', layerThickness)
		if self.repository.meta.value:
			self.distanceFeedRate.addTagBracketedLine('meta', self.repository.meta.value)
		perimeterWidth = float(self.svgReader.sliceDictionary['perimeterWidth'])
		self.distanceFeedRate.addTagRoundedLine('perimeterWidth', perimeterWidth)
		self.distanceFeedRate.addTagBracketedLine('profileName', skeinforge_profile.getProfileName(craftTypeName))
		procedureNames = self.svgReader.sliceDictionary['procedureName'].replace(',', ' ').split()
		for procedureName in procedureNames:
			self.distanceFeedRate.addTagBracketedLine('procedureName', procedureName)
		self.distanceFeedRate.addTagBracketedLine('procedureName', 'preface')
		self.distanceFeedRate.addLine('(</extruderInitialization>)') # Initialization is finished, extrusion is starting.
		self.distanceFeedRate.addLine('(<crafting>)') # Initialization is finished, crafting is starting.

	def addPreface( self, rotatedLoopLayer ):
		"""Add preface to the carve layer."""
		self.distanceFeedRate.addLine('(<layer> %s )' % rotatedLoopLayer.z ) # Indicate that a new layer is starting.
		if rotatedLoopLayer.rotation is not None:
			self.distanceFeedRate.addTagBracketedLine('bridgeRotation', str( rotatedLoopLayer.rotation ) ) # Indicate the bridge rotation.
		for loop in rotatedLoopLayer.loops:
			self.distanceFeedRate.addGcodeFromLoop(loop, rotatedLoopLayer.z)
		self.distanceFeedRate.addLine('(</layer>)')

	def getCraftedGcode( self, repository, gcodeText ):
		"""Parse gcode text and store the bevel gcode."""
		self.repository = repository
		self.svgReader.parseSVG('', gcodeText)
		if self.svgReader.sliceDictionary is None:
			print('Warning, nothing will be done because the sliceDictionary could not be found getCraftedGcode in preface.')
			return ''
		self.distanceFeedRate.decimalPlacesCarried = int(self.svgReader.sliceDictionary['decimalPlacesCarried'])
		self.addInitializationToOutput()
		for rotatedLoopLayerIndex, rotatedLoopLayer in enumerate(self.svgReader.rotatedLoopLayers):
			settings.printProgressByNumber(rotatedLoopLayerIndex, len(self.svgReader.rotatedLoopLayers), 'preface')
			self.addPreface( rotatedLoopLayer )
		return self.distanceFeedRate.output.getvalue()


def main():
	"""Display the preface dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == "__main__":
	main()
