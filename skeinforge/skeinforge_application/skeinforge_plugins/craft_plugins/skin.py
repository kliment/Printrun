"""
This page is in the table of contents.
Skin is a script to smooth the surface skin as described at:
http://adventuresin3-dprinting.blogspot.com/2011/05/skinning.html

The skin manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skin


==Operation==
The default 'Activate Skin' checkbox is off.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Examples==
The following examples skin the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and skin.py.

> python skin.py
This brings up the skin dialog.

> python skin.py Screw Holder Bottom.stl
The skin tool is parsing the file:
Screw Holder Bottom.stl
..
The skin tool has created the file:
.. Screw Holder Bottom_skin.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.

import __init__
import math

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, gcodeText, repository=None):
	"""Skin a gcode linear move text."""
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, gcodeText), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"""Skin a gcode linear move text."""
	if gcodec.isProcedureDoneOrFileIsEmpty(gcodeText, 'skin'):
		return gcodeText
	if repository is None:
		repository = settings.getReadRepository(SkinRepository())
	if not repository.activateSkin.value:
		return gcodeText
	return SkinSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	"""Get new repository."""
	return SkinRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"""Skin a gcode linear move file.  Chain skin the gcode if it is not already skinned."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'skin', shouldAnalyze)


class SkinRepository:
	"""A class to handle the skin settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.skin.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Skin', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Skin')
		self.activateSkin = settings.BooleanSetting().getFromValue('Activate Skin: this is experimental.  \nIt prints the perimeters and loops only at half the layer height that is specified under carve.', self, False )
		self.clipOverPerimeterWidth = settings.FloatSpin().getFromValue(0.50, 'Clip Over Perimeter Width (scaler):', self, 1.50, 1.00)
		self.layersFrom = settings.IntSpin().getSingleIncrementFromValue(0, 'Do Not Skin the first ... Layers:', self, 912345678, 3)
		self.executeTitle = 'Skin'

	def execute(self):
		"""Skin button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class SkinSkein:
	"""A class to skin a skein of extrusions."""
	def __init__(self):
		"""Initialize."""
		self.boundaryLayerIndex = -1
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = 959.0
		self.lineIndex = 0
		self.lines = None
		self.oldFlowRate = None
		self.oldLocation = None
		self.perimeter = None
		self.travelFeedRateMinute = 957.0

	def addFlowRateLine(self, flowRate):
		"""Add a flow rate line."""
		self.distanceFeedRate.addLine('M108 S' + euclidean.getFourSignificantFigures(flowRate))

	def addPerimeterLoop(self, thread, z):
		"""Add the perimeter loop to the gcode."""
		self.distanceFeedRate.addGcodeFromFeedRateThreadZ(self.feedRateMinute, thread, self.travelFeedRateMinute, z)

	def addSkinnedPerimeter(self):
		"""Add skinned perimeter."""
		if self.perimeter is None:
			return
		self.perimeter = self.perimeter[: -1]
		innerPerimeter = intercircle.getLargestInsetLoopFromLoop(self.perimeter, self.quarterPerimeterWidth)
		innerPerimeter = self.getClippedSimplifiedLoopPathByLoop(innerPerimeter)
		outerPerimeter = intercircle.getLargestInsetLoopFromLoop(self.perimeter, -self.quarterPerimeterWidth)
		outerPerimeter = self.getClippedSimplifiedLoopPathByLoop(outerPerimeter)
		lowerZ = self.oldLocation.z - self.quarterLayerThickness
		higherZ = self.oldLocation.z + self.quarterLayerThickness
		self.addFlowRateLine(0.25 * self.oldFlowRate)
		self.addPerimeterLoop(innerPerimeter, lowerZ)
		self.addPerimeterLoop(outerPerimeter, lowerZ)
		self.addPerimeterLoop(innerPerimeter, higherZ)
		self.addPerimeterLoop(outerPerimeter, higherZ)
		self.addFlowRateLine(self.oldFlowRate)

	def getClippedSimplifiedLoopPathByLoop(self, loop):
		"""Get clipped and simplified loop path from a loop."""
		loopPath = loop + [loop[0]]
		return euclidean.getClippedSimplifiedLoopPath(self.clipLength, loopPath, self.halfPerimeterWidth)

	def getCraftedGcode( self, gcodeText, repository ):
		"""Parse gcode text and store the skin gcode."""
		self.lines = archive.getTextLines(gcodeText)
		self.repository = repository
		self.parseInitialization()
		for self.lineIndex in xrange(self.lineIndex, len(self.lines)):
			line = self.lines[self.lineIndex]
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		"""Parse gcode initialization and store the parameters."""
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addLine('(<procedureName> skin </procedureName>)')
				return
			elif firstWord == '(<layerThickness>':

				self.quarterLayerThickness = 0.25 * float(splitLine[1])
			elif firstWord == '(<operatingFlowRate>':
				self.oldFlowRate = float(splitLine[1])
			elif firstWord == '(<perimeterWidth>':
				perimeterWidth = float(splitLine[1])
				self.halfPerimeterWidth = 0.5 * perimeterWidth
				self.quarterPerimeterWidth = 0.25 * perimeterWidth
				self.clipLength = (self.quarterLayerThickness - (self.repository.clipOverPerimeterWidth.value * self.quarterLayerThickness * (math.pi/4)))*4
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"""Parse a gcode line and add it to the skin skein."""
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPerimeter>)':
			self.boundaryLayerIndex = max(0, self.boundaryLayerIndex)
		elif firstWord == 'G1':
			self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			self.oldLocation = location
			if self.perimeter is not None:
				self.perimeter.append(location.dropAxis())
				return
		elif firstWord == '(<layer>':
			if self.boundaryLayerIndex > -1:
				self.boundaryLayerIndex += 1
		elif firstWord == 'M101' or firstWord == 'M103':
			if self.perimeter is not None:
				return
		elif firstWord == 'M108':
			self.oldFlowRate = gcodec.getDoubleAfterFirstLetter(splitLine[1])
		elif firstWord == '(<perimeter>':
			if self.boundaryLayerIndex >= self.repository.layersFrom.value:
				self.perimeter = []
		elif firstWord == '(</perimeter>)':
			self.addSkinnedPerimeter()
			self.perimeter = None
		self.distanceFeedRate.addLine(line)


def main():
	"""Display the skin dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
