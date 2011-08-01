"""
Boolean geometry bottom.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 400


def bottomXMLElement(derivation, target):
	"""Bottom target."""
	xmlObject = target.xmlObject
	if xmlObject is None:
		print('Warning, bottomTarget in bottom could not get xmlObject for:')
		print(target)
		print(derivation.xmlElement)
		return
	targetMatrix = matrix.getBranchMatrixSetXMLElement(target)
	lift = derivation.altitude
	transformedPaths = xmlObject.getTransformedPaths()
	if len(transformedPaths) > 0:
		lift += derivation.getAdditionalPathLift() - euclidean.getBottomByPaths(transformedPaths)
	else:
		lift -= boolean_geometry.getMinimumZ(xmlObject)
	targetMatrix.tetragrid = matrix.getIdentityTetragrid(targetMatrix.tetragrid)
	targetMatrix.tetragrid[2][3] += lift
	matrix.setXMLElementDictionaryMatrix(targetMatrix, target)

def getManipulatedGeometryOutput(geometryOutput, prefix, xmlElement):
	"""Get bottomed geometryOutput."""
	derivation = BottomDerivation(prefix, xmlElement)
	copyShallow = xmlElement.getCopyShallow()
	solid.processXMLElementByGeometry(geometryOutput, copyShallow)
	targetMatrix = matrix.getBranchMatrixSetXMLElement(xmlElement)
	matrix.setXMLElementDictionaryMatrix(targetMatrix, copyShallow)
	minimumZ = boolean_geometry.getMinimumZ(copyShallow.xmlObject)
	copyShallow.parent.xmlObject.archivableObjects.remove(copyShallow.xmlObject)
	lift = derivation.altitude - minimumZ
	vertexes = matrix.getVertexes(geometryOutput)
	for vertex in vertexes:
		vertex.z += lift
	return geometryOutput

def getManipulatedPaths(close, loop, prefix, sideLength, xmlElement):
	"""Get flipped paths."""
	if len(loop) < 1:
		return [[]]
	derivation = BottomDerivation(prefix, xmlElement)
	targetMatrix = matrix.getBranchMatrixSetXMLElement(xmlElement)
	transformedLoop = matrix.getTransformedVector3s(matrix.getIdentityTetragrid(targetMatrix.tetragrid), loop)
	lift = derivation.altitude + derivation.getAdditionalPathLift() - euclidean.getBottomByPath(transformedLoop)
	for point in loop:
		point.z += lift
	return [loop]

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return BottomDerivation('', xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	processXMLElementByDerivation(None, xmlElement)

def processXMLElementByDerivation(derivation, xmlElement):
	"""Process the xml element by derivation."""
	if derivation is None:
		derivation = BottomDerivation('', xmlElement)
	targets = evaluate.getXMLElementsByKey('target', xmlElement)
	if len(targets) < 1:
		print('Warning, processXMLElement in bottom could not get targets for:')
		print(xmlElement)
		return
	for target in targets:
		bottomXMLElement(derivation, target)


class BottomDerivation:
	"""Class to hold bottom variables."""
	def __init__(self, prefix, xmlElement):
		"""Set defaults."""
		self.altitude = evaluate.getEvaluatedFloat(0.0, prefix + 'altitude', xmlElement)
		self.liftPath = evaluate.getEvaluatedBoolean(True, prefix + 'liftPath', xmlElement)
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this BottomDerivation."""
		return str(self.__dict__)

	def getAdditionalPathLift(self):
		"""Get path lift."""
		return 0.5 * setting.getLayerThickness(self.xmlElement) * float(self.liftPath)
