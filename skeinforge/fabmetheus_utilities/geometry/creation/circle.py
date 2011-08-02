"""
Polygon path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = CircleDerivation(xmlElement)
	angleTotal = math.radians(derivation.start)
	loop = []
	sidesCeiling = int(math.ceil(abs(derivation.sides) * derivation.extent / 360.0))
	sideAngle = math.radians(derivation.extent) / sidesCeiling
	if derivation.sides < 0.0:
		sideAngle = -sideAngle
	spiral = lineation.Spiral(derivation.spiral, 0.5 * sideAngle / math.pi)
	for side in xrange(sidesCeiling + 1):
		unitPolar = euclidean.getWiddershinsUnitPolar(angleTotal)
		x = unitPolar.real * derivation.circularizedRadius.real
		y = unitPolar.imag * derivation.circularizedRadius.imag
		vertex = spiral.getSpiralPoint(unitPolar, Vector3(x, y))
		angleTotal += sideAngle
		loop.append(vertex)
	radiusMaximum = 0.000001 * max(derivation.circularizedRadius.real, derivation.circularizedRadius.imag)
	loop = euclidean.getLoopWithoutCloseEnds(radiusMaximum, loop)
	sideLength = sideAngle * lineation.getRadiusAverage(derivation.circularizedRadius)
	lineation.setClosedAttribute(derivation.revolutions, xmlElement)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop, sideAngle, sideLength), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['radius', 'start', 'end', 'revolutions'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return CircleDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class CircleDerivation:
	"""Class to hold circle variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.radius = lineation.getRadiusComplex(complex(1.0, 1.0), xmlElement)
		self.sides = evaluate.getEvaluatedFloat(None, 'sides', xmlElement)
		if self.sides is None:
			radiusMaximum = max(self.radius.real, self.radius.imag)
			self.sides = evaluate.getSidesMinimumThreeBasedOnPrecisionSides(radiusMaximum, xmlElement)
		self.circularizedRadius = self.radius
		if evaluate.getEvaluatedBoolean(False, 'areaRadius', xmlElement):
			self.circularizedRadius *= euclidean.getAreaRadiusMultiplier(self.sides)
		self.start = evaluate.getEvaluatedFloat(0.0, 'start', xmlElement)
		end = evaluate.getEvaluatedFloat(360.0, 'end', xmlElement)
		self.revolutions = evaluate.getEvaluatedFloat(1.0, 'revolutions', xmlElement)
		self.extent = evaluate.getEvaluatedFloat(end - self.start, 'extent', xmlElement)
		self.extent += 360.0 * (self.revolutions - 1.0)
		self.spiral = evaluate.getVector3ByPrefix(None, 'spiral', xmlElement)

	def __repr__(self):
		"""Get the string representation of this CircleDerivation."""
		return str(self.__dict__)
