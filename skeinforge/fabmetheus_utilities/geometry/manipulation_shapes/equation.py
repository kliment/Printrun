"""
Equation for vertexes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = -100


def equate(point, returnValue):
	"""Get equation for rectangular."""
	point.setToVector3(evaluate.getVector3ByDictionaryListValue(returnValue, point))

def equatePoints(points, prefix, revolutions, xmlElement):
	"""Equate the points."""
	equateVertexesByFunction(equate, points, prefix, revolutions, xmlElement)
	equateVertexesByFunction(equateX, points, prefix, revolutions, xmlElement)
	equateVertexesByFunction(equateY, points, prefix, revolutions, xmlElement)
	equateVertexesByFunction(equateZ, points, prefix, revolutions, xmlElement)

def equateX(point, returnValue):
	"""Get equation for rectangular x."""
	point.x = returnValue

def equateY(point, returnValue):
	"""Get equation for rectangular y."""
	point.y = returnValue

def equateZ(point, returnValue):
	"""Get equation for rectangular z."""
	point.z = returnValue

def equateVertexesByFunction( equationFunction, points, prefix, revolutions, xmlElement ):
	"""Get equated points by equation function."""
	prefixedEquationName = prefix + equationFunction.__name__[ len('equate') : ].replace('Dot', '.').lower()
	if prefixedEquationName not in xmlElement.attributeDictionary:
		return
	equationResult = EquationResult( prefixedEquationName, revolutions, xmlElement )
	for point in points:
		returnValue = equationResult.getReturnValue(point)
		if returnValue is None:
			print('Warning, returnValue in alterVertexesByEquation in equation is None for:')
			print(point)
			print(xmlElement)
		else:
			equationFunction(point, returnValue)
#	equationResult.function.reset() #removeLater

def getManipulatedGeometryOutput(geometryOutput, prefix, xmlElement):
	"""Get equated geometryOutput."""
	equatePoints( matrix.getVertexes(geometryOutput), prefix, None, xmlElement )
	return geometryOutput

def getManipulatedPaths(close, loop, prefix, sideLength, xmlElement):
	"""Get equated paths."""
	equatePoints( loop, prefix, 0.0, xmlElement )
	return [loop]


class EquationResult:
	"""Class to get equation results."""
	def __init__(self, key, revolutions, xmlElement):
		"""Initialize."""
		self.distance = 0.0
		xmlElement.xmlObject = evaluate.getEvaluatorSplitWords(xmlElement.attributeDictionary[key])
		self.function = evaluate.Function(xmlElement)
		self.points = []
		self.revolutions = revolutions

	def getReturnValue(self, point):
		"""Get return value."""
		if self.function is None:
			return point
		self.function.localDictionary['azimuth'] = math.degrees(math.atan2(point.y, point.x))
		if len(self.points) > 0:
			self.distance += abs(point - self.points[-1])
		self.function.localDictionary['distance'] = self.distance
		self.function.localDictionary['radius'] = abs(point.dropAxis())
		if self.revolutions is not None:
			if len( self.points ) > 0:
				self.revolutions += 0.5 / math.pi * euclidean.getAngleAroundZAxisDifference(point, self.points[-1])
			self.function.localDictionary['revolutions'] = self.revolutions
		self.function.localDictionary['vertex'] = point
		self.function.localDictionary['vertexes'] = self.points
		self.function.localDictionary['vertexindex'] = len(self.points)
		self.function.localDictionary['x'] = point.x
		self.function.localDictionary['y'] = point.y
		self.function.localDictionary['z'] = point.z
		self.points.append(point)
		return self.function.getReturnValueWithoutDeletion()
