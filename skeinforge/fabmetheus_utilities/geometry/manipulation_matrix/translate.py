"""
Boolean geometry translation.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


globalExecutionOrder = 380


def getManipulatedGeometryOutput(geometryOutput, prefix, xmlElement):
	"""Get equated geometryOutput."""
	translatePoints( matrix.getVertexes(geometryOutput), prefix, xmlElement )
	return geometryOutput

def getManipulatedPaths(close, loop, prefix, sideLength, xmlElement):
	"""Get equated paths."""
	translatePoints( loop, prefix, xmlElement )
	return [loop]

def manipulateXMLElement(target, xmlElement):
	"""Manipulate the xml element."""
	translateTetragrid = matrix.getTranslateTetragrid('', xmlElement)
	if translateTetragrid is None:
		print('Warning, translateTetragrid was None in translate so nothing will be done for:')
		print(xmlElement)
		return
	matrix.setAttributeDictionaryToMultipliedTetragrid(translateTetragrid, target)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	solid.processXMLElementByFunction(manipulateXMLElement, xmlElement)

def translateNegativesPositives(negatives, positives, translation):
	"""Translate the negatives and postives."""
	euclidean.translateVector3Path(matrix.getVertexes(negatives), translation)
	euclidean.translateVector3Path(matrix.getVertexes(positives), translation)

def translatePoints(points, prefix, xmlElement):
	"""Translate the points."""
	translateVector3 = matrix.getCumulativeVector3Remove(Vector3(), prefix, xmlElement)
	if abs(translateVector3) > 0.0:
		euclidean.translateVector3Path(points, translateVector3)
