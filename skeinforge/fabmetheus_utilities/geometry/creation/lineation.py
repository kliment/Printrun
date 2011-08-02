"""
Polygon path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getComplexByDictionary(dictionary, valueComplex):
	"""Get complex by dictionary."""
	if 'x' in dictionary:
		valueComplex = complex(euclidean.getFloatFromValue(dictionary['x']),valueComplex.imag)
	if 'y' in dictionary:
		valueComplex = complex(valueComplex.real, euclidean.getFloatFromValue(dictionary['y']))
	return valueComplex

def getComplexByDictionaryListValue(value, valueComplex):
	"""Get complex by dictionary, list or value."""
	if value.__class__ == complex:
		return value
	if value.__class__ == dict:
		return getComplexByDictionary(value, valueComplex)
	if value.__class__ == list:
		return getComplexByFloatList(value, valueComplex)
	floatFromValue = euclidean.getFloatFromValue(value)
	if floatFromValue is None:
		return valueComplex
	return complex( floatFromValue, floatFromValue )

def getComplexByFloatList( floatList, valueComplex ):
	"""Get complex by float list."""
	if len(floatList) > 0:
		valueComplex = complex(euclidean.getFloatFromValue(floatList[0]), valueComplex.imag)
	if len(floatList) > 1:
		valueComplex = complex(valueComplex.real, euclidean.getFloatFromValue(floatList[1]))
	return valueComplex

def getComplexByMultiplierPrefix( multiplier, prefix, valueComplex, xmlElement ):
	"""Get complex from multiplier, prefix and xml element."""
	if multiplier == 0.0:
		return valueComplex
	oldMultipliedValueComplex = valueComplex * multiplier
	complexByPrefix = getComplexByPrefix( prefix, oldMultipliedValueComplex, xmlElement )
	if complexByPrefix == oldMultipliedValueComplex:
		return valueComplex
	return complexByPrefix / multiplier

def getComplexByMultiplierPrefixes( multiplier, prefixes, valueComplex, xmlElement ):
	"""Get complex from multiplier, prefixes and xml element."""
	for prefix in prefixes:
		valueComplex = getComplexByMultiplierPrefix( multiplier, prefix, valueComplex, xmlElement )
	return valueComplex

def getComplexByPrefix( prefix, valueComplex, xmlElement ):
	"""Get complex from prefix and xml element."""
	value = evaluate.getEvaluatedValue(None, prefix, xmlElement)
	if value is not None:
		valueComplex = getComplexByDictionaryListValue(value, valueComplex)
	x = evaluate.getEvaluatedFloat(None, prefix + '.x', xmlElement)
	if x is not None:
		valueComplex = complex( x, getComplexIfNone( valueComplex ).imag )
	y = evaluate.getEvaluatedFloat(None, prefix + '.y', xmlElement)
	if y is not None:
		valueComplex = complex( getComplexIfNone( valueComplex ).real, y )
	return valueComplex

def getComplexByPrefixBeginEnd(prefixBegin, prefixEnd, valueComplex, xmlElement):
	"""Get complex from prefixBegin, prefixEnd and xml element."""
	valueComplex = getComplexByPrefix(prefixBegin, valueComplex, xmlElement)
	if prefixEnd in xmlElement.attributeDictionary:
		return 0.5 * getComplexByPrefix(valueComplex + valueComplex, prefixEnd, xmlElement)
	else:
		return valueComplex

def getComplexByPrefixes( prefixes, valueComplex, xmlElement ):
	"""Get complex from prefixes and xml element."""
	for prefix in prefixes:
		valueComplex = getComplexByPrefix( prefix, valueComplex, xmlElement )
	return valueComplex

def getComplexIfNone( valueComplex ):
	"""Get new complex if the original complex is none."""
	if valueComplex is None:
		return complex()
	return valueComplex

def getFloatByPrefixBeginEnd(prefixBegin, prefixEnd, valueFloat, xmlElement):
	"""Get float from prefixBegin, prefixEnd and xml element."""
	valueFloat = evaluate.getEvaluatedFloat(valueFloat, prefixBegin, xmlElement)
	if prefixEnd in xmlElement.attributeDictionary:
		return 0.5 * evaluate.getEvaluatedFloat(valueFloat + valueFloat, prefixEnd, xmlElement)
	return valueFloat

def getFloatByPrefixSide( prefix, side, xmlElement ):
	"""Get float by prefix and side."""
	floatByDenominatorPrefix = evaluate.getEvaluatedFloat(0.0, prefix, xmlElement)
	return floatByDenominatorPrefix + evaluate.getEvaluatedFloat(0.0,  prefix + 'OverSide', xmlElement ) * side

def getGeometryOutput(derivation, xmlElement):
	"""Get geometry output from paths."""
	if derivation is None:
		derivation = LineationDerivation(xmlElement)
	geometryOutput = []
	for path in derivation.target:
		sideLoop = SideLoop(path)
		geometryOutput += getGeometryOutputByLoop(sideLoop, xmlElement)
	return geometryOutput

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	return getGeometryOutput(None, xmlElement)

def getGeometryOutputByLoop( sideLoop, xmlElement ):
	"""Get geometry output by side loop."""
	sideLoop.rotate(xmlElement)
	return getGeometryOutputByManipulation( sideLoop, xmlElement )

def getGeometryOutputByManipulation( sideLoop, xmlElement ):
	"""Get geometry output by manipulation."""
	sideLoop.loop = euclidean.getLoopWithoutCloseSequentialPoints( sideLoop.close, sideLoop.loop )
	return sideLoop.getManipulationPluginLoops(xmlElement)

def getMinimumRadius( beginComplexSegmentLength, endComplexSegmentLength, radius ):
	"""Get minimum radius."""
	return min( abs(radius), 0.5 * min( beginComplexSegmentLength, endComplexSegmentLength ) )

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return LineationDerivation(xmlElement)

def getNumberOfBezierPoints(begin, end, xmlElement):
	"""Get the numberOfBezierPoints."""
	numberOfBezierPoints = int(math.ceil(0.5 * evaluate.getSidesMinimumThreeBasedOnPrecision(abs(end - begin), xmlElement)))
	return evaluate.getEvaluatedInt(numberOfBezierPoints, 'sides', xmlElement)

def getPackedGeometryOutputByLoop(sideLoop, xmlElement):
	"""Get packed geometry output by side loop."""
	sideLoop.rotate(xmlElement)
	return getGeometryOutputByManipulation(sideLoop, xmlElement)

def getRadiusAverage(radiusComplex):
	"""Get average radius from radiusComplex."""
	if radiusComplex.real == radiusComplex.imag:
		return radiusComplex.real
	return math.sqrt(radiusComplex.real * radiusComplex.imag)

def getRadiusComplex(radius, xmlElement):
	"""Get radius complex for xmlElement."""
	radius = getComplexByPrefixes(['demisize', 'radius'], radius, xmlElement)
	return getComplexByMultiplierPrefixes(2.0, ['diameter', 'size'], radius, xmlElement)

def getRadiusByPrefix(prefix, sideLength, xmlElement):
	"""Get radius by prefix."""
	radius = getFloatByPrefixSide(prefix + 'radius', sideLength, xmlElement)
	radius += 0.5 * getFloatByPrefixSide(prefix + 'diameter', sideLength, xmlElement)
	return radius + 0.5 * getFloatByPrefixSide(prefix + 'size', sideLength, xmlElement)

def getStrokeRadiusByPrefix(prefix, xmlElement):
	"""Get strokeRadius by prefix."""
	strokeRadius = getFloatByPrefixBeginEnd(prefix + 'strokeRadius', prefix + 'strokeWidth', 1.0, xmlElement )
	return getFloatByPrefixBeginEnd(prefix + 'radius', prefix + 'diameter', strokeRadius, xmlElement )

def processTargetByFunction(manipulationFunction, target):
	"""Process the target by the manipulationFunction."""
	if target.xmlObject is None:
		print('Warning, there is no object in processTargetByFunction in lineation for:')
		print(target)
		return
	geometryOutput = []
	transformedPaths = target.xmlObject.getTransformedPaths()
	for transformedPath in transformedPaths:
		sideLoop = SideLoop(transformedPath)
		sideLoop.rotate(target)
		sideLoop.loop = euclidean.getLoopWithoutCloseSequentialPoints( sideLoop.close, sideLoop.loop )
		geometryOutput += manipulationFunction( sideLoop.close, sideLoop.loop, '', sideLoop.sideLength, target )
	if len(geometryOutput) < 1:
		print('Warning, there is no geometryOutput in processTargetByFunction in lineation for:')
		print(target)
		return
	removeChildrenFromElementObject(target)
	path.convertXMLElement(geometryOutput, target)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)

def processXMLElementByFunction(manipulationFunction, xmlElement):
	"""Process the xml element by the manipulationFunction."""
	targets = evaluate.getXMLElementsByKey('target', xmlElement)
	for target in targets:
		processTargetByFunction(manipulationFunction, target)

def removeChildrenFromElementObject(xmlElement):
	"""Process the xml element by manipulationFunction."""
	xmlElement.removeChildrenFromIDNameParent()
	if xmlElement.xmlObject is not None:
		if xmlElement.parent.xmlObject is not None:
			if xmlElement.xmlObject in xmlElement.parent.xmlObject.archivableObjects:
				xmlElement.parent.xmlObject.archivableObjects.remove(xmlElement.xmlObject)

def setClosedAttribute(revolutions, xmlElement):
	"""Set the closed attribute of the xmlElement."""
	closedBoolean = evaluate.getEvaluatedBoolean(revolutions <= 1, 'closed', xmlElement)
	xmlElement.attributeDictionary['closed'] = str(closedBoolean).lower()


class LineationDerivation:
	"""Class to hold lineation variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.target = evaluate.getTransformedPathsByKey([], 'target', xmlElement)

	def __repr__(self):
		"""Get the string representation of this LineationDerivation."""
		return str(self.__dict__)


class SideLoop:
	"""Class to handle loop, side angle and side length."""
	def __init__(self, loop, sideAngle=None, sideLength=None):
		"""Initialize."""
		if sideAngle is None:
			if len(loop) > 0:
				sideAngle = 2.0 * math.pi / float(len(loop))
			else:
				sideAngle = 1.0
				print('Warning, loop has no sides in SideLoop in lineation.')
		if sideLength is None:
			if len(loop) > 0:
				sideLength = euclidean.getLoopLength(loop) / float(len(loop))
			else:
				sideLength = 1.0
				print('Warning, loop has no length in SideLoop in lineation.')
		self.loop = loop
		self.sideAngle = abs(sideAngle)
		self.sideLength = abs(sideLength)
		self.close = 0.001 * sideLength

	def getManipulationPluginLoops(self, xmlElement):
		"""Get loop manipulated by the plugins in the manipulation paths folder."""
		xmlProcessor = xmlElement.getXMLProcessor()
#		matchingPlugins = evaluate.getFromCreationEvaluatorPlugins(xmlProcessor.manipulationMatrixDictionary, xmlElement)
		matchingPlugins = evaluate.getMatchingPlugins(xmlProcessor.manipulationMatrixDictionary, xmlElement)
		matchingPlugins += evaluate.getMatchingPlugins(xmlProcessor.manipulationPathDictionary, xmlElement)
		matchingPlugins += evaluate.getMatchingPlugins(xmlProcessor.manipulationShapeDictionary, xmlElement)
		matchingPlugins.sort(evaluate.compareExecutionOrderAscending)
		loops = [self.loop]
		for matchingPlugin in matchingPlugins:
			matchingLoops = []
			prefix = matchingPlugin.__name__.replace('_', '') + '.'
			for loop in loops:
				matchingLoops += matchingPlugin.getManipulatedPaths(self.close, loop, prefix, self.sideLength, xmlElement)
			loops = matchingLoops
		return loops

	def rotate(self, xmlElement):
		"""Rotate."""
		rotation = math.radians( evaluate.getEvaluatedFloat(0.0, 'rotation', xmlElement ) )
		rotation += evaluate.getEvaluatedFloat(0.0, 'rotationOverSide', xmlElement ) * self.sideAngle
		if rotation != 0.0:
			planeRotation = euclidean.getWiddershinsUnitPolar( rotation )
			for vertex in self.loop:
				rotatedComplex = vertex.dropAxis() * planeRotation
				vertex.x = rotatedComplex.real
				vertex.y = rotatedComplex.imag
		if 'clockwise' in xmlElement.attributeDictionary:
			isClockwise = euclidean.getBooleanFromValue( evaluate.getEvaluatedValueObliviously('clockwise', xmlElement ) )
			if isClockwise == euclidean.getIsWiddershinsByVector3( self.loop ):
				self.loop.reverse()


class Spiral:
	"""Class to add a spiral."""
	def __init__(self, spiral, stepRatio):
		"""Initialize."""
		self.spiral = spiral
		if self.spiral is None:
			return
		self.spiralIncrement = self.spiral * stepRatio
		self.spiralTotal = Vector3()

	def __repr__(self):
		"""Get the string representation of this Spiral."""
		return self.spiral

	def getSpiralPoint(self, unitPolar, vector3):
		"""Add spiral to the vector."""
		if self.spiral is None:
			return vector3
		vector3 += Vector3(unitPolar.real * self.spiralTotal.x, unitPolar.imag * self.spiralTotal.y, self.spiralTotal.z)
		self.spiralTotal += self.spiralIncrement
		return vector3
