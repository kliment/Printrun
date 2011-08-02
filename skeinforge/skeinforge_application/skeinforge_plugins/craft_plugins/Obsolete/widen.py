#! /usr/bin/env python
"""
This page is in the table of contents.
Widen will widen the outside perimeters away from the inside perimeters, so that the outsides will be at least two perimeter widths away from the insides and therefore the outside filaments will not overlap the inside filaments.

For example, if a mug has a very thin wall, widen would widen the outside of the mug so that the wall of the mug would be two perimeter widths wide, and the outside wall filament would not overlap the inside filament.

For another example, if the outside of the object runs right next to a hole, widen would widen the wall around the hole so that the wall would bulge out around the hole, and the outside filament would not overlap the hole filament.

The widen manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Widen

==Operation==
The default 'Activate Widen' checkbox is off.  When it is on, widen will work, when it is off, widen will not be called.

==Examples==
The following examples widen the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and widen.py.

> python widen.py
This brings up the widen dialog.

> python widen.py Screw Holder Bottom.stl
The widen tool is parsing the file:
Screw Holder Bottom.stl
..
The widen tool has created the file:
.. Screw Holder Bottom_widen.gcode

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.geometry_utilities import boolean_solid
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/28/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text='', repository=None):
	"""Widen the preface file or text."""
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"""Widen the preface gcode text."""
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'widen'):
		return gcodeText
	if repository is None:
		repository = settings.getReadRepository( WidenRepository() )
	if not repository.activateWiden.value:
		return gcodeText
	return WidenSkein().getCraftedGcode(gcodeText, repository)

def getIntersectingWithinLoops(loop, loopList, outsetLoop):
	"""Get the loops which are intersecting or which it is within."""
	intersectingWithinLoops = []
	for otherLoop in loopList:
		if getIsIntersectingWithinLoop(loop, otherLoop, outsetLoop):
			intersectingWithinLoops.append(otherLoop)
	return intersectingWithinLoops

def getIsIntersectingWithinLoop(loop, otherLoop, outsetLoop):
	"""Determine if the loop is intersecting or is within the other loop."""
	if euclidean.isLoopIntersectingLoop(loop, otherLoop):
		return True
	return euclidean.isPathInsideLoop(otherLoop, loop) != euclidean.isPathInsideLoop(otherLoop, outsetLoop)

def getIsPointInsideALoop(loops, point):
	"""Determine if a point is inside a loop of a loop list."""
	for loop in loops:
		if euclidean.isPointInsideLoop(loop, point):
			return True
	return False

def getNewRepository():
	"""Get new repository."""
	return WidenRepository()

def getWidenedLoop(loop, loopList, outsetLoop, radius):
	"""Get the widened loop."""
	intersectingWithinLoops = getIntersectingWithinLoops(loop, loopList, outsetLoop)
	if len(intersectingWithinLoops) < 1:
		return loop
	loopsUnified = boolean_solid.getLoopsUnified(radius, [[loop], intersectingWithinLoops])
	if len(loopsUnified) < 1:
		return loop
	return euclidean.getLargestLoop(loopsUnified)

def writeOutput(fileName, shouldAnalyze=True):
	"""Widen the carving of a gcode file."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'widen', shouldAnalyze)


class WidenRepository:
	"""A class to handle the widen settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.widen.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Widen', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute(
			'http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Widen')
		self.activateWiden = settings.BooleanSetting().getFromValue('Activate Widen:', self, False)
		self.executeTitle = 'Widen'

	def execute(self):
		"""Widen button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(
			self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class WidenSkein:
	"""A class to widen a skein of extrusions."""
	def __init__(self):
		self.boundary = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.rotatedLoopLayer = None

	def addWiden(self, rotatedLoopLayer):
		"""Add widen to the layer."""
		triangle_mesh.sortLoopsInOrderOfArea(False, rotatedLoopLayer.loops)
		widdershinsLoops = []
		clockwiseInsetLoops = []
		for loopIndex in xrange(len(rotatedLoopLayer.loops)):
			loop = rotatedLoopLayer.loops[loopIndex]
			if euclidean.isWiddershins(loop):
				otherLoops = rotatedLoopLayer.loops[: loopIndex] + rotatedLoopLayer.loops[loopIndex + 1 :]
				leftPoint = euclidean.getLeftPoint(loop)
				if getIsPointInsideALoop(otherLoops, leftPoint):
					self.distanceFeedRate.addGcodeFromLoop(loop, rotatedLoopLayer.z)
				else:
					widdershinsLoops.append(loop)
			else:
#				clockwiseInsetLoop = intercircle.getLargestInsetLoopFromLoop(loop, self.doublePerimeterWidth)
#				clockwiseInsetLoop.reverse()
#				clockwiseInsetLoops.append(clockwiseInsetLoop)
				clockwiseInsetLoops += intercircle.getInsetLoopsFromLoop(loop, self.doublePerimeterWidth)
				self.distanceFeedRate.addGcodeFromLoop(loop, rotatedLoopLayer.z)
		for widdershinsLoop in widdershinsLoops:
			outsetLoop = intercircle.getLargestInsetLoopFromLoop(widdershinsLoop, -self.doublePerimeterWidth)
			widenedLoop = getWidenedLoop(widdershinsLoop, clockwiseInsetLoops, outsetLoop, self.perimeterWidth)
			self.distanceFeedRate.addGcodeFromLoop(widenedLoop, rotatedLoopLayer.z)

	def getCraftedGcode(self, gcodeText, repository):
		"""Parse gcode text and store the widen gcode."""
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
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
				self.distanceFeedRate.addTagBracketedLine('procedureName', 'widen')
			elif firstWord == '(<crafting>)':
				self.distanceFeedRate.addLine(line)
				return
			elif firstWord == '(<perimeterWidth>':
				self.perimeterWidth = float(splitLine[1])
				self.doublePerimeterWidth = 2.0 * self.perimeterWidth
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"""Parse a gcode line and add it to the widen skein."""
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.boundary.append(location.dropAxis())
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('widen')
			self.rotatedLoopLayer = euclidean.RotatedLoopLayer(float(splitLine[1]))
			self.distanceFeedRate.addLine(line)
		elif firstWord == '(</layer>)':
			self.addWiden( self.rotatedLoopLayer )
			self.rotatedLoopLayer = None
		elif firstWord == '(<nestedRing>)':
			self.boundary = []
			self.rotatedLoopLayer.loops.append( self.boundary )
		if self.rotatedLoopLayer is None or firstWord == '(<bridgeRotation>':
			self.distanceFeedRate.addLine(line)


def main():
	"""Display the widen dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
