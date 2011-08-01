"""
Peg.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.vector3 import Vector3
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'



def addPegOutput(bevel, endZ, outputs, radius, start, topOverBottom, xmlElement):
	"""Add beveled cylinder to outputs given bevel, endZ, radius and start."""
	height = abs(start.z - endZ)
	bevelStartRatio = max(1.0 - bevel / height, 0.5)
	oneMinusBevelStartRatio = 1.0 - bevelStartRatio
	trunkEndZ = bevelStartRatio * endZ + oneMinusBevelStartRatio * start.z
	trunkTopOverBottom = bevelStartRatio * topOverBottom + oneMinusBevelStartRatio
	sides = evaluate.getSidesMinimumThreeBasedOnPrecision(max(radius.real, radius.imag), xmlElement )
	cylinder.addCylinderOutputByEndStart(trunkEndZ, radius, outputs, sides, start, trunkTopOverBottom)
	capRadius = radius * trunkTopOverBottom
	capStart = bevelStartRatio * Vector3(start.x, start.y, endZ) + oneMinusBevelStartRatio * start
	radiusMaximum = max(radius.real, radius.imag)
	endRadiusMaximum = radiusMaximum * topOverBottom - bevel
	trunkRadiusMaximum = radiusMaximum * trunkTopOverBottom
	capTopOverBottom = endRadiusMaximum / trunkRadiusMaximum
	cylinder.addCylinderOutputByEndStart(endZ, capRadius, outputs, sides, capStart, capTopOverBottom)

def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = PegDerivation(xmlElement)
	positives = []
	radius = complex(derivation.radius, derivation.radius)
	addPegOutput(derivation.bevel, derivation.endZ, positives, radius, derivation.start, derivation.topOverBottom, xmlElement)
	return extrude.getGeometryOutputByNegativesPositives([], positives, xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['radius', 'endZ', 'start'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return PegDerivation(xmlElement)

def getTopAddBiconicOutput(bottomRadians, height, outputs, radius, sides, start, tipRadius, topRadians):
	"""Get top and add biconic cylinder to outputs."""
	radiusMaximum = max(radius.real, radius.imag)
	topRadiusMaximum = radiusMaximum - height * math.tan(bottomRadians)
	trunkEndZ = start.z + height
	trunkTopOverBottom = topRadiusMaximum / radiusMaximum
	topRadiusComplex = trunkTopOverBottom * radius
	cylinder.addCylinderOutputByEndStart(trunkEndZ, radius, outputs, sides, start, trunkTopOverBottom)
	tipOverTop = tipRadius / topRadiusMaximum
	if tipOverTop >= 1.0:
		return trunkEndZ
	capStart = Vector3(start.x, start.y, trunkEndZ)
	capEndZ = trunkEndZ + (topRadiusMaximum - tipRadius) / math.tan(topRadians)
	cylinder.addCylinderOutputByEndStart(capEndZ, topRadiusComplex, outputs, sides, capStart, tipOverTop)
	return capEndZ

def processXMLElement(xmlElement):
	"""Process the xml element."""
	solid.processXMLElementByGeometry(getGeometryOutput(None, xmlElement), xmlElement)


class PegDerivation:
	"""Class to hold peg variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.endZ = evaluate.getEvaluatedFloat(10.0, 'endZ', xmlElement)
		self.start = evaluate.getVector3ByPrefix(Vector3(), 'start', xmlElement)
		self.radius = lineation.getFloatByPrefixBeginEnd('radius', 'diameter', 2.0, xmlElement)
		self.topOverBottom = evaluate.getEvaluatedFloat(0.8, 'topOverBottom', xmlElement)
		self.xmlElement = xmlElement
		# Set derived variables.
		self.bevelOverRadius = evaluate.getEvaluatedFloat(0.25, 'bevelOverRadius', xmlElement)
		self.bevel = self.bevelOverRadius * self.radius
		self.bevel = evaluate.getEvaluatedFloat(self.bevel, 'bevel', xmlElement)
		self.clearanceOverRadius = evaluate.getEvaluatedFloat(0.0, 'clearanceOverRadius', xmlElement)
		self.clearance = self.clearanceOverRadius * self.radius
		self.clearance = evaluate.getEvaluatedFloat(self.clearance, 'clearance', xmlElement)

	def __repr__(self):
		"""Get the string representation of this PegDerivation."""
		return str(self.__dict__)
