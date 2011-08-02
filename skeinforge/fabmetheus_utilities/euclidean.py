"""
Euclidean is a collection of python utilities for complex numbers, paths, polygons & Vector3s.

To use euclidean, install python 2.x on your machine, which is avaliable from http://www.python.org/download/

Then in the folder which euclidean is in, type 'python' in a shell to run the python interpreter.  Finally type 'import euclidean' to import these utilities and 'from vector3 import Vector3' to import the Vector3 class.


Below are examples of euclidean use.

>>> from euclidean import *
>>> origin=complex()
>>> right=complex(1.0,0.0)
>>> back=complex(0.0,1.0)
>>> getMaximum(right,back)
1.0, 1.0
>>> polygon=[origin, right, back]
>>> getLoopLength(polygon)
3.4142135623730949
>>> getAreaLoop(polygon)
0.5
"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import xml_simple_writer
import cStringIO
import math
import random


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalGoldenAngle = 3.8832220774509332 # (math.sqrt(5.0) - 1.0) * math.pi
globalGoldenRatio = 1.6180339887498948482045868 # math.sqrt(1.25) - .5
globalTau = math.pi + math.pi # http://tauday.com/


def addElementToListDictionary(element, key, listDictionary):
	"""Add an element to the list table."""
	if key in listDictionary:
		listDictionary[key].append(element)
	else:
		listDictionary[key] = [element]

def addElementToListDictionaryIfNotThere(element, key, listDictionary):
	"""Add the value to the lists."""
	if key in listDictionary:
		elements = listDictionary[key]
		if element not in elements:
			elements.append(element)
	else:
		listDictionary[key] = [element]

def addElementToPixelList( element, pixelDictionary, x, y ):
	"""Add an element to the pixel list."""
	stepKey = getStepKey(x, y)
	addElementToListDictionary( element, stepKey, pixelDictionary )

def addElementToPixelListFromPoint( element, pixelDictionary, point ):
	"""Add an element to the pixel list."""
	addElementToPixelList( element, pixelDictionary, int( round( point.real ) ), int( round( point.imag ) ) )

def addHorizontallyBoundedPoint(begin, center, end, horizontalBegin, horizontalEnd, path):
	"""Add point if it is within the horizontal bounds."""
	if center.real >= horizontalEnd and center.real <= horizontalBegin:
		path.append(center)
		return
	if end is not None:
		if center.real > horizontalBegin and end.real <= horizontalBegin:
			centerMinusEnd = center - end
			along = (center.real - horizontalBegin) / centerMinusEnd.real
			path.append(center - along * centerMinusEnd)
			return
	if begin is not None:
		if center.real < horizontalEnd and begin.real >= horizontalEnd:
			centerMinusBegin = center - begin
			along = (center.real - horizontalEnd) / centerMinusBegin.real
			path.append(center - along * centerMinusBegin)

def addListToListTable( elementList, key, listDictionary ):
	"""Add a list to the list table."""
	if key in listDictionary:
		listDictionary[key] += elementList
	else:
		listDictionary[key] = elementList

def addLoopToPixelTable( loop, pixelDictionary, width ):
	"""Add loop to the pixel table."""
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		addValueSegmentToPixelTable( pointBegin, pointEnd, pixelDictionary, None, width )

def addPathToPixelTable( path, pixelDictionary, value, width ):
	"""Add path to the pixel table."""
	for pointIndex in xrange( len(path) - 1 ):
		pointBegin = path[pointIndex]
		pointEnd = path[pointIndex + 1]
		addValueSegmentToPixelTable( pointBegin, pointEnd, pixelDictionary, value, width )

def addPixelTableToPixelTable( fromPixelTable, intoPixelTable ):
	"""Add from pixel table to the into pixel table."""
	for fromPixelTableKey in fromPixelTable.keys():
		intoPixelTable[ fromPixelTableKey ] = fromPixelTable[ fromPixelTableKey ]

def addPixelToPixelTable( pixelDictionary, value, x, y ):
	"""Add pixel to the pixel table."""
	pixelDictionary[getStepKey(x, y)] = value

def addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, value, x, y ):
	"""Add pixels to the pixel table with steepness."""
	if isSteep:
		addPixelToPixelTable( pixelDictionary, value, y, x )
	else:
		addPixelToPixelTable( pixelDictionary, value, x, y )

def addPointToPath( path, pixelDictionary, point, value, width ):
	"""Add a point to a path and the pixel table."""
	path.append(point)
	if len(path) < 2:
		return
	begin = path[-2]
	addValueSegmentToPixelTable( begin, point, pixelDictionary, value, width )

def addSegmentToPixelTable( beginComplex, endComplex, pixelDictionary, shortenDistanceBegin, shortenDistanceEnd, width ):
	"""Add line segment to the pixel table."""
	if abs( beginComplex - endComplex ) <= 0.0:
		return
	beginComplex /= width
	endComplex /= width
	if shortenDistanceBegin > 0.0:
		endMinusBeginComplex = endComplex - beginComplex
		endMinusBeginComplexLength = abs( endMinusBeginComplex )
		if endMinusBeginComplexLength < shortenDistanceBegin:
			return
		beginComplex = beginComplex + endMinusBeginComplex * shortenDistanceBegin / endMinusBeginComplexLength
	if shortenDistanceEnd > 0.0:
		beginMinusEndComplex = beginComplex - endComplex
		beginMinusEndComplexLength = abs( beginMinusEndComplex )
		if beginMinusEndComplexLength < 0.0:
			return
		endComplex = endComplex + beginMinusEndComplex * shortenDistanceEnd / beginMinusEndComplexLength
	deltaX = endComplex.real - beginComplex.real
	deltaY = endComplex.imag - beginComplex.imag
	isSteep = abs( deltaY ) > abs( deltaX )
	if isSteep:
		beginComplex = complex( beginComplex.imag, beginComplex.real )
		endComplex = complex( endComplex.imag, endComplex.real )
	if beginComplex.real > endComplex.real:
		endComplex, beginComplex = beginComplex, endComplex
	deltaX = endComplex.real - beginComplex.real
	deltaY = endComplex.imag - beginComplex.imag
	if deltaX > 0.0:
		gradient = deltaY / deltaX
	else:
		gradient = 0.0
		print('This should never happen, deltaX in addSegmentToPixelTable in euclidean is 0.')
		print( beginComplex )
		print( endComplex )
		print( shortenDistanceBegin )
		print( shortenDistanceEnd )
		print( width )
	xBegin = int(round(beginComplex.real))
	xEnd = int(round(endComplex.real))
	yIntersection = beginComplex.imag - beginComplex.real * gradient
	addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, None, xBegin, int( round( beginComplex.imag ) ) )
	addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, None, xEnd, int( round( endComplex.imag ) ) )
	for x in xrange( xBegin + 1, xEnd ):
		y = int( math.floor( yIntersection + x * gradient ) )
		addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, None, x, y )
		addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, None, x, y + 1 )

def addSquareTwoToPixelDictionary(pixelDictionary, point, value, width):
	"""Add square with two pixels around the center to pixel dictionary."""
	point /= width
	x = int(round(point.real))
	y = int(round(point.imag))
	for xStep in xrange(x - 2, x + 3):
		for yStep in xrange(y - 2, y + 3):
			pixelDictionary[getStepKey(xStep, yStep)] = value

def addSurroundingLoopBeginning( distanceFeedRate, loop, z ):
	"""Add surrounding loop beginning to gcode output."""
	distanceFeedRate.addLine('(<nestedRing>)')
	distanceFeedRate.addLine('(<boundaryPerimeter>)')
	for point in loop:
		pointVector3 = Vector3(point.real, point.imag, z)
		distanceFeedRate.addLine( distanceFeedRate.getBoundaryLine( pointVector3 ) )

def addToThreadsFromLoop(extrusionHalfWidth, gcodeType, loop, oldOrderedLocation, skein):
	"""Add to threads from the last location from loop."""
	loop = getLoopStartingNearest(extrusionHalfWidth, oldOrderedLocation.dropAxis(), loop)
	oldOrderedLocation.x = loop[0].real
	oldOrderedLocation.y = loop[0].imag
	gcodeTypeStart = gcodeType
	if isWiddershins(loop):
		skein.distanceFeedRate.addLine('(<%s> outer )' % gcodeType)
	else:
		skein.distanceFeedRate.addLine('(<%s> inner )' % gcodeType)
	skein.addGcodeFromThreadZ(loop + [loop[0]], oldOrderedLocation.z)
	skein.distanceFeedRate.addLine('(</%s>)' % gcodeType)

def addToThreadsRemove(extrusionHalfWidth, nestedRings, oldOrderedLocation, skein, threadSequence):
	"""Add to threads from the last location from surrounding loops."""
	while len(nestedRings) > 0:
		getTransferClosestSurroundingLoop(extrusionHalfWidth, nestedRings, oldOrderedLocation, skein, threadSequence)

def addValueSegmentToPixelTable( beginComplex, endComplex, pixelDictionary, value, width ):
	"""Add line segment to the pixel table."""
	if abs( beginComplex - endComplex ) <= 0.0:
		return
	beginComplex /= width
	endComplex /= width
	deltaX = endComplex.real - beginComplex.real
	deltaY = endComplex.imag - beginComplex.imag
	isSteep = abs( deltaY ) > abs( deltaX )
	if isSteep:
		beginComplex = complex( beginComplex.imag, beginComplex.real )
		endComplex = complex( endComplex.imag, endComplex.real )
	if beginComplex.real > endComplex.real:
		endComplex, beginComplex = beginComplex, endComplex
	deltaX = endComplex.real - beginComplex.real
	deltaY = endComplex.imag - beginComplex.imag
	if deltaX > 0.0:
		gradient = deltaY / deltaX
	else:
		gradient = 0.0
		print('This should never happen, deltaX in addValueSegmentToPixelTable in euclidean is 0.')
		print( beginComplex )
		print(value)
		print( endComplex )
		print( width )
	xBegin = int(round(beginComplex.real))
	xEnd = int(round(endComplex.real))
	yIntersection = beginComplex.imag - beginComplex.real * gradient
	addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, value, xBegin, int( round( beginComplex.imag ) ) )
	addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, value, xEnd, int( round( endComplex.imag ) ) )
	for x in xrange( xBegin + 1, xEnd ):
		y = int( math.floor( yIntersection + x * gradient ) )
		addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, value, x, y )
		addPixelToPixelTableWithSteepness( isSteep, pixelDictionary, value, x, y + 1 )

def addValueToOutput(depth, keyInput, output, value):
	"""Add value to the output."""
	depthStart = '  ' * depth
	output.write('%s%s:' % (depthStart, keyInput))
	if value.__class__ == dict:
		output.write('\n')
		keys = value.keys()
		keys.sort()
		for key in keys:
			addValueToOutput(depth + 1, key, output, value[key])
		return
	if value.__class__ == list:
		output.write('\n')
		for elementIndex, element in enumerate(value):
			addValueToOutput(depth + 1, elementIndex, output, element)
		return
	output.write(' %s\n' % value)

def addXIntersectionIndexesFromLoop( frontOverWidth, loop, solidIndex, xIntersectionIndexLists, width, yList ):
	"""Add the x intersection indexes for a loop."""
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if pointBegin.imag > pointEnd.imag:
			pointOriginal = pointBegin
			pointBegin = pointEnd
			pointEnd = pointOriginal
		fillBegin = int( math.ceil( pointBegin.imag / width - frontOverWidth ) )
		fillBegin = max( 0, fillBegin )
		fillEnd = int( math.ceil( pointEnd.imag / width - frontOverWidth ) )
		fillEnd = min( len( xIntersectionIndexLists ), fillEnd )
		if fillEnd > fillBegin:
			secondMinusFirstComplex = pointEnd - pointBegin
			secondMinusFirstImaginaryOverReal = secondMinusFirstComplex.real / secondMinusFirstComplex.imag
			beginRealMinusImaginary = pointBegin.real - pointBegin.imag * secondMinusFirstImaginaryOverReal
			for fillLine in xrange( fillBegin, fillEnd ):
				xIntersection = yList[fillLine] * secondMinusFirstImaginaryOverReal + beginRealMinusImaginary
				xIntersectionIndexList = xIntersectionIndexLists[fillLine]
				xIntersectionIndexList.append( XIntersectionIndex( solidIndex, xIntersection ) )

def addXIntersectionIndexesFromLoops( frontOverWidth, loops, solidIndex, xIntersectionIndexLists, width, yList ):
	"""Add the x intersection indexes for a loop."""
	for loop in loops:
		addXIntersectionIndexesFromLoop( frontOverWidth, loop, solidIndex, xIntersectionIndexLists, width, yList )

def addXIntersectionIndexesFromLoopY( loop, solidIndex, xIntersectionIndexList, y ):
	"""Add the x intersection indexes for a loop."""
	for pointIndex in xrange(len(loop)):
		pointFirst = loop[pointIndex]
		pointSecond = loop[(pointIndex + 1) % len(loop)]
		xIntersection = getXIntersectionIfExists( pointFirst, pointSecond, y )
		if xIntersection is not None:
			xIntersectionIndexList.append( XIntersectionIndex( solidIndex, xIntersection ) )

def addXIntersectionIndexesFromLoopListsY( loopLists, xIntersectionIndexList, y ):
	"""Add the x intersection indexes for the loop lists."""
	for loopListIndex in xrange( len(loopLists) ):
		loopList = loopLists[ loopListIndex ]
		addXIntersectionIndexesFromLoopsY( loopList, loopListIndex, xIntersectionIndexList, y )

def addXIntersectionIndexesFromLoopsY( loops, solidIndex, xIntersectionIndexList, y ):
	"""Add the x intersection indexes for the loops."""
	for loop in loops:
		addXIntersectionIndexesFromLoopY( loop, solidIndex, xIntersectionIndexList, y )

def addXIntersectionIndexesFromSegment( index, segment, xIntersectionIndexList ):
	"""Add the x intersection indexes from the segment."""
	for endpoint in segment:
		xIntersectionIndexList.append( XIntersectionIndex( index, endpoint.point.real ) )

def addXIntersectionIndexesFromSegments( index, segments, xIntersectionIndexList ):
	"""Add the x intersection indexes from the segments."""
	for segment in segments:
		addXIntersectionIndexesFromSegment( index, segment, xIntersectionIndexList )

def addXIntersectionIndexesFromXIntersections( index, xIntersectionIndexList, xIntersections ):
	"""Add the x intersection indexes from the XIntersections."""
	for xIntersection in xIntersections:
		xIntersectionIndexList.append( XIntersectionIndex( index, xIntersection ) )

def addXIntersections( loop, xIntersections, y ):
	"""Add the x intersections for a loop."""
	for pointIndex in xrange(len(loop)):
		pointFirst = loop[pointIndex]
		pointSecond = loop[(pointIndex + 1) % len(loop)]
		xIntersection = getXIntersectionIfExists( pointFirst, pointSecond, y )
		if xIntersection is not None:
			xIntersections.append( xIntersection )

def addXIntersectionsFromLoopForTable( loop, xIntersectionsTable, width ):
	"""Add the x intersections for a loop into a table."""
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if pointBegin.imag > pointEnd.imag:
			pointOriginal = pointBegin
			pointBegin = pointEnd
			pointEnd = pointOriginal
		fillBegin = int( math.ceil( pointBegin.imag / width ) )
		fillEnd = int( math.ceil( pointEnd.imag / width ) )
		if fillEnd > fillBegin:
			secondMinusFirstComplex = pointEnd - pointBegin
			secondMinusFirstImaginaryOverReal = secondMinusFirstComplex.real / secondMinusFirstComplex.imag
			beginRealMinusImaginary = pointBegin.real - pointBegin.imag * secondMinusFirstImaginaryOverReal
			for fillLine in xrange( fillBegin, fillEnd ):
				y = fillLine * width
				xIntersection = y * secondMinusFirstImaginaryOverReal + beginRealMinusImaginary
				addElementToListDictionary( xIntersection, fillLine, xIntersectionsTable )

def addXIntersectionsFromLoops( loops, xIntersections, y ):
	"""Add the x intersections for the loops."""
	for loop in loops:
		addXIntersections( loop, xIntersections, y )

def addXIntersectionsFromLoopsForTable( loops, xIntersectionsTable, width ):
	"""Add the x intersections for a loop into a table."""
	for loop in loops:
		addXIntersectionsFromLoopForTable( loop, xIntersectionsTable, width )

def compareSegmentLength( endpoint, otherEndpoint ):
	"""Get comparison in order to sort endpoints in ascending order of segment length."""
	if endpoint.segmentLength > otherEndpoint.segmentLength:
		return 1
	if endpoint.segmentLength < otherEndpoint.segmentLength:
		return - 1
	return 0

def concatenateRemovePath( connectedPaths, pathIndex, paths, pixelDictionary, segments, width ):
	"""Get connected paths from paths."""
	bottomSegment = segments[ pathIndex ]
	path = paths[ pathIndex ]
	if bottomSegment is None:
		connectedPaths.append(path)
		return
	endpoints = getEndpointsFromSegments( segments[ pathIndex + 1 : ] )
	bottomSegmentEndpoint = bottomSegment[0]
	nextEndpoint = bottomSegmentEndpoint.getNearestMissCheckEndpointPath( endpoints, bottomSegmentEndpoint.path, pixelDictionary, width )
	if nextEndpoint is None:
		bottomSegmentEndpoint = bottomSegment[1]
		nextEndpoint = bottomSegmentEndpoint.getNearestMissCheckEndpointPath( endpoints, bottomSegmentEndpoint.path, pixelDictionary, width )
	if nextEndpoint is None:
		connectedPaths.append(path)
		return
	if len( bottomSegmentEndpoint.path ) > 0 and len( nextEndpoint.path ) > 0:
		bottomEnd = bottomSegmentEndpoint.path[-1]
		nextBegin = nextEndpoint.path[-1]
		nextMinusBottomNormalized = getNormalized( nextBegin - bottomEnd )
		if len( bottomSegmentEndpoint.path ) > 1:
			bottomPenultimate = bottomSegmentEndpoint.path[-2]
			if getDotProduct( getNormalized( bottomPenultimate - bottomEnd ), nextMinusBottomNormalized ) > 0.9:
				connectedPaths.append(path)
				return
		if len( nextEndpoint.path ) > 1:
			nextPenultimate = nextEndpoint.path[-2]
			if getDotProduct( getNormalized( nextPenultimate - nextBegin ), - nextMinusBottomNormalized ) > 0.9:
				connectedPaths.append(path)
				return
	nextEndpoint.path.reverse()
	concatenatedPath = bottomSegmentEndpoint.path + nextEndpoint.path
	paths[ nextEndpoint.pathIndex ] = concatenatedPath
	segments[ nextEndpoint.pathIndex ] = getSegmentFromPath( concatenatedPath, nextEndpoint.pathIndex )
	addValueSegmentToPixelTable( bottomSegmentEndpoint.point, nextEndpoint.point, pixelDictionary, None, width )

def getAngleAroundZAxisDifference( subtractFromVec3, subtractVec3 ):
	"""Get the angle around the Z axis difference between a pair of Vector3s."""
	subtractVectorMirror = complex( subtractVec3.x , - subtractVec3.y )
	differenceVector = getRoundZAxisByPlaneAngle( subtractVectorMirror, subtractFromVec3 )
	return math.atan2( differenceVector.y, differenceVector.x )

def getAngleDifferenceByComplex( subtractFromComplex, subtractComplex ):
	"""Get the angle between a pair of normalized complexes."""
	subtractComplexMirror = complex( subtractComplex.real , - subtractComplex.imag )
	differenceComplex = subtractComplexMirror * subtractFromComplex
	return math.atan2( differenceComplex.imag, differenceComplex.real )

def getAreaLoop(loop):
	"""Get the area of a complex polygon."""
	areaLoopDouble = 0.0
	for pointIndex, point in enumerate(loop):
		pointEnd  = loop[(pointIndex + 1) % len(loop)]
		areaLoopDouble += point.real * pointEnd.imag - pointEnd.real * point.imag
	return 0.5 * areaLoopDouble

def getAreaLoopAbsolute(loop):
	"""Get the absolute area of a complex polygon."""
	return abs(getAreaLoop(loop))

def getAreaLoops(loops):
	"""Get the area of a list of complex polygons."""
	areaLoops = 0.0
	for loop in loops:
		areaLoops += getAreaLoop(loop)
	return areaLoops

def getAreaRadiusMultiplier(sides):
	"""Get the area radius multiplier for the polygon."""
	return math.sqrt(globalTau / sides / math.sin(globalTau / sides))

def getAreaVector3LoopAbsolute(loop):
	"""Get the absolute area of a vector3 polygon."""
	return getAreaLoopAbsolute(getComplexPath(loop))

def getAroundLoop(begin, end, loop):
	"""Get an arc around a loop."""
	aroundLoop = []
	if end <= begin:
		end += len(loop)
	for pointIndex in xrange(begin, end):
		aroundLoop.append(loop[pointIndex % len(loop)])
	return aroundLoop

def getAwayPoints(points, radius):
	"""Get a path with only the points that are far enough away from each other."""
	away = []
	oneOverOverlapDistance = 1000.0 / radius
	pixelDictionary = {}
	for point in points:
		x = int(point.real * oneOverOverlapDistance)
		y = int(point.imag * oneOverOverlapDistance)
		if not getSquareIsOccupied(pixelDictionary, x, y):
			away.append(point)
			stepKey = getStepKey(x, y)
			pixelDictionary[stepKey] = None
	return away

def getBackOfLoops(loops):
	"""Get the back of the loops."""
	negativeFloat = - 987654321.75342341
	back = negativeFloat
	for loop in loops:
		for point in loop:
			back = max( back, point.imag )
	if back == negativeFloat:
		print('This should never happen, there are no loops for getBackOfLoops in euclidean')
	return back

def getBooleanFromDictionary(defaultBoolean, dictionary, key):
	"""Get boolean from the dictionary and key."""
	if key not in dictionary:
		return defaultBoolean
	return getBooleanFromValue(dictionary[key])

def getBooleanFromValue(value):
	"""Get boolean from the word."""
	firstCharacter = str(value).lower().lstrip()[: 1]
	return firstCharacter == 't' or firstCharacter == '1'

def getBottomByPath(path):
	"""Get the bottom of the path."""
	bottom = 987654321.0
	for point in path:
		bottom = min(bottom, point.z)
	return bottom

def getBottomByPaths(paths):
	"""Get the bottom of the paths."""
	bottom = 987654321.0
	for path in paths:
		for point in path:
			bottom = min(bottom, point.z)
	return bottom

def getClippedAtEndLoopPath( clip, loopPath ):
	"""Get a clipped loop path."""
	if clip <= 0.0:
		return loopPath
	loopPathLength = getPathLength(loopPath)
	clip = min( clip, 0.3 * loopPathLength )
	lastLength = 0.0
	pointIndex = 0
	totalLength = 0.0
	clippedLength = loopPathLength - clip
	while totalLength < clippedLength and pointIndex < len(loopPath) - 1:
		firstPoint = loopPath[pointIndex]
		secondPoint  = loopPath[pointIndex + 1]
		pointIndex += 1
		lastLength = totalLength
		totalLength += abs(firstPoint - secondPoint)
	remainingLength = clippedLength - lastLength
	clippedLoopPath = loopPath[ : pointIndex ]
	ultimateClippedPoint = loopPath[pointIndex]
	penultimateClippedPoint = clippedLoopPath[-1]
	segment = ultimateClippedPoint - penultimateClippedPoint
	segmentLength = abs(segment)
	if segmentLength <= 0.0:
		return clippedLoopPath
	newUltimatePoint = penultimateClippedPoint + segment * remainingLength / segmentLength
	return clippedLoopPath + [newUltimatePoint]

def getClippedLoopPath(clip, loopPath):
	"""Get a clipped loop path."""
	if clip <= 0.0:
		return loopPath
	loopPathLength = getPathLength(loopPath)
	clip = min(clip, 0.3 * loopPathLength)
	lastLength = 0.0
	pointIndex = 0
	totalLength = 0.0
	while totalLength < clip and pointIndex < len(loopPath) - 1:
		firstPoint = loopPath[pointIndex]
		secondPoint  = loopPath[pointIndex + 1]
		pointIndex += 1
		lastLength = totalLength
		totalLength += abs(firstPoint - secondPoint)
	remainingLength = clip - lastLength
	clippedLoopPath = loopPath[pointIndex :]
	ultimateClippedPoint = clippedLoopPath[0]
	penultimateClippedPoint = loopPath[pointIndex - 1]
	segment = ultimateClippedPoint - penultimateClippedPoint
	segmentLength = abs(segment)
	loopPath = clippedLoopPath
	if segmentLength > 0.0:
		newUltimatePoint = penultimateClippedPoint + segment * remainingLength / segmentLength
		loopPath = [newUltimatePoint] + loopPath
	return getClippedAtEndLoopPath(clip, loopPath)

def getClippedSimplifiedLoopPath(clip, loopPath, radius):
	"""Get a clipped and simplified loop path."""
	return getSimplifiedPath(getClippedLoopPath(clip, loopPath), radius)

def getComplexByCommaString( valueCommaString ):
	"""Get the commaString as a complex."""
	try:
		splitLine = valueCommaString.replace(',', ' ').split()
		return complex( float( splitLine[0] ), float(splitLine[1]) )
	except:
		pass
	return None

def getComplexDefaultByDictionary( defaultComplex, dictionary, key ):
	"""Get the value as a complex."""
	if key in dictionary:
		return complex( dictionary[key].strip().replace('(', '').replace(')', '') )
	return defaultComplex

def getComplexDefaultByDictionaryKeys( defaultComplex, dictionary, keyX, keyY ):
	"""Get the value as a complex."""
	x = getFloatDefaultByDictionary( defaultComplex.real, dictionary, keyX )
	y = getFloatDefaultByDictionary( defaultComplex.real, dictionary, keyY )
	return complex(x, y)

def getComplexByWords(words, wordIndex=0):
	"""Get the complex by the first two words."""
	try:
		return complex(float(words[wordIndex]), float(words[wordIndex + 1]))
	except:
		pass
	return None

def getComplexPath(vector3Path):
	"""Get the complex path from the vector3 path."""
	complexPath = []
	for point in vector3Path:
		complexPath.append(point.dropAxis())
	return complexPath

def getComplexPathByMultiplier(multiplier, path):
	"""Get the multiplied complex path."""
	complexPath = []
	for point in path:
		complexPath.append(multiplier * point)
	return complexPath

def getComplexPaths(vector3Paths):
	"""Get the complex paths from the vector3 paths."""
	complexPaths = []
	for vector3Path in vector3Paths:
		complexPaths.append(getComplexPath(vector3Path))
	return complexPaths

def getComplexPolygon(center, radius, sides, startAngle=0.0):
	"""Get the complex polygon."""
	complexPolygon = []
	sideAngle = 2.0 * math.pi / float(sides)
	for side in xrange(abs(sides)):
		unitPolar = getWiddershinsUnitPolar(startAngle)
		complexPolygon.append(unitPolar * radius + center)
		startAngle += sideAngle
	return complexPolygon

def getComplexPolygonByComplexRadius(radius, sides, startAngle=0.0):
	"""Get the complex polygon."""
	complexPolygon = []
	sideAngle = 2.0 * math.pi / float(sides)
	for side in xrange(abs(sides)):
		unitPolar = getWiddershinsUnitPolar(startAngle)
		complexPolygon.append(complex(unitPolar.real * radius.real, unitPolar.imag * radius.imag))
		startAngle += sideAngle
	return complexPolygon

def getComplexPolygonByStartEnd(endAngle, radius, sides, startAngle=0.0):
	"""Get the complex polygon by start and end angle."""
	angleExtent = endAngle - startAngle
	sideAngle = 2.0 * math.pi / float(sides)
	sides = int(math.ceil(abs(angleExtent / sideAngle)))
	sideAngle = angleExtent / float(sides)
	complexPolygon = []
	for side in xrange(abs(sides) + 1):
		unitPolar = getWiddershinsUnitPolar(startAngle)
		complexPolygon.append(unitPolar * radius)
		startAngle += sideAngle
	return getLoopWithoutCloseEnds(0.000001 * radius, complexPolygon)

def getConcatenatedList(originalLists):
	"""Get the lists as one concatenated list."""
	concatenatedList = []
	for originalList in originalLists:
		concatenatedList += originalList
	return concatenatedList

def getConnectedPaths( paths, pixelDictionary, width ):
	"""Get connected paths from paths."""
	if len(paths) < 2:
		return paths
	connectedPaths = []
	segments = []
	for pathIndex in xrange( len(paths) ):
		path = paths[ pathIndex ]
		segments.append( getSegmentFromPath( path, pathIndex ) )
	for pathIndex in xrange( 0, len(paths) - 1 ):
		concatenateRemovePath( connectedPaths, pathIndex, paths, pixelDictionary, segments, width )
	connectedPaths.append( paths[-1] )
	return connectedPaths

def getCrossProduct( firstComplex, secondComplex ):
	"""Get z component cross product of a pair of complexes."""
	return firstComplex.real * secondComplex.imag - firstComplex.imag * secondComplex.real

def getDecimalPlacesCarried(extraDecimalPlaces, value):
	"""Get decimal places carried by the decimal places of the value plus the extraDecimalPlaces."""
	return max(0, 1 + int(math.ceil(extraDecimalPlaces - math.log10(value))))

def getDiagonalFlippedLoop(loop):
	"""Get loop flipped over the dialogonal, in other words with the x and y swapped."""
	diagonalFlippedLoop = []
	for point in loop:
		diagonalFlippedLoop.append( complex( point.imag, point.real ) )
	return diagonalFlippedLoop

def getDiagonalFlippedLoops(loops):
	"""Get loops flipped over the dialogonal, in other words with the x and y swapped."""
	diagonalFlippedLoops = []
	for loop in loops:
		diagonalFlippedLoops.append( getDiagonalFlippedLoop(loop) )
	return diagonalFlippedLoops

def getDictionaryString(dictionary):
	"""Get the dictionary string."""
	output = cStringIO.StringIO()
	keys = dictionary.keys()
	keys.sort()
	for key in keys:
		addValueToOutput(0, key, output, dictionary[key])
	return output.getvalue()

def getDistanceToLine(begin, end, point):
	"""Get the distance from a vector3 point to an infinite line."""
	pointMinusBegin = point - begin
	if begin == end:
		return abs(pointMinusBegin)
	endMinusBegin = end - begin
	return abs(endMinusBegin.cross(pointMinusBegin)) / abs(endMinusBegin)

def getDistanceToLineByPath(begin, end, path):
	"""Get the maximum distance from a path to an infinite line."""
	distanceToLine = -987654321.0
	for point in path:
		distanceToLine = max(getDistanceToLine(begin, end, point), distanceToLine)
	return distanceToLine

def getDistanceToLineByPaths(begin, end, paths):
	"""Get the maximum distance from paths to an infinite line."""
	distanceToLine = -987654321.0
	for path in paths:
		distanceToLine = max(getDistanceToLineByPath(begin, end, path), distanceToLine)
	return distanceToLine

def getDistanceToPlaneSegment( segmentBegin, segmentEnd, point ):
	"""Get the distance squared from a point to the x & y components of a segment."""
	segmentDifference = segmentEnd - segmentBegin
	pointMinusSegmentBegin = point - segmentBegin
	beginPlaneDot = getDotProduct( pointMinusSegmentBegin, segmentDifference )
	if beginPlaneDot <= 0.0:
		return abs( point - segmentBegin ) * abs( point - segmentBegin )
	differencePlaneDot = getDotProduct( segmentDifference, segmentDifference )
	if differencePlaneDot <= beginPlaneDot:
		return abs( point - segmentEnd ) * abs( point - segmentEnd )
	intercept = beginPlaneDot / differencePlaneDot
	interceptPerpendicular = segmentBegin + segmentDifference * intercept
	return abs( point - interceptPerpendicular ) * abs( point - interceptPerpendicular )

def getDotProduct( firstComplex, secondComplex ):
	"""Get the dot product of a pair of complexes."""
	return firstComplex.real * secondComplex.real + firstComplex.imag * secondComplex.imag

def getDotProductPlusOne( firstComplex, secondComplex ):
	"""Get the dot product plus one of the x and y components of a pair of Vector3s."""
	return 1.0 + getDotProduct( firstComplex, secondComplex )

def getDurationString( seconds ):
	"""Get the duration string."""
	secondsRounded = int( round( seconds ) )
	durationString = getPluralString( secondsRounded % 60, 'second')
	if seconds < 60:
		return durationString
	durationString =  '%s %s' % ( getPluralString( ( secondsRounded / 60 ) % 60, 'minute'), durationString )
	if seconds < 3600:
		return durationString
	return  '%s %s' % ( getPluralString( secondsRounded / 3600, 'hour'), durationString )

def getEndpointFromPath( path, pathIndex ):
	"""Get endpoint segment from a path."""
	begin = path[-1]
	end = path[-2]
	endpointBegin = Endpoint()
	endpointEnd = Endpoint().getFromOtherPoint( endpointBegin, end )
	endpointBegin.getFromOtherPoint( endpointEnd, begin )
	endpointBegin.path = path
	endpointBegin.pathIndex = pathIndex
	return endpointBegin

def getEndpointsFromSegments( segments ):
	"""Get endpoints from segments."""
	endpoints = []
	for segment in segments:
		for endpoint in segment:
			endpoints.append( endpoint )
	return endpoints

def getEndpointsFromSegmentTable( segmentTable ):
	"""Get the endpoints from the segment table."""
	endpoints = []
	segmentTableKeys = segmentTable.keys()
	segmentTableKeys.sort()
	for segmentTableKey in segmentTableKeys:
		for segment in segmentTable[ segmentTableKey ]:
			for endpoint in segment:
				endpoints.append( endpoint )
	return endpoints

def getEnumeratorKeys(enumerator, keys):
	"""Get enumerator keys."""
	if len(keys) == 1:
		return keys[0]
	return getEnumeratorKeysExceptForOneArgument(enumerator, keys)

def getEnumeratorKeysAlwaysList(enumerator, keys):
	"""Get enumerator keys."""
	if keys.__class__ != list:
		return [keys]
	if len(keys) == 1:
		return keys
	return getEnumeratorKeysExceptForOneArgument(enumerator, keys)

def getEnumeratorKeysExceptForOneArgument(enumerator, keys):
	"""Get enumerator keys, except when there is one argument."""
	if not len(keys):
		return range(0, len(enumerator))
	beginIndex = keys[0]
	endIndex = keys[1]
	if len(keys) == 2:
		if beginIndex is None:
			beginIndex = 0
		if endIndex is None:
			endIndex = len(enumerator)
		return range(beginIndex, endIndex)
	step = keys[2]
	beginIndexDefault = 0
	endIndexDefault = len(enumerator)
	if step < 0:
		beginIndexDefault = endIndexDefault - 1
		endIndexDefault = -1
	if beginIndex is None:
		beginIndex = beginIndexDefault
	if endIndex is None:
		endIndex = endIndexDefault
	return range(beginIndex, endIndex, step)

def getFillOfSurroundings(nestedRings, penultimateFillLoops):
	"""Get extra fill loops of surrounding loops."""
	fillOfSurroundings = []
	for nestedRing in nestedRings:
		fillOfSurroundings += nestedRing.getFillLoops(penultimateFillLoops)
	return fillOfSurroundings

def getFloatDefaultByDictionary( defaultFloat, dictionary, key ):
	"""Get the value as a float."""
	evaluatedFloat = None
	if key in dictionary:
		evaluatedFloat = getFloatFromValue(dictionary[key])
	if evaluatedFloat is None:
		return defaultFloat
	return evaluatedFloat

def getFloatFromValue(value):
	"""Get the value as a float."""
	try:
		return float(value)
	except:
		pass
	return None

def getFourSignificantFigures(number):
	"""Get number rounded to four significant figures as a string."""
	if number is None:
		return None
	absoluteNumber = abs(number)
	if absoluteNumber >= 100.0:
		return getRoundedToPlacesString( 2, number )
	if absoluteNumber < 0.000000001:
		return getRoundedToPlacesString( 13, number )
	return getRoundedToPlacesString( 3 - math.floor( math.log10( absoluteNumber ) ), number )

def getFrontOfLoops(loops):
	"""Get the front of the loops."""
	bigFloat = 987654321.196854654
	front = bigFloat
	for loop in loops:
		for point in loop:
			front = min( front, point.imag )
	if front == bigFloat:
		print('This should never happen, there are no loops for getFrontOfLoops in euclidean')
	return front

def getFrontOverWidthAddXListYList( front, loopLists, numberOfLines, xIntersectionIndexLists, width, yList ):
	"""Get the front over width and add the x intersection index lists and ylist."""
	frontOverWidth = getFrontOverWidthAddYList( front, numberOfLines, xIntersectionIndexLists, width, yList )
	for loopListIndex in xrange( len(loopLists) ):
		loopList = loopLists[ loopListIndex ]
		addXIntersectionIndexesFromLoops( frontOverWidth, loopList, loopListIndex, xIntersectionIndexLists, width, yList )
	return frontOverWidth

def getFrontOverWidthAddYList( front, numberOfLines, xIntersectionIndexLists, width, yList ):
	"""Get the front over width and add the x intersection index lists and ylist."""
	frontOverWidth = front / width
	for fillLine in xrange( numberOfLines ):
		yList.append( front + float( fillLine ) * width )
		xIntersectionIndexLists.append([])
	return frontOverWidth

def getHalfSimplifiedLoop( loop, radius, remainder ):
	"""Get the loop with half of the points inside the channel removed."""
	if len(loop) < 2:
		return loop
	channelRadius = radius * .01
	simplified = []
	addIndex = 0
	if remainder == 1:
		addIndex = len(loop) - 1
	for pointIndex in xrange(len(loop)):
		point = loop[pointIndex]
		if pointIndex % 2 == remainder or pointIndex == addIndex:
			simplified.append(point)
		elif not isWithinChannel( channelRadius, pointIndex, loop ):
			simplified.append(point)
	return simplified

def getHalfSimplifiedPath(path, radius, remainder):
	"""Get the path with half of the points inside the channel removed."""
	if len(path) < 2:
		return path
	channelRadius = radius * .01
	simplified = [path[0]]
	for pointIndex in xrange(1, len(path) - 1):
		point = path[pointIndex]
		if pointIndex % 2 == remainder:
			simplified.append(point)
		elif not isWithinChannel(channelRadius, pointIndex, path):
			simplified.append(point)
	simplified.append(path[-1])
	return simplified

def getHorizontallyBoundedPath(horizontalBegin, horizontalEnd, path):
	"""Get horizontally bounded path."""
	horizontallyBoundedPath = []
	for pointIndex, point in enumerate(path):
		begin = None
		previousIndex = pointIndex - 1
		if previousIndex >= 0:
			begin = path[previousIndex]
		end = None
		nextIndex = pointIndex + 1
		if nextIndex < len(path):
			end = path[nextIndex]
		addHorizontallyBoundedPoint(begin, point, end, horizontalBegin, horizontalEnd, horizontallyBoundedPath)
	return horizontallyBoundedPath

def getHorizontalSegmentListsFromLoopLists( alreadyFilledArounds, front, numberOfLines, rotatedFillLoops, width ):
	"""Get horizontal segment lists inside loops."""
	xIntersectionIndexLists = []
	yList = []
	frontOverWidth = getFrontOverWidthAddXListYList( front, alreadyFilledArounds, numberOfLines, xIntersectionIndexLists, width, yList )
	addXIntersectionIndexesFromLoops( frontOverWidth, rotatedFillLoops, - 1, xIntersectionIndexLists, width, yList )
	horizontalSegmentLists = []
	for xIntersectionIndexListIndex in xrange( len( xIntersectionIndexLists ) ):
		xIntersectionIndexList = xIntersectionIndexLists[ xIntersectionIndexListIndex ]
		lineSegments = getSegmentsFromXIntersectionIndexes( xIntersectionIndexList, yList[ xIntersectionIndexListIndex ] )
		horizontalSegmentLists.append( lineSegments )
	return horizontalSegmentLists

def getIncrementFromRank( rank ):
	"""Get the increment from the rank which is 0 at 1 and increases by three every power of ten."""
	rankZone = int( math.floor( rank / 3 ) )
	rankModulo = rank % 3
	powerOfTen = pow( 10, rankZone )
	moduloMultipliers = ( 1, 2, 5 )
	return float( powerOfTen * moduloMultipliers[ rankModulo ] )

def getInsidesAddToOutsides( loops, outsides ):
	"""Add loops to either the insides or outsides."""
	insides = []
	for loopIndex in xrange( len(loops) ):
		loop = loops[loopIndex]
		if isInsideOtherLoops( loopIndex, loops ):
			insides.append(loop)
		else:
			outsides.append(loop)
	return insides

def getIntermediateLocation( alongWay, begin, end ):
	"""Get the intermediate location between begin and end."""
	return begin * ( 1.0 - alongWay ) + end * alongWay

def getIntersectionOfXIntersectionIndexes( totalSolidSurfaceThickness, xIntersectionIndexList ):
	"""Get x intersections from surrounding layers."""
	xIntersectionList = []
	solidTable = {}
	solid = False
	xIntersectionIndexList.sort()
	for xIntersectionIndex in xIntersectionIndexList:
		toggleHashtable(solidTable, xIntersectionIndex.index, '')
		oldSolid = solid
		solid = len(solidTable) >= totalSolidSurfaceThickness
		if oldSolid != solid:
			xIntersectionList.append(xIntersectionIndex.x)
	return xIntersectionList

def getIntersectionOfXIntersectionsTables( xIntersectionsTables ):
	"""Get the intersection of both XIntersections tables."""
	intersectionOfXIntersectionsTables = {}
	firstIntersectionTable = xIntersectionsTables[0]
	for firstIntersectionTableKey in firstIntersectionTable.keys():
		xIntersectionIndexList = []
		for xIntersectionsTableIndex in xrange( len( xIntersectionsTables ) ):
			xIntersectionsTable = xIntersectionsTables[ xIntersectionsTableIndex ]
			addXIntersectionIndexesFromXIntersections( xIntersectionsTableIndex, xIntersectionIndexList, xIntersectionsTable[ firstIntersectionTableKey ] )
		xIntersections = getIntersectionOfXIntersectionIndexes( len( xIntersectionsTables ), xIntersectionIndexList )
		if len( xIntersections ) > 0:
			intersectionOfXIntersectionsTables[ firstIntersectionTableKey ] = xIntersections
	return intersectionOfXIntersectionsTables

def getIntFromValue(value):
	"""Get the value as an int."""
	try:
		return int(value)
	except:
		pass
	return None

def getIsInFilledRegion(loops, point):
	"""Determine if the point is in the filled region of the loops."""
	return getNumberOfIntersectionsToLeftOfLoops(loops, point) % 2 == 1

def getIsInFilledRegionByPaths(loops, paths):
	"""Determine if the point of any path is in the filled region of the loops."""
	for path in paths:
		if len(path) > 0:
			if getIsInFilledRegion(loops, path[0]):
				return True
	return False

def getIsRadianClose(firstRadian, secondRadian):
	"""Determine if the firstRadian is close to the secondRadian."""
	return abs(math.pi - abs(math.pi - ((firstRadian - secondRadian) % (math.pi + math.pi) ))) < 0.000001

def getIsWiddershinsByVector3( polygon ):
	"""Determine if the polygon goes round in the widdershins direction."""
	return isWiddershins( getComplexPath( polygon ) )

def getJoinOfXIntersectionIndexes( xIntersectionIndexList ):
	"""Get joined x intersections from surrounding layers."""
	xIntersections = []
	solidTable = {}
	solid = False
	xIntersectionIndexList.sort()
	for xIntersectionIndex in xIntersectionIndexList:
		toggleHashtable(solidTable, xIntersectionIndex.index, '')
		oldSolid = solid
		solid = len(solidTable) > 0
		if oldSolid != solid:
			xIntersections.append(xIntersectionIndex.x)
	return xIntersections

def getLargestLoop(loops):
	"""Get largest loop from loops."""
	if len(loops) == 1:
		return loops[0]
	largestArea = - 987654321.0
	largestLoop = []
	for loop in loops:
		loopArea = abs( getAreaLoop(loop) )
		if loopArea > largestArea:
			largestArea = loopArea
			largestLoop = loop
	return largestLoop

def getLeftPoint(points):
	"""Get the leftmost complex point in the points."""
	leftmost = 987654321.0
	leftPointComplex = None
	for pointComplex in points:
		if pointComplex.real < leftmost:
			leftmost = pointComplex.real
			leftPointComplex = pointComplex
	return leftPointComplex

def getLeftPointIndex(points):
	"""Get the index of the leftmost complex point in the points."""
	if len(points) < 1:
		return None
	leftPointIndex = 0
	for pointIndex in xrange( len(points) ):
		if points[pointIndex].real < points[ leftPointIndex ].real:
			leftPointIndex = pointIndex
	return leftPointIndex

def getListTableElements( listDictionary ):
	"""Get all the element in a list table."""
	listDictionaryElements = []
	for listDictionaryValue in listDictionary.values():
		listDictionaryElements += listDictionaryValue
	return listDictionaryElements

def getLoopCentroid(polygonComplex):
	"""Get the area of a complex polygon using http://en.wikipedia.org/wiki/Centroid."""
	polygonDoubleArea = 0.0
	polygonTorque = 0.0
	for pointIndex in xrange( len(polygonComplex) ):
		pointBegin = polygonComplex[pointIndex]
		pointEnd  = polygonComplex[ (pointIndex + 1) % len(polygonComplex) ]
		doubleArea = pointBegin.real * pointEnd.imag - pointEnd.real * pointBegin.imag
		doubleCenter = complex( pointBegin.real + pointEnd.real, pointBegin.imag + pointEnd.imag )
		polygonDoubleArea += doubleArea
		polygonTorque += doubleArea * doubleCenter
	torqueMultiplier = 0.333333333333333333333333 / polygonDoubleArea
	return polygonTorque * torqueMultiplier

def getLoopConvex(points):
	"""Get convex hull of points using gift wrap algorithm."""
	loopConvex = []
	pointSet = set()
	for point in points:
		if point not in pointSet:
			pointSet.add(point)
			loopConvex.append(point)
	if len(loopConvex) < 4:
		return loopConvex
	leftPoint = getLeftPoint(loopConvex)
	lastPoint = leftPoint
	pointSet.remove(leftPoint)
	loopConvex = [leftPoint]
	lastSegment = complex(0.0, 1.0)
	while True:
		greatestDotProduct = -9.9
		greatestPoint = None
		greatestSegment = None
		if len(loopConvex) > 2:
			nextSegment = getNormalized(leftPoint - lastPoint)
			if abs(nextSegment) > 0.0:
				greatestDotProduct = getDotProduct(nextSegment, lastSegment)
		for point in pointSet:
			nextSegment = getNormalized(point - lastPoint)
			if abs(nextSegment) > 0.0:
				dotProduct = getDotProduct(nextSegment, lastSegment)
				if dotProduct >= greatestDotProduct:
					greatestDotProduct = dotProduct
					greatestPoint = point
					greatestSegment = nextSegment
		if greatestPoint is None:
			return loopConvex
		lastPoint = greatestPoint
		loopConvex.append(greatestPoint)
		pointSet.remove(greatestPoint)
		lastSegment = greatestSegment
	return loopConvex

def getLoopConvexCentroid(polygonComplex):
	"""Get centroid of the convex hull of a complex polygon."""
	return getLoopCentroid( getLoopConvex(polygonComplex) )

def getLoopInsideContainingLoop( containingLoop, loops ):
	"""Get a loop that is inside the containing loop."""
	for loop in loops:
		if loop != containingLoop:
			if isPathInsideLoop( containingLoop, loop ):
				return loop
	return None

def getLoopLength( polygon ):
	"""Get the length of a polygon perimeter."""
	polygonLength = 0.0
	for pointIndex in xrange( len( polygon ) ):
		point = polygon[pointIndex]
		secondPoint  = polygon[ (pointIndex + 1) % len( polygon ) ]
		polygonLength += abs( point - secondPoint )
	return polygonLength

def getLoopStartingNearest(extrusionHalfWidth, location, loop):
	"""Add to threads from the last location from loop."""
	nearestIndex = getNearestDistanceIndex(location, loop).index
	loop = getAroundLoop(nearestIndex, nearestIndex, loop)
	nearestPoint = getNearestPointOnSegment(loop[0], loop[1], location)
	if abs(nearestPoint - loop[0]) > extrusionHalfWidth and abs(nearestPoint - loop[1]) > extrusionHalfWidth:
		loop = [nearestPoint] + loop[1 :] + [loop[0]]
	elif abs(nearestPoint - loop[0]) > abs(nearestPoint - loop[1]):
		loop = loop[1 :] + [loop[0]]
	return loop

def getLoopWithoutCloseEnds(close, loop):
	"""Get loop without close ends."""
	if len(loop) < 2:
		return loop
	if abs(loop[0] - loop[-1]) > close:
		return loop
	return loop[: -1]

def getLoopWithoutCloseSequentialPoints(close, loop):
	"""Get loop without close sequential points."""
	if len(loop) < 2:
		return loop
	lastPoint = loop[-1]
	loopWithoutCloseSequentialPoints = []
	for point in loop:
		if abs(point - lastPoint) > close:
			loopWithoutCloseSequentialPoints.append(point)
		lastPoint = point
	return loopWithoutCloseSequentialPoints

def getMaximum(firstComplex, secondComplex):
	"""Get a complex with each component the maximum of the respective components of a pair of complexes."""
	return complex(max(firstComplex.real, secondComplex.real), max(firstComplex.imag, secondComplex.imag))

def getMaximumByComplexPath(path):
	"""Get a complex with each component the maximum of the respective components of a complex path."""
	maximum = complex(-987654321.0, -987654321.0)
	for point in path:
		maximum = getMaximum(maximum, point)
	return maximum

def getMaximumByComplexPaths(paths):
	"""Get a complex with each component the maximum of the respective components of complex paths."""
	maximum = complex(-987654321.0, -987654321.0)
	for path in paths:
		for point in path:
			maximum = getMaximum(maximum, point)
	return maximum

def getMaximumByVector3Path(path):
	"""Get a vector3 with each component the maximum of the respective components of a vector3 path."""
	maximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
	for point in path:
		maximum.maximize(point)
	return maximum

def getMaximumByVector3Paths(paths):
	"""Get a complex with each component the maximum of the respective components of a complex path."""
	maximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
	for path in paths:
		for point in path:
			maximum.maximize(point)
	return maximum

def getMaximumSpan(loop):
	"""Get the maximum span of the loop."""
	extent = getMaximumByComplexPath(loop) - getMinimumByComplexPath(loop)
	return max(extent.real, extent.imag)

def getMinimum(firstComplex, secondComplex):
	"""Get a complex with each component the minimum of the respective components of a pair of complexes."""
	return complex(min(firstComplex.real, secondComplex.real), min(firstComplex.imag, secondComplex.imag))

def getMinimumByComplexPath(path):
	"""Get a complex with each component the minimum of the respective components of a complex path."""
	minimum = complex(987654321.0, 987654321.0)
	for point in path:
		minimum = getMinimum(minimum, point)
	return minimum

def getMinimumByComplexPaths(paths):
	"""Get a complex with each component the minimum of the respective components of complex paths."""
	minimum = complex(987654321.0, 987654321.0)
	for path in paths:
		for point in path:
			minimum = getMinimum(minimum, point)
	return minimum

def getMinimumByVector3Path(path):
	"""Get a vector3 with each component the minimum of the respective components of a vector3 path."""
	minimum = Vector3(987654321.0, 987654321.0, 987654321.0)
	for point in path:
		minimum.minimize(point)
	return minimum

def getMinimumByVector3Paths(paths):
	"""Get a complex with each component the minimum of the respective components of a complex path."""
	minimum = Vector3(987654321.0, 987654321.0, 987654321.0)
	for path in paths:
		for point in path:
			minimum.minimize(point)
	return minimum

def getMirrorPath(path):
	"""Get mirror path."""
	close = 0.001 * getPathLength(path)
	for pointIndex in xrange(len(path) - 1, -1, -1):
		point = path[pointIndex]
		flipPoint = complex(-point.real, point.imag)
		if abs(flipPoint - path[-1]) > close:
			path.append(flipPoint)
	return path

def getNearestDistanceIndex( point, loop ):
	"""Get the distance squared to the nearest segment of the loop and index of that segment."""
	smallestDistance = 987654321987654321.0
	nearestDistanceIndex = None
	for pointIndex in xrange(len(loop)):
		segmentBegin = loop[pointIndex]
		segmentEnd = loop[(pointIndex + 1) % len(loop)]
		distance = getDistanceToPlaneSegment( segmentBegin, segmentEnd, point )
		if distance < smallestDistance:
			smallestDistance = distance
			nearestDistanceIndex = DistanceIndex( distance, pointIndex )
	return nearestDistanceIndex

def getNearestPointOnSegment( segmentBegin, segmentEnd, point ):
	"""Get the nearest point on the segment."""
	segmentDifference = segmentEnd - segmentBegin
	if abs(segmentDifference) <= 0.0:
		return segmentBegin
	pointMinusSegmentBegin = point - segmentBegin
	beginPlaneDot = getDotProduct(pointMinusSegmentBegin, segmentDifference)
	differencePlaneDot = getDotProduct(segmentDifference, segmentDifference)
	intercept = beginPlaneDot / differencePlaneDot
	intercept = max(intercept, 0.0)
	intercept = min(intercept, 1.0)
	return segmentBegin + segmentDifference * intercept

def getNormal(begin, center, end):
	"""Get normal."""
	centerMinusBegin = (center - begin).getNormalized()
	endMinusCenter = (end - center).getNormalized()
	return centerMinusBegin.cross(endMinusCenter)

def getNormalByPath(path):
	"""Get normal by path."""
	totalNormal = Vector3()
	for pointIndex, point in enumerate(path):
		center = path[(pointIndex + 1) % len(path)]
		end = path[(pointIndex + 2) % len(path)]
		totalNormal += getNormalWeighted(point, center, end)
	return totalNormal.getNormalized()

def getNormalized( complexNumber ):
	"""Get the normalized complex."""
	complexNumberLength = abs( complexNumber )
	if complexNumberLength > 0.0:
		return complexNumber / complexNumberLength
	return complexNumber

def getNormalWeighted(begin, center, end):
	"""Get weighted normal."""
	return (center - begin).cross(end - center)

def getNumberOfIntersectionsToLeft(loop, point):
	"""Get the number of intersections through the loop for the line going left."""
	numberOfIntersectionsToLeft = 0
	for pointIndex in xrange(len(loop)):
		firstPointComplex = loop[pointIndex]
		secondPointComplex = loop[(pointIndex + 1) % len(loop)]
		xIntersection = getXIntersectionIfExists(firstPointComplex, secondPointComplex, point.imag)
		if xIntersection is not None:
			if xIntersection < point.real:
				numberOfIntersectionsToLeft += 1
	return numberOfIntersectionsToLeft

def getNumberOfIntersectionsToLeftOfLoops(loops, point):
	"""Get the number of intersections through the loop for the line starting from the left point and going left."""
	totalNumberOfIntersectionsToLeft = 0
	for loop in loops:
		totalNumberOfIntersectionsToLeft += getNumberOfIntersectionsToLeft(loop, point)
	return totalNumberOfIntersectionsToLeft

def getOrderedNestedRings(nestedRings):
	"""Get ordered nestedRings from nestedRings."""
	insides = []
	orderedNestedRings = []
	for loopIndex in xrange(len(nestedRings)):
		nestedRing = nestedRings[loopIndex]
		otherLoops = []
		for beforeIndex in xrange(loopIndex):
			otherLoops.append(nestedRings[beforeIndex].boundary)
		for afterIndex in xrange(loopIndex + 1, len(nestedRings)):
			otherLoops.append(nestedRings[afterIndex].boundary)
		if isPathEntirelyInsideLoops(otherLoops, nestedRing.boundary):
			insides.append(nestedRing)
		else:
			orderedNestedRings.append(nestedRing)
	for outside in orderedNestedRings:
		outside.getFromInsideSurroundings(insides)
	return orderedNestedRings

def getPathCopy(path):
	"""Get path copy."""
	pathCopy = []
	for point in path:
		pathCopy.append(point.copy())
	return pathCopy

def getPathLength(path):
	"""Get the length of a path ( an open polyline )."""
	pathLength = 0.0
	for pointIndex in xrange( len(path) - 1 ):
		firstPoint = path[pointIndex]
		secondPoint  = path[pointIndex + 1]
		pathLength += abs(firstPoint - secondPoint)
	return pathLength

def getPathsFromEndpoints(endpoints, maximumConnectionLength, pixelDictionary, width):
	"""Get paths from endpoints."""
	if len(endpoints) < 2:
		return [[]]
	for beginningEndpoint in endpoints[: : 2]:
		beginningPoint = beginningEndpoint.point
		addSegmentToPixelTable(beginningPoint, beginningEndpoint.otherEndpoint.point, pixelDictionary, 0, 0, width)
	endpointFirst = endpoints[0]
	endpoints.remove(endpointFirst)
	otherEndpoint = endpointFirst.otherEndpoint
	endpoints.remove(otherEndpoint)
	nextEndpoint = None
	path = []
	paths = [path]
	if len(endpoints) > 1:
		nextEndpoint = otherEndpoint.getNearestMiss(endpoints, path, pixelDictionary, width)
		if nextEndpoint is not None:
			if abs(nextEndpoint.point - endpointFirst.point) < abs(nextEndpoint.point - otherEndpoint.point):
				endpointFirst = endpointFirst.otherEndpoint
				otherEndpoint = endpointFirst.otherEndpoint
	addPointToPath(path, pixelDictionary, endpointFirst.point, None, width)
	addPointToPath(path, pixelDictionary, otherEndpoint.point, len(paths) - 1, width)
	oneOverEndpointWidth = 1.0 / maximumConnectionLength
	endpointTable = {}
	for endpoint in endpoints:
		addElementToPixelListFromPoint(endpoint, endpointTable, endpoint.point * oneOverEndpointWidth)
	while len(endpointTable) > 0:
		if len(endpointTable) == 1:
			if len(endpointTable.values()[0]) < 2:
				return
		endpoints = getSquareValuesFromPoint(endpointTable, otherEndpoint.point * oneOverEndpointWidth)
		nextEndpoint = otherEndpoint.getNearestMiss(endpoints, path, pixelDictionary, width)
		if nextEndpoint is None:
			path = []
			paths.append(path)
			endpoints = getListTableElements(endpointTable)
			nextEndpoint = otherEndpoint.getNearestEndpoint(endpoints)
# this commented code should be faster than the getListTableElements code, but it isn't, someday a spiral algorithim could be tried
#			endpoints = getSquareValuesFromPoint( endpointTable, otherEndpoint.point * oneOverEndpointWidth )
#			nextEndpoint = otherEndpoint.getNearestEndpoint(endpoints)
#			if nextEndpoint == None:
#				endpoints = []
#				for endpointTableValue in endpointTable.values():
#					endpoints.append( endpointTableValue[0] )
#				nextEndpoint = otherEndpoint.getNearestEndpoint(endpoints)
#				endpoints = getSquareValuesFromPoint( endpointTable, nextEndpoint.point * oneOverEndpointWidth )
#				nextEndpoint = otherEndpoint.getNearestEndpoint(endpoints)
		addPointToPath(path, pixelDictionary, nextEndpoint.point, len(paths) - 1, width)
		removeElementFromPixelListFromPoint(nextEndpoint, endpointTable, nextEndpoint.point * oneOverEndpointWidth)
		otherEndpoint = nextEndpoint.otherEndpoint
		addPointToPath(path, pixelDictionary, otherEndpoint.point, len(paths) - 1, width)
		removeElementFromPixelListFromPoint(otherEndpoint, endpointTable, otherEndpoint.point * oneOverEndpointWidth)
	return paths

def getPlaneDot( vec3First, vec3Second ):
	"""Get the dot product of the x and y components of a pair of Vector3s."""
	return vec3First.x * vec3Second.x + vec3First.y * vec3Second.y

def getPluralString( number, suffix ):
	"""Get the plural string."""
	if number == 1:
		return '1 %s' % suffix
	return '%s %ss' % ( number, suffix )

def getPointsByHorizontalDictionary(width, xIntersectionsDictionary):
	"""Get points from the horizontalXIntersectionsDictionary."""
	points = []
	xIntersectionsDictionaryKeys = xIntersectionsDictionary.keys()
	xIntersectionsDictionaryKeys.sort()
	for xIntersectionsDictionaryKey in xIntersectionsDictionaryKeys:
		for xIntersection in xIntersectionsDictionary[xIntersectionsDictionaryKey]:
			points.append(complex(xIntersection, xIntersectionsDictionaryKey * width))
	return points

def getPointsByVerticalDictionary(width, xIntersectionsDictionary):
	"""Get points from the verticalXIntersectionsDictionary."""
	points = []
	xIntersectionsDictionaryKeys = xIntersectionsDictionary.keys()
	xIntersectionsDictionaryKeys.sort()
	for xIntersectionsDictionaryKey in xIntersectionsDictionaryKeys:
		for xIntersection in xIntersectionsDictionary[xIntersectionsDictionaryKey]:
			points.append(complex(xIntersectionsDictionaryKey * width, xIntersection))
	return points

def getPointsRoundZAxis( planeAngle, points ):
	"""Get points rotated by the plane angle"""
	planeArray = []
	for point in points:
		planeArray.append( planeAngle * point )
	return planeArray

def getPointPlusSegmentWithLength( length, point, segment ):
	"""Get point plus a segment scaled to a given length."""
	return segment * length / abs(segment) + point

def getRandomComplex(begin, end):
	"""Get random complex."""
	endMinusBegin = end - begin
	return begin + complex(random.random() * endMinusBegin.real, random.random() * endMinusBegin.imag)

def getRank(width):
	"""Get the rank which is 0 at 1 and increases by three every power of ten."""
	return int(math.floor(3.0 * math.log10(width)))

def getRotatedWiddershinsQuarterAroundZAxis(vector3):
	"""Get Vector3 rotated a quarter widdershins turn around Z axis."""
	return Vector3(-vector3.y, vector3.x, vector3.z)

def getRoundedPoint(point):
	"""Get point with each component rounded."""
	return Vector3(round(point.x), round( point.y ), round(point.z))

def getRoundedToPlaces(decimalPlaces, number):
	"""Get number rounded to a number of decimal places."""
	decimalPlacesRounded = max(1, int(round(decimalPlaces)))
	return round(number, decimalPlacesRounded )

def getRoundedToPlacesString(decimalPlaces, number):
	"""Get number rounded to a number of decimal places as a string."""
	return str(getRoundedToPlaces(decimalPlaces, number))

def getRoundedToThreePlaces(number):
	"""Get number rounded to three places as a string."""
	return str(round(number, 3))

def getRoundZAxisByPlaneAngle( planeAngle, vector3 ):
	"""Get Vector3 rotated by a plane angle."""
	return Vector3( vector3.x * planeAngle.real - vector3.y * planeAngle.imag, vector3.x * planeAngle.imag + vector3.y * planeAngle.real, vector3.z )

def getSegmentFromPath( path, pathIndex ):
	"""Get endpoint segment from a path."""
	if len(path) < 2:
		return None
	begin = path[-1]
	end = path[-2]
	forwardEndpoint = getEndpointFromPath( path, pathIndex )
	reversePath = path[:]
	reversePath.reverse()
	reverseEndpoint = getEndpointFromPath( reversePath, pathIndex )
	return forwardEndpoint, reverseEndpoint

def getSegmentFromPoints( begin, end ):
	"""Get endpoint segment from a pair of points."""
	endpointFirst = Endpoint()
	endpointSecond = Endpoint().getFromOtherPoint( endpointFirst, end )
	endpointFirst.getFromOtherPoint( endpointSecond, begin )
	return endpointFirst, endpointSecond

def getSegmentsFromXIntersections( xIntersections, y ):
	"""Get endpoint segments from the x intersections."""
	segments = []
	end = len( xIntersections )
	if len( xIntersections ) % 2 == 1:
		end -= 1
	for xIntersectionIndex in xrange( 0, end, 2 ):
		firstX = xIntersections[ xIntersectionIndex ]
		secondX = xIntersections[ xIntersectionIndex + 1 ]
		if firstX != secondX:
			segments.append( getSegmentFromPoints( complex( firstX, y ), complex( secondX, y ) ) )
	return segments

def getSegmentsFromXIntersectionIndexes( xIntersectionIndexList, y ):
	"""Get endpoint segments from the x intersection indexes."""
	xIntersections = getXIntersectionsFromIntersections( xIntersectionIndexList )
	return getSegmentsFromXIntersections( xIntersections, y )

def getSimplifiedLoop( loop, radius ):
	"""Get loop with points inside the channel removed."""
	if len(loop) < 2:
		return loop
	simplificationMultiplication = 256
	simplificationRadius = radius / float( simplificationMultiplication )
	maximumIndex = len(loop) * simplificationMultiplication
	pointIndex = 1
	while pointIndex < maximumIndex:
		oldLoopLength = len(loop)
		loop = getHalfSimplifiedLoop( loop, simplificationRadius, 0 )
		loop = getHalfSimplifiedLoop( loop, simplificationRadius, 1 )
		simplificationRadius += simplificationRadius
		if oldLoopLength == len(loop):
			if simplificationRadius > radius:
				return getAwayPoints( loop, radius )
			else:
				simplificationRadius *= 1.5
		simplificationRadius = min( simplificationRadius, radius )
		pointIndex += pointIndex
	return getAwayPoints( loop, radius )

def getSimplifiedLoops( loops, radius ):
	"""Get the simplified loops."""
	simplifiedLoops = []
	for loop in loops:
		simplifiedLoops.append( getSimplifiedLoop( loop, radius ) )
	return simplifiedLoops

def getSimplifiedPath( path, radius ):
	"""Get path with points inside the channel removed."""
	if len(path) < 2:
		return path
	simplificationMultiplication = 256
	simplificationRadius = radius / float( simplificationMultiplication )
	maximumIndex = len(path) * simplificationMultiplication
	pointIndex = 1
	while pointIndex < maximumIndex:
		oldPathLength = len(path)
		path = getHalfSimplifiedPath( path, simplificationRadius, 0 )
		path = getHalfSimplifiedPath( path, simplificationRadius, 1 )
		simplificationRadius += simplificationRadius
		if oldPathLength == len(path):
			if simplificationRadius > radius:
				return getAwayPoints( path, radius )
			else:
				simplificationRadius *= 1.5
		simplificationRadius = min( simplificationRadius, radius )
		pointIndex += pointIndex
	return getAwayPoints( path, radius )

def getSquareIsOccupied( pixelDictionary, x, y ):
	"""Determine if a square around the x and y pixel coordinates is occupied."""
	squareValues = []
	for xStep in xrange(x - 1, x + 2):
		for yStep in xrange(y - 1, y + 2):
			stepKey = getStepKey(xStep, yStep)
			if stepKey in pixelDictionary:
				return True
	return False

def getSquareLoopWiddershins(beginComplex, endComplex):
	"""Get a square loop from the beginning to the end and back."""
	loop = [beginComplex, complex(endComplex.real, beginComplex.imag), endComplex,
            complex(beginComplex.real, endComplex.imag)]
	return loop

def getSquareValues( pixelDictionary, x, y ):
	"""Get a list of the values in a square around the x and y pixel coordinates."""
	squareValues = []
	for xStep in xrange(x - 1, x + 2):
		for yStep in xrange(y - 1, y + 2):
			stepKey = getStepKey(xStep, yStep)
			if stepKey in pixelDictionary:
				squareValues += pixelDictionary[ stepKey ]
	return squareValues

def getSquareValuesFromPoint( pixelDictionary, point ):
	"""Get a list of the values in a square around the point."""
	return getSquareValues(pixelDictionary, int(round(point.real)), int(round(point.imag)))

def getStepKey(x, y):
	"""Get step key for x and y."""
	return x, y

def getStepKeyFromPoint(point):
	"""Get step key for the point."""
	return int(round(point.real)), int(round(point.imag))

def getThreeSignificantFigures(number):
	"""Get number rounded to three significant figures as a string."""
	absoluteNumber = abs(number)
	if absoluteNumber >= 10.0:
		return getRoundedToPlacesString( 1, number )
	if absoluteNumber < 0.000000001:
		return getRoundedToPlacesString( 12, number )
	return getRoundedToPlacesString( 1 - math.floor( math.log10( absoluteNumber ) ), number )

def getTopPath(path):
	"""Get the top of the path."""
	top = -987654321.0
	for point in path:
		top = max(top, point.z)
	return top

def getTopPaths(paths):
	"""Get the top of the paths."""
	top = -987654321.0
	for path in paths:
		for point in path:
			top = max(top, point.z)
	return top

def getTransferClosestSurroundingLoop(extrusionHalfWidth, nestedRings, oldOrderedLocation, skein, threadSequence):
	"""Get and transfer the closest remaining surrounding loop."""
	if len(nestedRings) > 0:
		oldOrderedLocation.z = nestedRings[0].z
	closestDistance = 987654321987654321.0
	closestSurroundingLoop = None
	for remainingSurroundingLoop in nestedRings:
		distance = getNearestDistanceIndex(oldOrderedLocation.dropAxis(), remainingSurroundingLoop.boundary).distance
		if distance < closestDistance:
			closestDistance = distance
			closestSurroundingLoop = remainingSurroundingLoop
	nestedRings.remove(closestSurroundingLoop)
	closestSurroundingLoop.addToThreads(extrusionHalfWidth, oldOrderedLocation, skein, threadSequence)
	return closestSurroundingLoop

def getTransferredPaths( insides, loop ):
	"""Get transferred paths from inside paths."""
	transferredPaths = []
	for insideIndex in xrange( len( insides ) - 1, - 1, - 1 ):
		inside = insides[ insideIndex ]
		if isPathInsideLoop( loop, inside ):
			transferredPaths.append( inside )
			del insides[ insideIndex ]
	return transferredPaths

def getTransferredSurroundingLoops( insides, loop ):
	"""Get transferred paths from inside surrounding loops."""
	transferredSurroundings = []
	for insideIndex in xrange( len( insides ) - 1, - 1, - 1 ):
		insideSurrounding = insides[ insideIndex ]
		if isPathInsideLoop( loop, insideSurrounding.boundary ):
			transferredSurroundings.append( insideSurrounding )
			del insides[ insideIndex ]
	return transferredSurroundings

def getTranslatedComplexPath(path, translateComplex):
	"""Get the translated complex path."""
	translatedComplexPath = []
	for point in path:
		translatedComplexPath.append(point + translateComplex)
	return translatedComplexPath

def getVector3Path(complexPath, z=0.0):
	"""Get the vector3 path from the complex path."""
	vector3Path = []
	for complexPoint in complexPath:
		vector3Path.append(Vector3(complexPoint.real, complexPoint.imag, z))
	return vector3Path

def getVector3Paths(complexPaths, z=0.0):
	"""Get the vector3 paths from the complex paths."""
	vector3Paths = []
	for complexPath in complexPaths:
		vector3Paths.append(getVector3Path(complexPath, z))
	return vector3Paths

def getWiddershinsUnitPolar(angle):
	"""Get polar complex from counterclockwise angle from 1, 0."""
	return complex(math.cos(angle), math.sin(angle))

def getXIntersectionIfExists( beginComplex, endComplex, y ):
	"""Get the x intersection if it exists."""
	if ( y > beginComplex.imag ) == ( y > endComplex.imag ):
		return None
	endMinusBeginComplex = endComplex - beginComplex
	return ( y - beginComplex.imag ) / endMinusBeginComplex.imag * endMinusBeginComplex.real + beginComplex.real

def getXIntersectionsFromIntersections( xIntersectionIndexList ):
	"""Get x intersections from the x intersection index list, in other words subtract non negative intersections from negatives."""
	xIntersections = []
	fill = False
	solid = False
	solidTable = {}
	xIntersectionIndexList.sort()
	for solidX in xIntersectionIndexList:
		if solidX.index >= 0:
			toggleHashtable( solidTable, solidX.index, '' )
		else:
			fill = not fill
		oldSolid = solid
		solid = ( len( solidTable ) == 0 and fill )
		if oldSolid != solid:
			xIntersections.append( solidX.x )
	return xIntersections

def getXYComplexFromVector3(vector3):
	"""Get an xy complex from a vector3 if it exists, otherwise return None."""
	if vector3 is None:
		return None
	return vector3.dropAxis()

def getYIntersectionIfExists( beginComplex, endComplex, x ):
	"""Get the y intersection if it exists."""
	if ( x > beginComplex.real ) == ( x > endComplex.real ):
		return None
	endMinusBeginComplex = endComplex - beginComplex
	return ( x - beginComplex.real ) / endMinusBeginComplex.real * endMinusBeginComplex.imag + beginComplex.imag

def getZComponentCrossProduct( vec3First, vec3Second ):
	"""Get z component cross product of a pair of Vector3s."""
	return vec3First.x * vec3Second.y - vec3First.y * vec3Second.x

def isInsideOtherLoops( loopIndex, loops ):
	"""Determine if a loop in a list is inside another loop in that list."""
	return isPathInsideLoops( loops[ : loopIndex ] + loops[loopIndex + 1 :], loops[loopIndex] )

def isLineIntersectingInsideXSegment( beginComplex, endComplex, segmentFirstX, segmentSecondX, y ):
	"""Determine if the line is crossing inside the x segment."""
	xIntersection = getXIntersectionIfExists( beginComplex, endComplex, y )
	if xIntersection is None:
		return False
	if xIntersection < min( segmentFirstX, segmentSecondX ):
		return False
	return xIntersection <= max( segmentFirstX, segmentSecondX )

def isLineIntersectingLoop( loop, pointBegin, pointEnd ):
	"""Determine if the line is intersecting loops."""
	normalizedSegment = pointEnd - pointBegin
	normalizedSegmentLength = abs( normalizedSegment )
	if normalizedSegmentLength > 0.0:
		normalizedSegment /= normalizedSegmentLength
		segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
		pointBeginRotated = segmentYMirror * pointBegin
		pointEndRotated = segmentYMirror * pointEnd
		if isLoopIntersectingInsideXSegment( loop, pointBeginRotated.real, pointEndRotated.real, segmentYMirror, pointBeginRotated.imag ):
			return True
	return False

def isLineIntersectingLoops( loops, pointBegin, pointEnd ):
	"""Determine if the line is intersecting loops."""
	normalizedSegment = pointEnd - pointBegin
	normalizedSegmentLength = abs( normalizedSegment )
	if normalizedSegmentLength > 0.0:
		normalizedSegment /= normalizedSegmentLength
		segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
		pointBeginRotated = segmentYMirror * pointBegin
		pointEndRotated = segmentYMirror * pointEnd
		if isLoopListIntersectingInsideXSegment( loops, pointBeginRotated.real, pointEndRotated.real, segmentYMirror, pointBeginRotated.imag ):
			return True
	return False

def isLoopIntersectingInsideXSegment( loop, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	"""Determine if the loop is intersecting inside the x segment."""
	rotatedLoop = getPointsRoundZAxis( segmentYMirror, loop )
	for pointIndex in xrange( len( rotatedLoop ) ):
		pointFirst = rotatedLoop[pointIndex]
		pointSecond = rotatedLoop[ (pointIndex + 1) % len( rotatedLoop ) ]
		if isLineIntersectingInsideXSegment( pointFirst, pointSecond, segmentFirstX, segmentSecondX, y ):
			return True
	return False

def isLoopIntersectingLoop( loop, otherLoop ):
	"""Determine if the loop is intersecting the other loop."""
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if isLineIntersectingLoop( otherLoop, pointBegin, pointEnd ):
			return True
	return False

def isLoopIntersectingLoops( loop, otherLoops ):
	"""Determine if the loop is intersecting other loops."""
	for pointIndex in xrange(len(loop)):
		pointBegin = loop[pointIndex]
		pointEnd = loop[(pointIndex + 1) % len(loop)]
		if isLineIntersectingLoops( otherLoops, pointBegin, pointEnd ):
			return True
	return False

def isLoopListIntersectingInsideXSegment( loopList, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	"""Determine if the loop list is crossing inside the x segment."""
	for alreadyFilledLoop in loopList:
		if isLoopIntersectingInsideXSegment( alreadyFilledLoop, segmentFirstX, segmentSecondX, segmentYMirror, y ):
			return True
	return False

def isLoopListIntersecting(loops):
	"""Determine if a loop in the list is intersecting the other loops."""
	for loopIndex in xrange(len(loops) - 1):
		loop = loops[loopIndex]
		if isLoopIntersectingLoops(loop, loops[loopIndex + 1 :]):
			return True
	return False

def isPathEntirelyInsideLoop(loop, path):
	"""Determine if a path is entirely inside another loop."""
	for point in path:
		if not isPointInsideLoop(loop, point):
			return False
	return True

def isPathEntirelyInsideLoops(loops, path):
	"""Determine if a path is entirely inside another loop in a list."""
	for loop in loops:
		if isPathEntirelyInsideLoop(loop, path):
			return True
	return False

def isPathInsideLoop(loop, path):
	"""Determine if a path is inside another loop."""
	return isPointInsideLoop(loop, getLeftPoint(path))

def isPathInsideLoops(loops, path):
	"""Determine if a path is inside another loop in a list."""
	for loop in loops:
		if isPathInsideLoop(loop, path):
			return True
	return False

def isPixelTableIntersecting( bigTable, littleTable, maskTable = {} ):
	"""Add path to the pixel table."""
	littleTableKeys = littleTable.keys()
	for littleTableKey in littleTableKeys:
		if littleTableKey not in maskTable:
			if littleTableKey in bigTable:
				return True
	return False

def isPointInsideLoop(loop, point):
	"""Determine if a point is inside another loop."""
	return getNumberOfIntersectionsToLeft(loop, point) % 2 == 1

def isSegmentCompletelyInX( segment, xFirst, xSecond ):
	"""Determine if the segment overlaps within x."""
	segmentFirstX = segment[0].point.real
	segmentSecondX = segment[1].point.real
	if max( segmentFirstX, segmentSecondX ) > max( xFirst, xSecond ):
		return False
	return min( segmentFirstX, segmentSecondX ) >= min( xFirst, xSecond )

def isWiddershins(polygonComplex):
	"""Determine if the complex polygon goes round in the widdershins direction."""
	return getAreaLoop(polygonComplex) > 0.0

def isWithinChannel( channelRadius, pointIndex, loop ):
	"""Determine if the the point is within the channel between two adjacent points."""
	point = loop[pointIndex]
	behindSegmentComplex = loop[(pointIndex + len(loop) - 1) % len(loop)] - point
	behindSegmentComplexLength = abs( behindSegmentComplex )
	if behindSegmentComplexLength < channelRadius:
		return True
	aheadSegmentComplex = loop[(pointIndex + 1) % len(loop)] - point
	aheadSegmentComplexLength = abs( aheadSegmentComplex )
	if aheadSegmentComplexLength < channelRadius:
		return True
	behindSegmentComplex /= behindSegmentComplexLength
	aheadSegmentComplex /= aheadSegmentComplexLength
	absoluteZ = getDotProductPlusOne( aheadSegmentComplex, behindSegmentComplex )
	if behindSegmentComplexLength * absoluteZ < channelRadius:
		return True
	return aheadSegmentComplexLength * absoluteZ < channelRadius

def isXSegmentIntersectingPath( path, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	"""Determine if a path is crossing inside the x segment."""
	rotatedPath = getPointsRoundZAxis( segmentYMirror, path )
	for pointIndex in xrange( len( rotatedPath ) - 1 ):
		pointFirst = rotatedPath[pointIndex]
		pointSecond = rotatedPath[pointIndex + 1]
		if isLineIntersectingInsideXSegment( pointFirst, pointSecond, segmentFirstX, segmentSecondX, y ):
			return True
	return False

def isXSegmentIntersectingPaths( paths, segmentFirstX, segmentSecondX, segmentYMirror, y ):
	"""Determine if a path list is crossing inside the x segment."""
	for path in paths:
		if isXSegmentIntersectingPath( path, segmentFirstX, segmentSecondX, segmentYMirror, y ):
			return True
	return False

def joinSegmentTables( fromTable, intoTable ):
	"""Join both segment tables and put the join into the intoTable."""
	intoTableKeys = intoTable.keys()
	fromTableKeys = fromTable.keys()
	joinedKeyTable = {}
	concatenatedTableKeys = intoTableKeys + fromTableKeys
	for concatenatedTableKey in concatenatedTableKeys:
		joinedKeyTable[ concatenatedTableKey ] = None
	joinedKeys = joinedKeyTable.keys()
	joinedKeys.sort()
	for joinedKey in joinedKeys:
		xIntersectionIndexList = []
		if joinedKey in intoTable:
			addXIntersectionIndexesFromSegments( 0, intoTable[ joinedKey ], xIntersectionIndexList )
		if joinedKey in fromTable:
			addXIntersectionIndexesFromSegments( 1, fromTable[ joinedKey ], xIntersectionIndexList )
		xIntersections = getJoinOfXIntersectionIndexes( xIntersectionIndexList )
		lineSegments = getSegmentsFromXIntersections( xIntersections, joinedKey )
		if len( lineSegments ) > 0:
			intoTable[ joinedKey ] = lineSegments
		else:
			print('This should never happen, there are no line segments in joinSegments in euclidean')

def joinXIntersectionsTables( fromTable, intoTable ):
	"""Join both XIntersections tables and put the join into the intoTable."""
	joinedKeyTable = {}
	concatenatedTableKeys = fromTable.keys() + intoTable.keys()
	for concatenatedTableKey in concatenatedTableKeys:
		joinedKeyTable[ concatenatedTableKey ] = None
	for joinedKey in joinedKeyTable.keys():
		xIntersectionIndexList = []
		if joinedKey in intoTable:
			addXIntersectionIndexesFromXIntersections( 0, xIntersectionIndexList, intoTable[ joinedKey ] )
		if joinedKey in fromTable:
			addXIntersectionIndexesFromXIntersections( 1, xIntersectionIndexList, fromTable[ joinedKey ] )
		xIntersections = getJoinOfXIntersectionIndexes( xIntersectionIndexList )
		if len( xIntersections ) > 0:
			intoTable[ joinedKey ] = xIntersections
		else:
			print('This should never happen, there are no line segments in joinSegments in euclidean')

def overwriteDictionary(fromDictionary, keys, toDictionary):
	"""Overwrite the dictionary."""
	for key in keys:
		if key in fromDictionary:
			toDictionary[key] = fromDictionary[key]

def removeElementFromDictionary(dictionary, key):
	"""Remove element from the dictionary."""
	if key in dictionary:
		del dictionary[key]

def removeElementFromListTable(element, key, listDictionary):
	"""Remove an element from the list table."""
	if key not in listDictionary:
		return
	elementList = listDictionary[key]
	if len( elementList ) < 2:
		del listDictionary[key]
		return
	if element in elementList:
		elementList.remove(element)

def removeElementFromPixelListFromPoint( element, pixelDictionary, point ):
	"""Remove an element from the pixel list."""
	stepKey = getStepKeyFromPoint(point)
	removeElementFromListTable( element, stepKey, pixelDictionary )

def removeElementsFromDictionary(dictionary, keys):
	"""Remove list from the dictionary."""
	for key in keys:
		removeElementFromDictionary(dictionary, key)

def removePrefixFromDictionary( dictionary, prefix ):
	"""Remove the attributes starting with the prefix from the dictionary."""
	for key in dictionary.keys():
		if key.startswith( prefix ):
			del dictionary[key]

def removePixelTableFromPixelTable( pixelDictionaryToBeRemoved, pixelDictionaryToBeRemovedFrom ):
	"""Remove pixel from the pixel table."""
	removeElementsFromDictionary( pixelDictionaryToBeRemovedFrom, pixelDictionaryToBeRemoved.keys() )

def removeTrueFromDictionary(dictionary, key):
	"""Remove key from the dictionary in the value is true."""
	if key in dictionary:
		if getBooleanFromValue(dictionary[key]):
			del dictionary[key]

def removeTrueListFromDictionary( dictionary, keys ):
	"""Remove list from the dictionary in the value is true."""
	for key in keys:
		removeTrueFromDictionary( dictionary, key )

def subtractXIntersectionsTable( subtractFromTable, subtractTable ):
	"""Subtract the subtractTable from the subtractFromTable."""
	subtractFromTableKeys = subtractFromTable.keys()
	subtractFromTableKeys.sort()
	for subtractFromTableKey in subtractFromTableKeys:
		xIntersectionIndexList = []
		addXIntersectionIndexesFromXIntersections( - 1, xIntersectionIndexList, subtractFromTable[ subtractFromTableKey ] )
		if subtractFromTableKey in subtractTable:
			addXIntersectionIndexesFromXIntersections( 0, xIntersectionIndexList, subtractTable[ subtractFromTableKey ] )
		xIntersections = getXIntersectionsFromIntersections( xIntersectionIndexList )
		if len( xIntersections ) > 0:
			subtractFromTable[ subtractFromTableKey ] = xIntersections
		else:
			del subtractFromTable[ subtractFromTableKey ]

def swapList( elements, indexBegin, indexEnd ):
	"""Swap the list elements."""
	elements[ indexBegin ], elements[ indexEnd ] = elements[ indexEnd ], elements[ indexBegin ]

def toggleHashtable( hashtable, key, value ):
	"""Toggle a hashtable between having and not having a key."""
	if key in hashtable:
		del hashtable[key]
	else:
		hashtable[key] = value

def transferClosestFillLoop(extrusionHalfWidth, oldOrderedLocation, remainingFillLoops, skein):
	"""Transfer the closest remaining fill loop."""
	closestDistance = 987654321987654321.0
	closestFillLoop = None
	for remainingFillLoop in remainingFillLoops:
		distance = getNearestDistanceIndex(oldOrderedLocation.dropAxis(), remainingFillLoop).distance
		if distance < closestDistance:
			closestDistance = distance
			closestFillLoop = remainingFillLoop
	newClosestFillLoop = getLoopInsideContainingLoop(closestFillLoop, remainingFillLoops)
	while newClosestFillLoop is not None:
		closestFillLoop = newClosestFillLoop
		newClosestFillLoop = getLoopInsideContainingLoop(closestFillLoop, remainingFillLoops)
	remainingFillLoops.remove(closestFillLoop)
	addToThreadsFromLoop(extrusionHalfWidth, 'loop', closestFillLoop[:], oldOrderedLocation, skein)

def transferClosestPath( oldOrderedLocation, remainingPaths, skein ):
	"""Transfer the closest remaining path."""
	closestDistance = 987654321987654321.0
	closestPath = None
	oldOrderedLocationComplex = oldOrderedLocation.dropAxis()
	for remainingPath in remainingPaths:
		distance = min( abs( oldOrderedLocationComplex - remainingPath[0] ), abs( oldOrderedLocationComplex - remainingPath[-1] ) )
		if distance < closestDistance:
			closestDistance = distance
			closestPath = remainingPath
	remainingPaths.remove( closestPath )
	skein.addGcodeFromThreadZ( closestPath, oldOrderedLocation.z )
	oldOrderedLocation.x = closestPath[-1].real
	oldOrderedLocation.y = closestPath[-1].imag

def transferClosestPaths(oldOrderedLocation, remainingPaths, skein):
	"""Transfer the closest remaining paths."""
	while len(remainingPaths) > 0:
		transferClosestPath(oldOrderedLocation, remainingPaths, skein)

def transferPathsToSurroundingLoops(nestedRings, paths):
	"""Transfer paths to surrounding loops."""
	for nestedRing in nestedRings:
		nestedRing.transferPaths(paths)

def translateVector3Path(path, translateVector3):
	"""Translate the vector3 path."""
	for point in path:
		point.setToVector3(point + translateVector3)

def translateVector3Paths(paths, translateVector3):
	"""Translate the vector3 paths."""
	for path in paths:
		translateVector3Path(path, translateVector3)

def unbuckleBasis( basis, maximumUnbuckling, normal ):
	"""Unbuckle space."""
	normalDot = basis.dot( normal )
	dotComplement = math.sqrt( 1.0 - normalDot * normalDot )
	unbuckling = maximumUnbuckling
	if dotComplement > 0.0:
		unbuckling = min( 1.0 / dotComplement, maximumUnbuckling )
	basis.setToVector3( basis * unbuckling )


class DistanceIndex:
	"""A class to hold the distance and the index of the loop."""
	def __init__( self, distance, index ):
		self.distance = distance
		self.index = index

	def __repr__(self):
		"""Get the string representation of this distance index."""
		return '%s, %s' % ( self.distance, self.index )


class Endpoint:
	"""The endpoint of a segment."""
	def __repr__(self):
		"""Get the string representation of this Endpoint."""
		return 'Endpoint %s, %s' % ( self.point, self.otherEndpoint.point )

	def getFromOtherPoint( self, otherEndpoint, point ):
		"""Initialize from other endpoint."""
		self.otherEndpoint = otherEndpoint
		self.point = point
		return self

	def getNearestEndpoint( self, endpoints ):
		"""Get nearest endpoint."""
		smallestDistance = 987654321987654321.0
		nearestEndpoint = None
		for endpoint in endpoints:
			distance = abs( self.point - endpoint.point )
			if distance < smallestDistance:
				smallestDistance = distance
				nearestEndpoint = endpoint
		return nearestEndpoint

	def getNearestMiss(self, endpoints, path, pixelDictionary, width):
		"""Get the nearest endpoint which the segment to that endpoint misses the other extrusions."""
		pathMaskTable = {}
		smallestDistance = 987654321.0
		penultimateMinusPoint = complex(0.0, 0.0)
		if len(path) > 1:
			penultimatePoint = path[-2]
			addSegmentToPixelTable(penultimatePoint, self.point, pathMaskTable, 0, 0, width)
			penultimateMinusPoint = penultimatePoint - self.point
			if abs(penultimateMinusPoint) > 0.0:
				penultimateMinusPoint /= abs(penultimateMinusPoint)
		for endpoint in endpoints:
			endpoint.segment = endpoint.point - self.point
			endpoint.segmentLength = abs(endpoint.segment)
			if endpoint.segmentLength <= 0.0:
#				print('This should never happen, the endpoints are touching')
#				print( endpoint )
#				print(path)
				return endpoint
		endpoints.sort(compareSegmentLength)
		for endpoint in endpoints[: 15]: # increasing the number of searched endpoints increases the search time, with 20 fill took 600 seconds for cilinder.gts, with 10 fill took 533 seconds
			normalizedSegment = endpoint.segment / endpoint.segmentLength
			isOverlappingSelf = getDotProduct(penultimateMinusPoint, normalizedSegment) > 0.9
			if not isOverlappingSelf:
				if len(path) > 2:
					segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
					pointRotated = segmentYMirror * self.point
					endpointPointRotated = segmentYMirror * endpoint.point
					if isXSegmentIntersectingPath(path[max(0, len(path) - 21) : -1], pointRotated.real, endpointPointRotated.real, segmentYMirror, pointRotated.imag):
						isOverlappingSelf = True
			if not isOverlappingSelf:
				totalMaskTable = pathMaskTable.copy()
				addSegmentToPixelTable(endpoint.point, endpoint.otherEndpoint.point, totalMaskTable, 0, 0, width)
				segmentTable = {}
				addSegmentToPixelTable(self.point, endpoint.point, segmentTable, 0, 0, width)
				if not isPixelTableIntersecting(pixelDictionary, segmentTable, totalMaskTable):
					return endpoint
		return None

	def getNearestMissCheckEndpointPath( self, endpoints, path, pixelDictionary, width ):
		"""Get the nearest endpoint which the segment to that endpoint misses the other extrusions, also checking the path of the endpoint."""
		pathMaskTable = {}
		smallestDistance = 987654321.0
		penultimateMinusPoint = complex(0.0, 0.0)
		if len(path) > 1:
			penultimatePoint = path[-2]
			addSegmentToPixelTable( penultimatePoint, self.point, pathMaskTable, 0, 0, width )
			penultimateMinusPoint = penultimatePoint - self.point
			if abs(penultimateMinusPoint) > 0.0:
				penultimateMinusPoint /= abs(penultimateMinusPoint)
		for endpoint in endpoints:
			endpoint.segment = endpoint.point - self.point
			endpoint.segmentLength = abs(endpoint.segment)
			if endpoint.segmentLength <= 0.0:
#				print('This should never happen, the endpoints are touching')
#				print( endpoint )
#				print(path)
				return endpoint
		endpoints.sort( compareSegmentLength )
		for endpoint in endpoints[ : 15 ]: # increasing the number of searched endpoints increases the search time, with 20 fill took 600 seconds for cilinder.gts, with 10 fill took 533 seconds
			normalizedSegment = endpoint.segment / endpoint.segmentLength
			isOverlappingSelf = getDotProduct( penultimateMinusPoint, normalizedSegment ) > 0.9
			if not isOverlappingSelf:
				if len(path) > 2:
					segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
					pointRotated = segmentYMirror * self.point
					endpointPointRotated = segmentYMirror * endpoint.point
					if isXSegmentIntersectingPath( path[ max( 0, len(path) - 21 ) : - 1 ], pointRotated.real, endpointPointRotated.real, segmentYMirror, pointRotated.imag ):
						isOverlappingSelf = True
				endpointPath = endpoint.path
				if len( endpointPath ) > 2:
					segmentYMirror = complex(normalizedSegment.real, -normalizedSegment.imag)
					pointRotated = segmentYMirror * self.point
					endpointPointRotated = segmentYMirror * endpoint.point
					if isXSegmentIntersectingPath( endpointPath, pointRotated.real, endpointPointRotated.real, segmentYMirror, pointRotated.imag ):
						isOverlappingSelf = True
			if not isOverlappingSelf:
				totalMaskTable = pathMaskTable.copy()
				addSegmentToPixelTable( endpoint.point, endpoint.otherEndpoint.point, totalMaskTable, 0, 0, width )
				segmentTable = {}
				addSegmentToPixelTable( self.point, endpoint.point, segmentTable, 0, 0, width )
				if not isPixelTableIntersecting( pixelDictionary, segmentTable, totalMaskTable ):
					return endpoint
		return None


class LoopLayer:
	"""Loops with a z."""
	def __init__(self, z):
		self.loops = []
		self.z = z

	def __repr__(self):
		"""Get the string representation of this loop layer."""
		return '%s, %s' % ( self.z, self.loops )


class NestedRing:
	"""A nested ring."""
	def __init__(self):
		"""Initialize."""
		self.boundary = []
		self.innerNestedRings = None

	def __repr__(self):
		"""Get the string representation of this surrounding loop."""
		return str(self.__dict__)

	def addFlattenedNestedRings(self, flattenedNestedRings):
		"""Add flattened nested rings."""
		flattenedNestedRings.append(self)
		for innerNestedRing in self.innerNestedRings:
			flattenedNestedRings += getFlattenedNestedRings(innerNestedRing.innerNestedRings)

	def getFromInsideSurroundings(self, inputSurroundingInsides):
		"""Initialize from inside surrounding loops."""
		transferredSurroundings = getTransferredSurroundingLoops(inputSurroundingInsides, self.boundary)
		self.innerNestedRings = getOrderedNestedRings(transferredSurroundings)
		return self


class NestedBand(NestedRing):
	"""A loop that surrounds paths."""
	def __init__(self):
		"""Initialize."""
		NestedRing.__init__(self)
		self.extraLoops = []
		self.infillPaths = []
#		self.lastExistingFillLoops = None
		self.lastFillLoops = None
		self.loop = None
		self.penultimateFillLoops = []
		self.perimeterPaths = []
		self.z = None

	def __repr__(self):
		"""Get the string representation of this surrounding loop."""
		stringRepresentation = 'boundary\n%s\n' % self.boundary
		stringRepresentation += 'loop\n%s\n' % self.loop
		stringRepresentation += 'inner nested rings\n%s\n' % self.innerNestedRings
		stringRepresentation += 'infillPaths\n'
		for infillPath in self.infillPaths:
			stringRepresentation += 'infillPath\n%s\n' % infillPath
		stringRepresentation += 'perimeterPaths\n'
		for perimeterPath in self.perimeterPaths:
			stringRepresentation += 'perimeterPath\n%s\n' % perimeterPath
		return stringRepresentation + '\n'

	def addToBoundary(self, vector3):
		"""Add vector3 to boundary."""
		self.boundary.append(vector3.dropAxis())
		self.z = vector3.z

	def addToLoop(self, vector3):
		"""Add vector3 to loop."""
		if self.loop is None:
			self.loop = []
		self.loop.append(vector3.dropAxis())
		self.z = vector3.z

	def addPerimeterInner(self, extrusionHalfWidth, oldOrderedLocation, skein, threadSequence):
		"""Add to the perimeter and the inner island."""
		if self.loop is None:
			skein.distanceFeedRate.addLine('(<perimeterPath>)')
			transferClosestPaths(oldOrderedLocation, self.perimeterPaths[:], skein)
			skein.distanceFeedRate.addLine('(</perimeterPath>)')
		else:
			addToThreadsFromLoop(extrusionHalfWidth, 'perimeter', self.loop[:], oldOrderedLocation, skein)
		skein.distanceFeedRate.addLine('(</boundaryPerimeter>)')
		addToThreadsRemove(extrusionHalfWidth, self.innerNestedRings[:], oldOrderedLocation, skein, threadSequence)

	def addToThreads(self, extrusionHalfWidth, oldOrderedLocation, skein, threadSequence):
		"""Add to paths from the last location. perimeter>inner >fill>paths or fill> perimeter>inner >paths"""
		addSurroundingLoopBeginning(skein.distanceFeedRate, self.boundary, self.z)
		threadFunctionDictionary = {
			'infill' : self.transferInfillPaths, 'loops' : self.transferClosestFillLoops, 'perimeter' : self.addPerimeterInner}
		for threadType in threadSequence:
			threadFunctionDictionary[threadType](extrusionHalfWidth, oldOrderedLocation, skein, threadSequence)
		skein.distanceFeedRate.addLine('(</nestedRing>)')

	def getFillLoops(self, penultimateFillLoops):
		"""Get last fill loops from the outside loop and the loops inside the inside loops."""
		fillLoops = self.getLoopsToBeFilled()[:]
		surroundingBoundaries = self.getSurroundingBoundaries()
		withinLoops = []
		if penultimateFillLoops is None:
			penultimateFillLoops = self.penultimateFillLoops
		for penultimateFillLoop in penultimateFillLoops:
			if len(penultimateFillLoop) > 2:
				if getIsInFilledRegion(surroundingBoundaries, penultimateFillLoop[0]):
					withinLoops.append(penultimateFillLoop)
		if not getIsInFilledRegionByPaths(self.penultimateFillLoops, fillLoops):
			fillLoops += self.penultimateFillLoops
		for nestedRing in self.innerNestedRings:
			fillLoops += getFillOfSurroundings(nestedRing.innerNestedRings, penultimateFillLoops)
		return fillLoops
#
#	def getLastExistingFillLoops(self):
#		'Get last existing fill loops.'
#		lastExistingFillLoops = self.lastExistingFillLoops[:]
#		for nestedRing in self.innerNestedRings:
#			lastExistingFillLoops += nestedRing.getLastExistingFillLoops()
#		return lastExistingFillLoops

	def getLoopsToBeFilled(self):
		"""Get last fill loops from the outside loop and the loops inside the inside loops."""
		if self.lastFillLoops is None:
			return self.getSurroundingBoundaries()
		return self.lastFillLoops

	def getSurroundingBoundaries(self):
		"""Get the boundary of the surronding loop plus any boundaries of the innerNestedRings."""
		surroundingBoundaries = [self.boundary]
		for nestedRing in self.innerNestedRings:
			surroundingBoundaries.append(nestedRing.boundary)
		return surroundingBoundaries

	def transferClosestFillLoops(self, extrusionHalfWidth, oldOrderedLocation, skein, threadSequence):
		"""Transfer closest fill loops."""
		if len( self.extraLoops ) < 1:
			return
		remainingFillLoops = self.extraLoops[:]
		while len( remainingFillLoops ) > 0:
			transferClosestFillLoop(extrusionHalfWidth, oldOrderedLocation, remainingFillLoops, skein)

	def transferInfillPaths(self, extrusionHalfWidth, oldOrderedLocation, skein, threadSequence):
		"""Transfer the infill paths."""
		transferClosestPaths(oldOrderedLocation, self.infillPaths[:], skein)

	def transferPaths(self, paths):
		"""Transfer paths."""
		for nestedRing in self.innerNestedRings:
			transferPathsToSurroundingLoops(nestedRing.innerNestedRings, paths)
		self.infillPaths = getTransferredPaths(paths, self.boundary)


class PathZ:
	"""Complex path with a z."""
	def __init__( self, z ):
		self.path = []
		self.z = z

	def __repr__(self):
		"""Get the string representation of this path z."""
		return '%s, %s' % ( self.z, self.path )


class ProjectiveSpace:
	"""Class to define a projective space."""
	def __init__( self, basisX = Vector3(1.0, 0.0, 0.0), basisY = Vector3( 0.0, 1.0, 0.0 ), basisZ = Vector3(0.0, 0.0, 1.0) ):
		"""Initialize the basis vectors."""
		self.basisX = basisX
		self.basisY = basisY
		self.basisZ = basisZ

	def __repr__(self):
		"""Get the string representation of this ProjectivePlane."""
		return '%s, %s, %s' % ( self.basisX, self.basisY, self.basisZ )

	def getByBasisXZ( self, basisX, basisZ ):
		"""Get by x basis x and y basis."""
		self.basisX = basisX
		self.basisZ = basisZ
		self.basisX.normalize()
		self.basisY = basisZ.cross(self.basisX)
		self.basisY.normalize()
		return self

	def getByBasisZFirst(self, basisZ, firstVector3):
		"""Get by basisZ and first."""
		self.basisZ = basisZ
		self.basisY = basisZ.cross(firstVector3)
		self.basisY.normalize()
		self.basisX = self.basisY.cross(self.basisZ)
		self.basisX.normalize()
		return self

	def getByBasisZTop(self, basisZ, top):
		"""Get by basisZ and top."""
		return self.getByBasisXZ(top.cross(basisZ), basisZ)

	def getByLatitudeLongitude( self, viewpointLatitude, viewpointLongitude ):
		"""Get by latitude and longitude."""
		longitudeComplex = getWiddershinsUnitPolar( math.radians( 90.0 - viewpointLongitude ) )
		viewpointLatitudeRatio = getWiddershinsUnitPolar( math.radians( viewpointLatitude ) )
		basisZ = Vector3( viewpointLatitudeRatio.imag * longitudeComplex.real, viewpointLatitudeRatio.imag * longitudeComplex.imag, viewpointLatitudeRatio.real )
		return self.getByBasisXZ( Vector3( - longitudeComplex.imag, longitudeComplex.real, 0.0 ), basisZ )

	def getByTilt( self, tilt ):
		"""Get by latitude and longitude."""
		xPlaneAngle = getWiddershinsUnitPolar( tilt.real )
		self.basisX = Vector3( xPlaneAngle.real, 0.0,  xPlaneAngle.imag )
		yPlaneAngle = getWiddershinsUnitPolar( tilt.imag )
		self.basisY = Vector3( 0.0,  yPlaneAngle.real, yPlaneAngle.imag )
		self.basisZ = self.basisX.cross(self.basisY)
		return self

	def getComplexByComplex( self, pointComplex ):
		"""Get complex by complex point."""
		return self.basisX.dropAxis() * pointComplex.real + self.basisY.dropAxis() * pointComplex.imag

	def getCopy(self):
		"""Get copy."""
		return ProjectiveSpace( self.basisX, self.basisY, self.basisZ )

	def getDotComplex(self, point):
		"""Get the dot complex."""
		return complex( point.dot(self.basisX), point.dot(self.basisY) )

	def getDotVector3(self, point):
		"""Get the dot vector3."""
		return Vector3(point.dot(self.basisX), point.dot(self.basisY), point.dot(self.basisZ))

	def getNextSpace( self, nextNormal ):
		"""Get next space by next normal."""
		nextSpace = self.getCopy()
		nextSpace.normalize()
		dotNext = nextSpace.basisZ.dot( nextNormal )
		if dotNext > 0.999999:
			return nextSpace
		if dotNext < - 0.999999:
			nextSpace.basisX = - nextSpace.basisX
			return nextSpace
		crossNext = nextSpace.basisZ.cross( nextNormal )
		oldBasis = ProjectiveSpace().getByBasisZTop( nextSpace.basisZ, crossNext )
		newBasis = ProjectiveSpace().getByBasisZTop( nextNormal, crossNext )
		nextSpace.basisX = newBasis.getVector3ByPoint( oldBasis.getDotVector3( nextSpace.basisX ) )
		nextSpace.basisY = newBasis.getVector3ByPoint( oldBasis.getDotVector3( nextSpace.basisY ) )
		nextSpace.basisZ = newBasis.getVector3ByPoint( oldBasis.getDotVector3( nextSpace.basisZ ) )
		nextSpace.normalize()
		return nextSpace

	def getSpaceByXYScaleAngle( self, angle, scale ):
		"""Get space by angle and scale."""
		spaceByXYScaleRotation = ProjectiveSpace()
		planeAngle = getWiddershinsUnitPolar(angle)
		spaceByXYScaleRotation.basisX = self.basisX * scale.real * planeAngle.real + self.basisY * scale.imag * planeAngle.imag
		spaceByXYScaleRotation.basisY = - self.basisX * scale.real * planeAngle.imag + self.basisY * scale.imag * planeAngle.real
		spaceByXYScaleRotation.basisZ = self.basisZ
		return spaceByXYScaleRotation

	def getVector3ByPoint(self, point):
		"""Get vector3 by point."""
		return self.basisX * point.x + self.basisY * point.y + self.basisZ * point.z

	def normalize(self):
		"""Normalize."""
		self.basisX.normalize()
		self.basisY.normalize()
		self.basisZ.normalize()

	def unbuckle( self, maximumUnbuckling, normal ):
		"""Unbuckle space."""
		unbuckleBasis( self.basisX, maximumUnbuckling, normal )
		unbuckleBasis( self.basisY, maximumUnbuckling, normal )


class RotatedLoopLayer:
	"""A rotated layer."""
	def __init__( self, z ):
		self.loops = []
		self.rotation = None
		self.z = z

	def __repr__(self):
		"""Get the string representation of this rotated loop layer."""
		return '%s, %s, %s' % ( self.z, self.rotation, self.loops )

	def addXML(self, depth, output):
		"""Add the xml for this object."""
		if len( self.loops ) < 1:
			return
		if len( self.loops ) == 1:
			xml_simple_writer.addXMLFromLoopComplexZ( {}, depth, self.loops[0], output, self.z )
			return
		xml_simple_writer.addBeginXMLTag( {}, 'group', depth, output )
		for loop in self.loops:
			xml_simple_writer.addXMLFromLoopComplexZ( {}, depth + 1, loop, output, self.z )
		xml_simple_writer.addEndXMLTag('group', depth, output )

	def getCopyAtZ( self, z ):
		"""Get a raised copy."""
		raisedRotatedLoopLayer = RotatedLoopLayer(z)
		for loop in self.loops:
			raisedRotatedLoopLayer.loops.append( loop[:] )
		raisedRotatedLoopLayer.rotation = self.rotation
		return raisedRotatedLoopLayer

def getFlattenedNestedRings(nestedRings):
	"""Get flattened nested rings."""
	flattenedNestedRings = []
	for nestedRing in nestedRings:
		nestedRing.addFlattenedNestedRings(flattenedNestedRings)
	return flattenedNestedRings


class XIntersectionIndex:
	"""A class to hold the x intersection position and the index of the loop which intersected."""
	def __init__( self, index, x ):
		"""Initialize."""
		self.index = index
		self.x = x

	def __cmp__(self, other):
		"""Get comparison in order to sort x intersections in ascending order of x."""
		if self.x < other.x:
			return - 1
		return int( self.x > other.x )

	def __eq__(self, other):
		"""Determine whether this XIntersectionIndex is identical to other one."""
		if other is None:
			return False
		if other.__class__ != self.__class__:
			return False
		return self.index == other.index and self.x == other.x

	def __ne__(self, other):
		"""Determine whether this XIntersectionIndex is not identical to other one."""
		return not self.__eq__(other)

	def __repr__(self):
		"""Get the string representation of this x intersection."""
		return 'XIntersectionIndex index %s; x %s ' % ( self.index, self.x )
