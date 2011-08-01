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
		derivation = PolygonDerivation(xmlElement)
	loop = []
	spiral = lineation.Spiral(derivation.spiral, 0.5 * derivation.sideAngle / math.pi)
	for side in xrange(derivation.start, derivation.start + derivation.extent + 1):
		angle = float(side) * derivation.sideAngle
		unitPolar = euclidean.getWiddershinsUnitPolar(angle)
		vertex = spiral.getSpiralPoint(unitPolar, Vector3(unitPolar.real * derivation.radius.real, unitPolar.imag * derivation.radius.imag))
		loop.append(vertex)
	loop = euclidean.getLoopWithoutCloseEnds(0.000001 * max(derivation.radius.real, derivation.radius.imag), loop)
	sideLength = derivation.sideAngle * lineation.getRadiusAverage(derivation.radius)
	lineation.setClosedAttribute(derivation.revolutions, xmlElement)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop, derivation.sideAngle, sideLength), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['sides', 'radius'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return PolygonDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class PolygonDerivation:
	"""Class to hold polygon variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.sides = evaluate.getEvaluatedFloat(4.0, 'sides', xmlElement)
		self.sideAngle = 2.0 * math.pi / self.sides
		cosSide = math.cos(0.5 * self.sideAngle)
		self.radius = lineation.getComplexByMultiplierPrefixes(cosSide, ['apothem', 'inradius'], complex(1.0, 1.0), xmlElement)
		self.radius = lineation.getComplexByPrefixes(['demisize', 'radius'], self.radius, xmlElement)
		self.radius = lineation.getComplexByMultiplierPrefixes(2.0, ['diameter', 'size'], self.radius, xmlElement)
		self.sidesCeiling = int(math.ceil(abs(self.sides)))
		self.start = evaluate.getEvaluatedInt(0, 'start', xmlElement)
		end = evaluate.getEvaluatedInt(self.sidesCeiling, 'end', xmlElement)
		self.revolutions = evaluate.getEvaluatedInt(1, 'revolutions', xmlElement)
		self.extent = evaluate.getEvaluatedInt(end - self.start, 'extent', xmlElement)
		self.extent += self.sidesCeiling * (self.revolutions - 1)
		self.spiral = evaluate.getVector3ByPrefix(None, 'spiral', xmlElement)

	def __repr__(self):
		"""Get the string representation of this PolygonDerivation."""
		return str(self.__dict__)
