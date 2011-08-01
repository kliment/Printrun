"""
Teardrop path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addNegativesByRadius(end, negatives, radius, start, xmlElement):
	"""Add teardrop drill hole to negatives."""
	if radius <= 0.0:
		return
	copyShallow = xmlElement.getCopyShallow()
	extrude.setXMLElementToEndStart(end, start, copyShallow)
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	extrude.addNegatives(extrudeDerivation, negatives, [getTeardropPathByEndStart(end, radius, start, xmlElement)])

def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = TeardropDerivation(xmlElement)
	teardropPath = getTeardropPath(derivation.inclination, derivation.radius, xmlElement)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(teardropPath), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['radius', 'inclination'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getInclination(end, start):
	"""Get inclination."""
	if end is None or start is None:
		return 0.0
	endMinusStart = end - start
	return math.atan2(endMinusStart.z, abs(endMinusStart.dropAxis()))

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return TeardropDerivation(xmlElement)

def getTeardropPath(inclination, radius, xmlElement):
	"""Get vector3 teardrop path."""
	teardropSides = evaluate.getSidesMinimumThreeBasedOnPrecision(radius, xmlElement)
	sideAngle = 2.0 * math.pi / float(teardropSides)
	overhangRadians = setting.getOverhangRadians(xmlElement)
	overhangPlaneAngle = euclidean.getWiddershinsUnitPolar(overhangRadians)
	overhangRadians = math.atan2(overhangPlaneAngle.imag, overhangPlaneAngle.real * math.cos(inclination))
	tanOverhangAngle = math.tan(overhangRadians)
	beginAngle = overhangRadians
	beginMinusEndAngle = math.pi + overhangRadians + overhangRadians
	withinSides = int(math.ceil(beginMinusEndAngle / sideAngle))
	withinSideAngle = -beginMinusEndAngle / float(withinSides)
	teardropPath = []
	for side in xrange(withinSides + 1):
		unitPolar = euclidean.getWiddershinsUnitPolar(beginAngle)
		teardropPath.append(unitPolar * radius)
		beginAngle += withinSideAngle
	firstPoint = teardropPath[0]
	overhangSpan = setting.getOverhangSpan(xmlElement)
	if overhangSpan <= 0.0:
		teardropPath.append(complex(0.0, firstPoint.imag + firstPoint.real / tanOverhangAngle))
	else:
		deltaX = (radius - firstPoint.imag) * tanOverhangAngle
		overhangPoint = complex(firstPoint.real - deltaX, radius)
		remainingDeltaX = max(0.0, overhangPoint.real - 0.5 * overhangSpan )
		overhangPoint += complex(-remainingDeltaX, remainingDeltaX / tanOverhangAngle)
		teardropPath.append(complex(-overhangPoint.real, overhangPoint.imag))
		teardropPath.append(overhangPoint)
	return euclidean.getVector3Path(teardropPath)

def getTeardropPathByEndStart(end, radius, start, xmlElement):
	"""Get vector3 teardrop path by end and start."""
	inclination = getInclination(end, start)
	return getTeardropPath(inclination, radius, xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class TeardropDerivation:
	"""Class to hold teardrop variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		end = evaluate.getVector3ByPrefix(None, 'end', xmlElement)
		start = evaluate.getVector3ByPrefix(Vector3(), 'start', xmlElement)
		inclinationDegree = math.degrees(getInclination(end, start))
		self.inclination = math.radians(evaluate.getEvaluatedFloat(inclinationDegree, 'inclination', xmlElement))
		self.radius = lineation.getFloatByPrefixBeginEnd('radius', 'diameter', 1.0, xmlElement)
		size = evaluate.getEvaluatedFloat(None, 'size', xmlElement)
		if size is not None:
			self.radius = 0.5 * size
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this TeardropDerivation."""
		return str(self.__dict__)
