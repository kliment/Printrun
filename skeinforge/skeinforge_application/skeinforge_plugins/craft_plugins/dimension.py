#! /usr/bin/env python
"""
This page is in the table of contents.
Dimension adds Adrian's extruder distance E value to the gcode movement lines, as described at:
http://blog.reprap.org/2009/05/4d-printing.html

and in Erik de Bruijn's conversion script page at:
http://objects.reprap.org/wiki/3D-to-5D-Gcode.php

The dimension manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Dimension

Nophead wrote an excellent article on how to set the filament parameters:
http://hydraraptor.blogspot.com/2011/03/spot-on-flow-rate.html

==Operation==
The default 'Activate Dimension' checkbox is off.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Extrusion Distance Format Choice===
Default is 'Absolute Extrusion Distance' because in Adrian's description the distance is absolute.  In future, because the relative distances are smaller than the cumulative absolute distances, hopefully the firmaware will be able to use relative distance.

====Absolute Extrusion Distance====
When selected, the extrusion distance output will be the total extrusion distance to that gcode line.

====Relative Extrusion Distance====
When selected, the extrusion distance output will be the extrusion distance from the last gcode line.

===Extruder Retraction Speed===
Default is 13.3 mm/s.

Defines the extruder retraction feed rate.

===Filament===
====Filament Diameter====
Default is 2.8 millimeters.

Defines the filament diameter.

====Filament Packing Density====
Default is 0.85.  This is for ABS.

Defines the effective filament packing density.

The default value is so low for ABS because ABS is relatively soft and with a pinch wheel extruder the teeth of the pinch dig in farther, so it sees a smaller effective diameter.  With a hard plastic like PLA the teeth of the pinch wheel don't dig in as far, so it sees a larger effective diameter, so feeds faster, so for PLA the value should be around 0.97.  This is with Wade's hobbed bolt.  The effect is less significant with larger pinch wheels.

Overall, you'll have to find the optimal filament packing density by experiment.

===Retraction Distance===
Default is zero.

Defines the retraction distance when the thread ends.

===Restart Extra Distance===
Default is zero.

Defines the restart extra distance when the thread restarts.  The restart distance will be the retraction distance plus the restart extra distance.

==Examples==
The following examples dimension the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and dimension.py.

> python dimension.py
This brings up the dimension dialog.

> python dimension.py Screw Holder Bottom.stl
The dimension tool is parsing the file:
Screw Holder Bottom.stl
..
The dimension tool has created the file:
.. Screw Holder Bottom_dimension.gcode

"""

#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	"""Dimension a gcode file or text."""
	return getCraftedTextFromText( archive.getTextIfEmpty(fileName, gcodeText), repository )

def getCraftedTextFromText(gcodeText, repository=None):
	"""Dimension a gcode text."""
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'dimension'):
		return gcodeText
	if repository is None:
		repository = settings.getReadRepository( DimensionRepository() )
	if not repository.activateDimension.value:
		return gcodeText
	return DimensionSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	"""Get new repository."""
	return DimensionRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"""Dimension a gcode file."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'dimension', shouldAnalyze)


class DimensionRepository:
	"""A class to handle the dimension settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.dimension.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Dimension', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Dimension')
		self.activateDimension = settings.BooleanSetting().getFromValue('Activate Volumetric Extrusion (Stepper driven Extruders)', self, True )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Filament Settings - YOU NEED TO HAVE YOUR EXTRUDER CALIBRATED FIRST -', self )
		settings.LabelDisplay().getFromName('http://josefprusa.cz/skeinforge-40-volumetric-calibration', self )
		settings.LabelSeparator().getFromRepository(self)		
		self.filamentDiameter = settings.FloatSpin().getFromValue(1.5, 'Filament Diameter (mm):', self, 3.5, 2.8)
		self.filamentPackingDensity = settings.FloatSpin().getFromValue(0.7, 'Filament Packing Density (ratio) lower=more extrusion:', self, 1.0, 1.00)
		settings.LabelSeparator().getFromRepository(self)		
		settings.LabelDisplay().getFromName('- Fighting Oooze -', self )
		settings.LabelSeparator().getFromRepository(self)		
		settings.LabelDisplay().getFromName('- Filament Retraction Settings -', self )		
		self.retractionDistance = settings.FloatSpin().getFromValue( 0.00, 'Retraction Distance (millimeters):', self, 3.00, 1.00 )
		self.restartExtraDistance = settings.FloatSpin().getFromValue( -0.50, 'Restart Extra Distance (millimeters):', self, 0.50, 0.00 )
		self.extruderRetractionSpeed = settings.FloatSpin().getFromValue( 5.0, 'Extruder Retraction Speed (mm/s):', self, 50.0, 15.0 )		
		settings.LabelSeparator().getFromRepository(self)		
		settings.LabelDisplay().getFromName('- When to retract ? -', self )
		self.retractWhenCrossing = settings.BooleanSetting().getFromValue('Force to retract when crossing over spaces', self, True)
		self.minimumExtrusionForRetraction = settings.FloatSpin().getFromValue(0.0, 'Minimum Extrusion before Retraction (millimeters):', self, 2.0, 1.0)
		self.minimumTravelForRetraction = settings.FloatSpin().getFromValue(0.0, 'Minimum Travelmove after Retraction (millimeters):', self, 2.0, 1.0)
		settings.LabelSeparator().getFromRepository(self)		
		settings.LabelDisplay().getFromName('- Firmware Related Stuff -', self )
		extrusionDistanceFormatLatentStringVar = settings.LatentStringVar()
		self.extrusionDistanceFormatChoiceLabel = settings.LabelDisplay().getFromName('Extrusion Values should be: ', self )
		settings.Radio().getFromRadio( extrusionDistanceFormatLatentStringVar, 'in Absolute units (Sprinter, FiveD a.o.)', self, True )
		self.relativeExtrusionDistance = settings.Radio().getFromRadio( extrusionDistanceFormatLatentStringVar, 'in Relative units (Teacup a.o.)', self, False )
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Dimension'

	def execute(self):
		"""Dimension button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class DimensionSkein:
	"""A class to dimension a skein of extrusions."""
	def __init__(self):
		"""Initialize."""
		self.absoluteDistanceMode = True
		self.boundaryLayers = []
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.feedRateMinute = None
		self.isExtruderActive = False
		self.layerIndex = -1
		self.lineIndex = 0
		self.maximumZTravelFeedRatePerSecond = None
		self.oldLocation = None
		self.operatingFlowRate = None
		self.retractionRatio = 1.0
		self.totalExtrusionDistance = 0.0
		self.travelFeedRatePerSecond = None
		self.zDistanceRatio = 5.0

	def addLinearMoveExtrusionDistanceLine( self, extrusionDistance ):
		"""Get the extrusion distance string from the extrusion distance."""

		
		self.distanceFeedRate.output.write('G1 F%s\n' % self.extruderRetractionSpeedMinuteString )
		self.distanceFeedRate.output.write('G1%s\n' % self.getExtrusionDistanceStringFromExtrusionDistance( extrusionDistance ) )
		self.distanceFeedRate.output.write('G1 F%s\n' % self.distanceFeedRate.getRounded( self.feedRateMinute ) )
		
	def getCraftedGcode(self, gcodeText, repository):
		"""Parse gcode text and store the dimension gcode."""
		self.repository = repository
		filamentRadius = 0.5 * repository.filamentDiameter.value
		filamentPackingArea = math.pi * filamentRadius * filamentRadius * repository.filamentPackingDensity.value
		self.minimumExtrusionForRetraction = self.repository.minimumExtrusionForRetraction.value
		self.minimumTravelForRetraction = self.repository.minimumTravelForRetraction.value
		self.doubleMinimumTravelForRetraction = self.minimumTravelForRetraction + self.minimumTravelForRetraction
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		if self.repository.retractWhenCrossing.value:
			self.parseBoundaries()
			self.flowScaleSixty = 60.0 * (((self.layerThickness/2)*(self.layerThickness/2)*math.pi)+self.layerThickness*(self.perimeterWidth-self.layerThickness))/filamentPackingArea
		if self.operatingFlowRate is None:
			print('There is no operatingFlowRate so dimension will do nothing.')
			return gcodeText
		self.restartDistance = self.repository.retractionDistance.value + self.repository.restartExtraDistance.value
		self.extruderRetractionSpeedMinuteString = self.distanceFeedRate.getRounded(60.0 * self.repository.extruderRetractionSpeed.value)
		if self.maximumZTravelFeedRatePerSecond is not None and self.travelFeedRatePerSecond is not None:
			self.zDistanceRatio = self.travelFeedRatePerSecond / self.maximumZTravelFeedRatePerSecond
		for lineIndex in xrange(self.lineIndex, len(self.lines)):
			self.parseLine( lineIndex )
		return self.distanceFeedRate.output.getvalue()

	def getDimensionedArcMovement(self, line, splitLine):
		"""Get a dimensioned arc movement."""
		if self.oldLocation is None:
			return line
		relativeLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.oldLocation += relativeLocation
		distance = gcodec.getArcDistance(relativeLocation, splitLine)
		return line + self.getExtrusionDistanceString(distance, splitLine)

	def getDimensionedLinearMovement( self, line, splitLine ):
		"""Get a dimensioned linear movement."""
		distance = 0.0
		if self.absoluteDistanceMode:
			location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
			if self.oldLocation is not None:
				distance = abs( location - self.oldLocation )
			self.oldLocation = location
		else:
			if self.oldLocation is None:
				print('Warning: There was no absolute location when the G91 command was parsed, so the absolute location will be set to the origin.')
#				self.oldLocation = Vector3()
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			distance = abs( location )
			self.oldLocation += location
		return line + self.getExtrusionDistanceString( distance, splitLine )

	def getDistanceToNextThread(self, lineIndex):
		"""Get the travel distance to the next thread."""
		if self.oldLocation is None:
			return None
		isActive = False
		location = self.oldLocation
		for afterIndex in xrange(lineIndex + 1, len(self.lines)):
			line = self.lines[afterIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == 'G1':
				if isActive:
					location = gcodec.getLocationFromSplitLine(location, splitLine)
					if self.repository.retractWhenCrossing.value:
						locationEnclosureIndex = self.getSmallestEnclosureIndex(location.dropAxis())
						if locationEnclosureIndex != self.getSmallestEnclosureIndex(self.oldLocation.dropAxis()):
							return None
					locationMinusOld = location - self.oldLocation
					xyTravel = abs(locationMinusOld.dropAxis())
					zTravelMultiplied = locationMinusOld.z * self.zDistanceRatio
					return math.sqrt(xyTravel * xyTravel + zTravelMultiplied * zTravelMultiplied)
			elif firstWord == 'M101':
				isActive = True
			elif firstWord == 'M103':
				isActive = False
		return None

	def getExtrusionDistanceString( self, distance, splitLine ):
		"""Get the extrusion distance string."""
		self.feedRateMinute = gcodec.getFeedRateMinute( self.feedRateMinute, splitLine )
		if not self.isExtruderActive:
			return ''
		if distance <= 0.0:
			return ''
		scaledFlowRate = self.flowRate * self.flowScaleSixty
		return self.getExtrusionDistanceStringFromExtrusionDistance(scaledFlowRate / self.feedRateMinute * distance)
	def getExtrusionDistanceStringFromExtrusionDistance( self, extrusionDistance ):
		"""Get the extrusion distance string from the extrusion distance."""
		if self.repository.relativeExtrusionDistance.value:
			return ' E' + self.distanceFeedRate.getRounded( extrusionDistance )
		self.totalExtrusionDistance += extrusionDistance
		return ' E' + self.distanceFeedRate.getRounded( self.totalExtrusionDistance )

	
	def getRetractionRatio(self, lineIndex):
		"""Get the retraction ratio."""
		distanceToNextThread = self.getDistanceToNextThread(lineIndex)
		if  self.totalExtrusionDistance <= self.minimumExtrusionForRetraction:
			return self.totalExtrusionDistance/self.minimumExtrusionForRetraction
		if distanceToNextThread is None:
			return 1.0
		if distanceToNextThread >= self.doubleMinimumTravelForRetraction:
			return 1.0
		if distanceToNextThread <= self.minimumTravelForRetraction:
			return 0.0
		return (distanceToNextThread - self.minimumTravelForRetraction) / self.minimumTravelForRetraction

	def getSmallestEnclosureIndex(self, point):
		"""Get the index of the smallest boundary loop which encloses the point."""
		boundaryLayer = self.boundaryLayers[self.layerIndex]
		for loopIndex, loop in enumerate(boundaryLayer.loops):
			if euclidean.isPointInsideLoop(loop, point):
				return loopIndex
		return None

	def parseBoundaries(self):
		"""Parse the boundaries and add them to the boundary layers."""
		boundaryLoop = None
		boundaryLayer = None
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(</boundaryPerimeter>)':
				boundaryLoop = None
			elif firstWord == '(<boundaryPoint>':
				location = gcodec.getLocationFromSplitLine(None, splitLine)
				if boundaryLoop is None:
					boundaryLoop = []
					boundaryLayer.loops.append(boundaryLoop)
				boundaryLoop.append(location.dropAxis())
			elif firstWord == '(<layer>':
				boundaryLayer = euclidean.LoopLayer(float(splitLine[1]))
				self.boundaryLayers.append(boundaryLayer)
		for boundaryLayer in self.boundaryLayers:
			triangle_mesh.sortLoopsInOrderOfArea(False, boundaryLayer.loops)

	def parseInitialization(self):
		"""Parse gcode initialization and store the parameters."""
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addLine('(<procedureName> dimension </procedureName>)')
				return
			elif firstWord == '(<layerThickness>':
				self.layerThickness = float(splitLine[1])
			elif firstWord == '(<maximumZDrillFeedRatePerSecond>':
				self.maximumZTravelFeedRatePerSecond = float(splitLine[1])
			elif firstWord == '(<maximumZTravelFeedRatePerSecond>':
				self.maximumZTravelFeedRatePerSecond = float(splitLine[1])
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.feedRateMinute = 60.0 * float(splitLine[1])
			elif firstWord == '(<operatingFlowRate>':
				self.operatingFlowRate = float(splitLine[1])
				self.flowRate = self.operatingFlowRate
			elif firstWord == '(<perimeterWidth>':
				self.perimeterWidth = float(splitLine[1])
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRatePerSecond = float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine( self, lineIndex ):
		"""Parse a gcode line and add it to the dimension skein."""
		line = self.lines[lineIndex].lstrip()
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G2' or firstWord == 'G3':
			line = self.getDimensionedArcMovement( line, splitLine )
		if firstWord == 'G1':
			line = self.getDimensionedLinearMovement( line, splitLine )
		if firstWord == 'G90':
			self.absoluteDistanceMode = True
		elif firstWord == 'G91':
			self.absoluteDistanceMode = False
		elif firstWord == '(<layer>':
			self.layerIndex += 1
		elif firstWord == 'M101':
			self.addLinearMoveExtrusionDistanceLine(self.restartDistance * self.retractionRatio)
			if not self.repository.relativeExtrusionDistance.value:
				self.distanceFeedRate.addLine('G92 E0')
				self.totalExtrusionDistance = 0.0
			self.isExtruderActive = True
		elif firstWord == 'M103':
			self.retractionRatio = self.getRetractionRatio(lineIndex)
			self.addLinearMoveExtrusionDistanceLine(-self.repository.retractionDistance.value * self.retractionRatio)
			self.isExtruderActive = False
		elif firstWord == 'M108':
			self.flowRate = float( splitLine[1][1 :] )
		self.distanceFeedRate.addLine(line)


def main():
	"""Display the dimension dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == '__main__':
	main()
