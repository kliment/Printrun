"""
Shaft path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = ShaftDerivation(xmlElement)
	shaftPath = getShaftPath(derivation.depthBottom, derivation.depthTop, derivation.radius, derivation.sides)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(shaftPath), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['radius', 'sides'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return ShaftDerivation(xmlElement)

def getShaftPath(depthBottom, depthTop, radius, sides):
	"""Get shaft with the option of a flat on the top and/or bottom."""
	if radius <= 0.0:
		return []
	sideAngle = 2.0 * math.pi / float(abs(sides))
	startAngle = 0.5 * sideAngle
	endAngle = math.pi - 0.1 * sideAngle
	shaftProfile = []
	while startAngle < endAngle:
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		shaftProfile.append(unitPolar * radius)
		startAngle += sideAngle
	if abs(sides) % 2 == 1:
		shaftProfile.append(complex(-radius, 0.0))
	horizontalBegin = radius - depthTop
	horizontalEnd = depthBottom - radius
	shaftProfile = euclidean.getHorizontallyBoundedPath(horizontalBegin, horizontalEnd, shaftProfile)
	for shaftPointIndex, shaftPoint in enumerate(shaftProfile):
		shaftProfile[shaftPointIndex] = complex(shaftPoint.imag, shaftPoint.real)
	shaftPath = euclidean.getVector3Path(euclidean.getMirrorPath(shaftProfile))
	if sides > 0:
		shaftPath.reverse()
	return shaftPath

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class ShaftDerivation:
	"""Class to hold shaft variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.depthBottomOverRadius = evaluate.getEvaluatedFloat(0.0, 'depthBottomOverRadius', xmlElement)
		self.depthTopOverRadius = evaluate.getEvaluatedFloat(0.0, 'depthOverRadius', xmlElement)
		self.depthTopOverRadius = evaluate.getEvaluatedFloat(
			self.depthTopOverRadius, 'depthTopOverRadius', xmlElement)
		self.radius = evaluate.getEvaluatedFloat(1.0, 'radius', xmlElement)
		self.sides = evaluate.getEvaluatedInt(4, 'sides', xmlElement)
		self.depthBottom = self.radius * self.depthBottomOverRadius
		self.depthBottom = evaluate.getEvaluatedFloat(self.depthBottom, 'depthBottom', xmlElement)
		self.depthTop = self.radius * self.depthTopOverRadius
		self.depthTop = evaluate.getEvaluatedFloat(self.depthTop, 'depth', xmlElement)
		self.depthTop = evaluate.getEvaluatedFloat(self.depthTop, 'depthTop', xmlElement)

	def __repr__(self):
		"""Get the string representation of this ShaftDerivation."""
		return str(self.__dict__)
