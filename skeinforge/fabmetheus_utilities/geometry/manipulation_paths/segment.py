"""
Add material to support overhang or remove material at the overhang angle.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 60


def getManipulatedPaths(close, loop, prefix, sideLength, xmlElement):
	"""Get segment loop."""
	if len(loop) < 3:
		return [loop]
	path = evaluate.getPathByPrefix(getSegmentPathDefault(), prefix, xmlElement)
	if path == getSegmentPathDefault():
		return [loop]
	path = getXNormalizedVector3Path(path)
	segmentCenter = evaluate.getVector3ByPrefix(None, prefix + 'center', xmlElement)
	if euclidean.getIsWiddershinsByVector3(loop):
		path = path[: : -1]
		for point in path:
			point.x = 1.0 - point.x
			if segmentCenter is None:
				point.y = - point.y
	segmentLoop = []
	startEnd = StartEnd(len(loop), prefix, xmlElement)
	for pointIndex in xrange(len(loop)):
		if pointIndex >= startEnd.start and pointIndex < startEnd.end:
			segmentLoop += getSegmentPath(loop, path, pointIndex, segmentCenter)
		else:
			segmentLoop.append(loop[pointIndex])
	return [euclidean.getLoopWithoutCloseSequentialPoints( close, segmentLoop)]

def getRadialPath( begin, end, path, segmentCenter ):
	"""Get radial path."""
	beginComplex = begin.dropAxis()
	endComplex = end.dropAxis()
	segmentCenterComplex = segmentCenter.dropAxis()
	beginMinusCenterComplex = beginComplex - segmentCenterComplex
	endMinusCenterComplex = endComplex - segmentCenterComplex
	beginMinusCenterComplexRadius = abs( beginMinusCenterComplex )
	endMinusCenterComplexRadius = abs( endMinusCenterComplex )
	if beginMinusCenterComplexRadius == 0.0 or endMinusCenterComplexRadius == 0.0:
		return [ begin ]
	beginMinusCenterComplex /= beginMinusCenterComplexRadius
	endMinusCenterComplex /= endMinusCenterComplexRadius
	angleDifference = euclidean.getAngleDifferenceByComplex( endMinusCenterComplex, beginMinusCenterComplex )
	radialPath = []
	for point in path:
		weightEnd = point.x
		weightBegin = 1.0 - weightEnd
		weightedRadius = beginMinusCenterComplexRadius * weightBegin + endMinusCenterComplexRadius * weightEnd * ( 1.0 + point.y )
		radialComplex = weightedRadius * euclidean.getWiddershinsUnitPolar( angleDifference * point.x ) * beginMinusCenterComplex
		polygonPoint = segmentCenter + Vector3( radialComplex.real, radialComplex.imag, point.z )
		radialPath.append( polygonPoint )
	return radialPath

def getSegmentPath( loop, path, pointIndex, segmentCenter ):
	"""Get segment path."""
	centerBegin = loop[pointIndex]
	centerEnd = loop[(pointIndex + 1) % len(loop)]
	centerEndMinusBegin = centerEnd - centerBegin
	if abs( centerEndMinusBegin ) <= 0.0:
		return [ centerBegin ]
	if segmentCenter is not None:
		return getRadialPath( centerBegin, centerEnd, path, segmentCenter )
	begin = loop[(pointIndex + len(loop) - 1) % len(loop)]
	end = loop[ ( pointIndex + 2 ) % len(loop) ]
	return getWedgePath( begin, centerBegin, centerEnd, centerEndMinusBegin, end, path )

def getSegmentPathDefault():
	"""Get segment path default."""
	return [ Vector3(), Vector3( 0.0, 1.0 ) ]

def getXNormalizedVector3Path(path):
	"""Get path where the x ranges from 0 to 1."""
	if len(path) < 1:
		return path
	minimumX = path[0].x
	for point in path[1 :]:
		minimumX = min( minimumX, point.x )
	for point in path:
		point.x -= minimumX
	maximumX = path[0].x
	for point in path[1 :]:
		maximumX = max( maximumX, point.x )
	for point in path:
		point.x /= maximumX
	return path

def getWedgePath( begin, centerBegin, centerEnd, centerEndMinusBegin, end, path ):
	"""Get segment path."""
	beginComplex = begin.dropAxis()
	centerBeginComplex = centerBegin.dropAxis()
	centerEndComplex = centerEnd.dropAxis()
	endComplex = end.dropAxis()
	wedgePath = []
	centerBeginMinusBeginComplex = euclidean.getNormalized( centerBeginComplex - beginComplex )
	centerEndMinusCenterBeginComplexOriginal = centerEndComplex - centerBeginComplex
	centerEndMinusCenterBeginComplexLength = abs( centerEndMinusCenterBeginComplexOriginal )
	if centerEndMinusCenterBeginComplexLength <= 0.0:
		return [ centerBegin ]
	centerEndMinusCenterBeginComplex = centerEndMinusCenterBeginComplexOriginal / centerEndMinusCenterBeginComplexLength
	endMinusCenterEndComplex = euclidean.getNormalized( endComplex - centerEndComplex )
	widdershinsBegin = getWiddershinsAverageByVector3( centerBeginMinusBeginComplex, centerEndMinusCenterBeginComplex )
	widdershinsEnd = getWiddershinsAverageByVector3( centerEndMinusCenterBeginComplex, endMinusCenterEndComplex )
	for point in path:
		weightEnd = point.x
		weightBegin = 1.0 - weightEnd
		polygonPoint = centerBegin + centerEndMinusBegin * point.x
		weightedWiddershins = widdershinsBegin * weightBegin + widdershinsEnd * weightEnd
		polygonPoint += weightedWiddershins * point.y * centerEndMinusCenterBeginComplexLength
		polygonPoint.z += point.z
		wedgePath.append( polygonPoint )
	return wedgePath

def getWiddershinsAverageByVector3( centerMinusBeginComplex, endMinusCenterComplex ):
	"""Get the normalized average of the widdershins vectors."""
	centerMinusBeginWiddershins = Vector3( - centerMinusBeginComplex.imag, centerMinusBeginComplex.real )
	endMinusCenterWiddershins = Vector3( - endMinusCenterComplex.imag, endMinusCenterComplex.real )
	return ( centerMinusBeginWiddershins + endMinusCenterWiddershins ).getNormalized()

def processXMLElement(xmlElement):
	"""Process the xml element."""
	lineation.processXMLElementByFunction(getManipulatedPaths, xmlElement)


class StartEnd:
	"""Class to get a start through end range."""
	def __init__(self, modulo, prefix, xmlElement):
		"""Initialize."""
		self.start = evaluate.getEvaluatedInt(0, prefix + 'start', xmlElement)
		self.extent = evaluate.getEvaluatedInt(modulo - self.start, prefix + 'extent', xmlElement)
		self.end = evaluate.getEvaluatedInt(self.start + self.extent, prefix + 'end', xmlElement)
		self.revolutions = evaluate.getEvaluatedInt(1, prefix + 'revolutions', xmlElement)
		if self.revolutions > 1:
			self.end += modulo * (self.revolutions - 1)

	def __repr__(self):
		"""Get the string representation of this StartEnd."""
		return '%s, %s, %s' % (self.start, self.end, self.revolutions)
