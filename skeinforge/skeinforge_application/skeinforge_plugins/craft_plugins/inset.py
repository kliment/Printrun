#! /usr/bin/env python
"""
This page is in the table of contents.
Inset will inset the outside outlines by half the perimeter width, and outset the inside outlines by the same amount.

The inset manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Inset

==Settings==
===Add Custom Code for Temperature Reading===
Default is on.

When selected, the M105 custom code for temperature reading will be added at the beginning of the file.

===Bridge Width Multiplier===
Default is one.

Defines the ratio of the extrusion width of a bridge layer over the extrusion width of the typical non bridge layers.

===Loop Order Choice===
Default loop order choice is 'Ascending Area'.

When overlap is to be removed, for each loop, the overlap is checked against the list of loops already extruded.  If the latest loop overlaps an already extruded loop, the overlap is removed from the latest loop.  The loops are ordered according to their areas.

====Ascending Area====
When selected, the loops will be ordered in ascending area.  With thin walled parts, if overlap is being removed the outside of the container will not be extruded.  Holes will be the correct size.

====Descending Area====
When selected, the loops will be ordered in descending area.  With thin walled parts, if overlap is being removed the inside of the container will not be extruded.  Holes will be missing the interior wall so they will be slightly wider than model size.

===Overlap Removal Width over Perimeter Width===
Default is 0.6.

Defines the ratio of the overlap removal width over the perimeter width.  Any part of the extrusion that comes within the overlap removal width of another is removed.  This is to prevent the extruder from depositing two extrusions right beside each other.  If the 'Overlap Removal Width over Perimeter Width' is less than 0.2, the overlap will not be removed.

===Turn Extruder Heater Off at Shut Down===
Default is on.

When selected, the M104 S0 gcode line will be added to the end of the file to turn the extruder heater off by setting the extruder heater temperature to 0.

==Examples==
The following examples inset the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and inset.py.

> python inset.py
This brings up the inset dialog.

> python inset.py Screw Holder Bottom.stl
The inset tool is parsing the file:
Screw Holder Bottom.stl
..
The inset tool has created the file:
.. Screw Holder Bottom_inset.gcode

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
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAlreadyFilledArounds( alreadyFilledArounds, loop, radius ):
	"""Add already filled loops around loop to alreadyFilledArounds."""
	radius = abs(radius)
	alreadyFilledLoop = []
	slightlyGreaterThanRadius = 1.01 * radius
	muchGreaterThanRadius = 2.5 * radius
	centers = intercircle.getCentersFromLoop( loop, slightlyGreaterThanRadius )
	for center in centers:
		alreadyFilledInset = intercircle.getSimplifiedInsetFromClockwiseLoop( center, radius )
		if intercircle.isLargeSameDirection( alreadyFilledInset, center, radius ):
			alreadyFilledLoop.append( alreadyFilledInset )
	if len( alreadyFilledLoop ) > 0:
		alreadyFilledArounds.append( alreadyFilledLoop )

def addSegmentOutline( isThick, outlines, pointBegin, pointEnd, width ):
	"""Add a diamond or hexagonal outline for a line segment."""
	width = abs( width )
	exclusionWidth = 0.6 * width
	slope = 0.2
	if isThick:
		slope = 3.0
		exclusionWidth = 0.8 * width
	segment = pointEnd - pointBegin
	segmentLength = abs(segment)
	if segmentLength == 0.0:
		return
	normalizedSegment = segment / segmentLength
	outline = []
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	pointBeginRotated = segmentYMirror * pointBegin
	pointEndRotated = segmentYMirror * pointEnd
	along = 0.05
	alongLength = along * segmentLength
	if alongLength > 0.1 * exclusionWidth:
		along *= 0.1 * exclusionWidth / alongLength
	alongEnd = 1.0 - along
	remainingToHalf = 0.5 - along
	alongToWidth = exclusionWidth / slope / segmentLength
	pointBeginIntermediate = euclidean.getIntermediateLocation( along, pointBeginRotated, pointEndRotated )
	pointEndIntermediate = euclidean.getIntermediateLocation( alongEnd, pointBeginRotated, pointEndRotated )
	outline.append( pointBeginIntermediate )
	verticalWidth = complex( 0.0, exclusionWidth )
	if alongToWidth > 0.9 * remainingToHalf:
		verticalWidth = complex( 0.0, slope * remainingToHalf * segmentLength )
		middle = ( pointBeginIntermediate + pointEndIntermediate ) * 0.5
		middleDown = middle - verticalWidth
		middleUp = middle + verticalWidth
		outline.append( middleUp )
		outline.append( pointEndIntermediate )
		outline.append( middleDown )
	else:
		alongOutsideBegin = along + alongToWidth
		alongOutsideEnd = alongEnd - alongToWidth
		outsideBeginCenter = euclidean.getIntermediateLocation( alongOutsideBegin, pointBeginRotated, pointEndRotated )
		outsideBeginCenterDown = outsideBeginCenter - verticalWidth
		outsideBeginCenterUp = outsideBeginCenter + verticalWidth
		outsideEndCenter = euclidean.getIntermediateLocation( alongOutsideEnd, pointBeginRotated, pointEndRotated )
		outsideEndCenterDown = outsideEndCenter - verticalWidth
		outsideEndCenterUp = outsideEndCenter + verticalWidth
		outline.append( outsideBeginCenterUp )
		outline.append( outsideEndCenterUp )
		outline.append( pointEndIntermediate )
		outline.append( outsideEndCenterDown )
		outline.append( outsideBeginCenterDown )
	outlines.append( euclidean.getPointsRoundZAxis( normalizedSegment, outline ) )

def getCraftedText( fileName, text='', repository=None):
	"""Inset the preface file or text."""
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"""Inset the preface gcode text."""
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'inset'):
		return gcodeText
	if repository is None:
		repository = settings.getReadRepository( InsetRepository() )
	return InsetSkein().getCraftedGcode(gcodeText, repository)

def getInteriorSegments(loops, segments):
	"""Get segments inside the loops."""
	interiorSegments = []
	for segment in segments:
		center = 0.5 * (segment[0].point + segment[1].point)
		if euclidean.getIsInFilledRegion(loops, center):
			interiorSegments.append(segment)
	return interiorSegments

def getIsIntersectingWithinList(loop, loopList):
	"""Determine if the loop is intersecting or is within the loop list."""
	leftPoint = euclidean.getLeftPoint(loop)
	for otherLoop in loopList:
		if euclidean.getNumberOfIntersectionsToLeft(otherLoop, leftPoint) % 2 == 1:
			return True
	return euclidean.isLoopIntersectingLoops(loop, loopList)

def getNewRepository():
	"""Get new repository."""
	return InsetRepository()

def getSegmentsFromLoopListsPoints( loopLists, pointBegin, pointEnd ):
	"""Get endpoint segments from the beginning and end of a line segment."""
	normalizedSegment = pointEnd - pointBegin
	normalizedSegmentLength = abs( normalizedSegment )
	if normalizedSegmentLength == 0.0:
		return []
	normalizedSegment /= normalizedSegmentLength
	segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
	pointBeginRotated = segmentYMirror * pointBegin
	pointEndRotated = segmentYMirror * pointEnd
	rotatedLoopLists = []
	for loopList in loopLists:
		rotatedLoopList = []
		rotatedLoopLists.append( rotatedLoopList )
		for loop in loopList:
			rotatedLoop = euclidean.getPointsRoundZAxis( segmentYMirror, loop )
			rotatedLoopList.append( rotatedLoop )
	xIntersectionIndexList = [euclidean.XIntersectionIndex(- 1, pointBeginRotated.real),
                              euclidean.XIntersectionIndex(- 1, pointEndRotated.real)]
	euclidean.addXIntersectionIndexesFromLoopListsY( rotatedLoopLists, xIntersectionIndexList, pointBeginRotated.imag )
	segments = euclidean.getSegmentsFromXIntersectionIndexes( xIntersectionIndexList, pointBeginRotated.imag )
	for segment in segments:
		for endpoint in segment:
			endpoint.point *= normalizedSegment
	return segments

def isCloseToLast( paths, point, radius ):
	"""Determine if the point is close to the last point of the last path."""
	if len(paths) < 1:
		return False
	lastPath = paths[-1]
	return abs( lastPath[-1] - point ) < radius

def isIntersectingItself( loop, width ):
	"""Determine if the loop is intersecting itself."""
	outlines = []
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if euclidean.isLineIntersectingLoops( outlines, pointBegin, pointEnd ):
			return True
		addSegmentOutline( False, outlines, pointBegin, pointEnd, width )
	return False

def isIntersectingWithinLists( loop, loopLists ):
	"""Determine if the loop is intersecting or is within the loop lists."""
	for loopList in loopLists:
		if getIsIntersectingWithinList( loop, loopList ):
			return True
	return False

def writeOutput(fileName, shouldAnalyze=True):
	"""Inset the carving of a gcode file."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'inset', shouldAnalyze)


class InsetRepository:
	"""A class to handle the inset settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.inset.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Inset', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Inset')
		self.bridgeWidthMultiplier = settings.FloatSpin().getFromValue( 0.8, 'Bridge Width Multiplier (ratio):', self, 1.2, 1.0 )
		self.loopOrderChoice = settings.MenuButtonDisplay().getFromName('In case of Conflict Solve:', self )
		self.loopOrderAscendingArea = settings.MenuRadio().getFromMenuButtonDisplay( self.loopOrderChoice, 'Prefer Loops', self, False )
		self.loopOrderDescendingArea = settings.MenuRadio().getFromMenuButtonDisplay( self.loopOrderChoice, 'Prefer Perimeter', self, True )
		self.overlapRemovalWidthOverPerimeterWidth = settings.FloatSpin().getFromValue( 0.5, 'Overlap Removal(Scaler):', self, 1.5, 1.0 )
		self.executeTitle = 'Inset'

	def execute(self):
		"""Inset button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class InsetSkein:
	"""A class to inset a skein of extrusions."""
	def __init__(self):
		self.boundary = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.layerCount = settings.LayerCount()
		self.lineIndex = 0
		self.rotatedLoopLayer = None

	def addGcodeFromPerimeterPaths(self, isIntersectingSelf, loop, loopLists, radius, rotatedLoopLayer):
		"""Add the perimeter paths to the output."""
		segments = []
		outlines = []
		thickOutlines = []
		allLoopLists = loopLists[:] + [thickOutlines]
		aroundLists = loopLists
		for pointIndex in xrange(len(loop)):
			pointBegin = loop[pointIndex]
			pointEnd = loop[(pointIndex + 1) % len(loop)]
			if isIntersectingSelf:
				if euclidean.isLineIntersectingLoops(outlines, pointBegin, pointEnd):
					segments += getSegmentsFromLoopListsPoints(allLoopLists, pointBegin, pointEnd)
				else:
					segments += getSegmentsFromLoopListsPoints(loopLists, pointBegin, pointEnd)
				addSegmentOutline(False, outlines, pointBegin, pointEnd, self.overlapRemovalWidth)
				addSegmentOutline(True, thickOutlines, pointBegin, pointEnd, self.overlapRemovalWidth)
			else:
				segments += getSegmentsFromLoopListsPoints(loopLists, pointBegin, pointEnd)
		perimeterPaths = []
		path = []
		muchSmallerThanRadius = 0.1 * radius
		segments = getInteriorSegments(rotatedLoopLayer.loops, segments)
		for segment in segments:
			pointBegin = segment[0].point
			if not isCloseToLast(perimeterPaths, pointBegin, muchSmallerThanRadius):
				path = [pointBegin]
				perimeterPaths.append(path)
			path.append(segment[1].point)
		if len(perimeterPaths) > 1:
			firstPath = perimeterPaths[0]
			lastPath = perimeterPaths[-1]
			if abs(lastPath[-1] - firstPath[0]) < 0.1 * muchSmallerThanRadius:
				connectedBeginning = lastPath[: -1] + firstPath
				perimeterPaths[0] = connectedBeginning
				perimeterPaths.remove(lastPath)
		muchGreaterThanRadius = 6.0 * radius
		for perimeterPath in perimeterPaths:
			if euclidean.getPathLength(perimeterPath) > muchGreaterThanRadius:
				self.distanceFeedRate.addGcodeFromThreadZ(perimeterPath, rotatedLoopLayer.z)

	def addGcodeFromRemainingLoop(self, loop, loopLists, radius, rotatedLoopLayer):
		"""Add the remainder of the loop which does not overlap the alreadyFilledArounds loops."""
		centerOutset = intercircle.getLargestCenterOutsetLoopFromLoopRegardless(loop, radius)
		euclidean.addSurroundingLoopBeginning(self.distanceFeedRate, centerOutset.outset, rotatedLoopLayer.z)
		self.addGcodePerimeterBlockFromRemainingLoop(centerOutset.center, loopLists, radius, rotatedLoopLayer)
		self.distanceFeedRate.addLine('(</boundaryPerimeter>)')
		self.distanceFeedRate.addLine('(</nestedRing>)')

	def addGcodePerimeterBlockFromRemainingLoop(self, loop, loopLists, radius, rotatedLoopLayer):
		"""Add the perimter block remainder of the loop which does not overlap the alreadyFilledArounds loops."""
		if self.repository.overlapRemovalWidthOverPerimeterWidth.value < 0.2:
			self.distanceFeedRate.addPerimeterBlock(loop, rotatedLoopLayer.z)
			return
		isIntersectingSelf = isIntersectingItself(loop, self.overlapRemovalWidth)
		if isIntersectingWithinLists(loop, loopLists) or isIntersectingSelf:
			self.addGcodeFromPerimeterPaths(isIntersectingSelf, loop, loopLists, radius, rotatedLoopLayer)
		else:
			self.distanceFeedRate.addPerimeterBlock(loop, rotatedLoopLayer.z)
		addAlreadyFilledArounds(loopLists, loop, self.overlapRemovalWidth)

	def addInitializationToOutput(self):
		"""Add initialization gcode to the output."""

	def addInset(self, rotatedLoopLayer):
		"""Add inset to the layer."""
		alreadyFilledArounds = []
		halfWidth = self.halfPerimeterWidth
		if rotatedLoopLayer.rotation is not None:
			halfWidth *= self.repository.bridgeWidthMultiplier.value
			self.distanceFeedRate.addTagBracketedLine('bridgeRotation', rotatedLoopLayer.rotation)
		extrudateLoops = intercircle.getInsetLoopsFromLoops(halfWidth, rotatedLoopLayer.loops)
		triangle_mesh.sortLoopsInOrderOfArea(not self.repository.loopOrderAscendingArea.value, extrudateLoops)
		for extrudateLoop in extrudateLoops:
			self.addGcodeFromRemainingLoop(extrudateLoop, alreadyFilledArounds, halfWidth, rotatedLoopLayer)

	def getCraftedGcode(self, gcodeText, repository):
		"""Parse gcode text and store the bevel gcode."""
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
			if firstWord == '(<decimalPlacesCarried>':
				self.addInitializationToOutput()
				self.distanceFeedRate.addTagBracketedLine(
					'bridgeWidthMultiplier', self.distanceFeedRate.getRounded( self.repository.bridgeWidthMultiplier.value ) )
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedLine('procedureName', 'inset')
				return
			elif firstWord == '(<layerThickness>':
				self.layerThickness = float(splitLine[1])
			elif firstWord == '(<perimeterWidth>':
				self.perimeterWidth = float(splitLine[1])
				self.halfPerimeterWidth = 0.5 * self.perimeterWidth
				self.overlapRemovalWidth = (self.halfPerimeterWidth + self.layerThickness/2) * ((math.pi/4) * self.repository.overlapRemovalWidthOverPerimeterWidth.value)
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"""Parse a gcode line and add it to the inset skein."""
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine(None, splitLine)
			self.boundary.append(location.dropAxis())
		elif firstWord == '(<bridgeRotation>':
			secondWordWithoutBrackets = splitLine[1].replace('(', '').replace(')', '')
			self.rotatedLoopLayer.rotation = complex(secondWordWithoutBrackets)
			return
		elif firstWord == '(<layer>':
			self.layerCount.printProgressIncrement('inset')
			self.rotatedLoopLayer = euclidean.RotatedLoopLayer(float(splitLine[1]))
			self.distanceFeedRate.addLine(line)
		elif firstWord == '(</layer>)':
			self.addInset( self.rotatedLoopLayer )
			self.rotatedLoopLayer = None
		elif firstWord == '(<nestedRing>)':
			self.boundary = []
			self.rotatedLoopLayer.loops.append( self.boundary )
		if self.rotatedLoopLayer is None:
			self.distanceFeedRate.addLine(line)


def main():
	"""Display the inset dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == "__main__":
	main()
