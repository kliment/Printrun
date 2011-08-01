"""
Boolean geometry scale.

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


globalExecutionOrder = 340


def getManipulatedGeometryOutput(geometryOutput, prefix, xmlElement):
	"""Get equated geometryOutput."""
	scalePoints( matrix.getVertexes(geometryOutput), prefix, xmlElement )
	return geometryOutput

def getManipulatedPaths(close, loop, prefix, sideLength, xmlElement):
	"""Get equated paths."""
	scalePoints( loop, prefix, xmlElement )
	return [loop]

def manipulateXMLElement(target, xmlElement):
	"""Manipulate the xml element."""
	scaleTetragrid = matrix.getScaleTetragrid('', xmlElement)
	if scaleTetragrid is None:
		print('Warning, scaleTetragrid was None in scale so nothing will be done for:')
		print(xmlElement)
		return
	matrix.setAttributeDictionaryToMultipliedTetragrid(scaleTetragrid, target)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	solid.processXMLElementByFunction( manipulateXMLElement, xmlElement)

def scalePoints(points, prefix, xmlElement):
	"""Scale the points."""
	scaleDefaultVector3 = Vector3(1.0, 1.0, 1.0)
	scaleVector3 = matrix.getCumulativeVector3Remove(scaleDefaultVector3.copy(), prefix, xmlElement)
	if scaleVector3 == scaleDefaultVector3:
		return
	for point in points:
		point.x *= scaleVector3.x
		point.y *= scaleVector3.y
		point.z *= scaleVector3.z
