"""
Square path.

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
		derivation = SquareDerivation(xmlElement)
	topRight = complex(derivation.topDemiwidth, derivation.demiheight)
	topLeft = complex(-derivation.topDemiwidth, derivation.demiheight)
	bottomLeft = complex(-derivation.bottomDemiwidth, -derivation.demiheight)
	bottomRight = complex(derivation.bottomDemiwidth, -derivation.demiheight)
	if derivation.interiorAngle != 90.0:
		interiorPlaneAngle = euclidean.getWiddershinsUnitPolar(math.radians(derivation.interiorAngle - 90.0))
		topRight = (topRight - bottomRight) * interiorPlaneAngle + bottomRight
		topLeft = (topLeft - bottomLeft) * interiorPlaneAngle + bottomLeft
	lineation.setClosedAttribute(derivation.revolutions, xmlElement)
	complexLoop = [topRight, topLeft, bottomLeft, bottomRight]
	originalLoop = complexLoop[:]
	for revolution in xrange(1, derivation.revolutions):
		complexLoop += originalLoop
	spiral = lineation.Spiral(derivation.spiral, 0.25)
	loop = []
	loopCentroid = euclidean.getLoopCentroid(originalLoop)
	for point in complexLoop:
		unitPolar = euclidean.getNormalized(point - loopCentroid)
		loop.append(spiral.getSpiralPoint(unitPolar, Vector3(point.real, point.imag)))
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop, 0.5 * math.pi), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	if len(arguments) < 1:
		return getGeometryOutput(None, xmlElement)
	inradius = 0.5 * euclidean.getFloatFromValue(arguments[0])
	xmlElement.attributeDictionary['inradius.x'] = str(inradius)
	if len(arguments) > 1:
		inradius = 0.5 * euclidean.getFloatFromValue(arguments[1])
	xmlElement.attributeDictionary['inradius.y'] = str(inradius)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return SquareDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class SquareDerivation:
	"""Class to hold square variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.inradius = lineation.getComplexByPrefixes(['demisize', 'inradius'], complex(1.0, 1.0), xmlElement)
		self.inradius = lineation.getComplexByMultiplierPrefix(2.0, 'size', self.inradius, xmlElement)
		self.demiwidth = lineation.getFloatByPrefixBeginEnd('demiwidth', 'width', self.inradius.real, xmlElement)
		self.demiheight = lineation.getFloatByPrefixBeginEnd('demiheight', 'height', self.inradius.imag, xmlElement)
		self.bottomDemiwidth = lineation.getFloatByPrefixBeginEnd('bottomdemiwidth', 'bottomwidth', self.demiwidth, xmlElement)
		self.topDemiwidth = lineation.getFloatByPrefixBeginEnd('topdemiwidth', 'topwidth', self.demiwidth, xmlElement)
		self.interiorAngle = evaluate.getEvaluatedFloat(90.0, 'interiorangle', xmlElement)
		self.revolutions = evaluate.getEvaluatedInt(1, 'revolutions', xmlElement)
		self.spiral = evaluate.getVector3ByPrefix(None, 'spiral', xmlElement)

	def __repr__(self):
		"""Get the string representation of this SquareDerivation."""
		return str(self.__dict__)
