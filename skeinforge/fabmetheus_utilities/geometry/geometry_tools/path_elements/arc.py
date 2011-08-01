"""
Arc vertexes.

From:
http://www.w3.org/TR/SVG/paths.html#PathDataEllipticalArcCommands

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_reader
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getArcPath(xmlElement):
	"""Get the arc path.rx ry x-axis-rotation large-arc-flag sweep-flag"""
	begin = xmlElement.getPreviousVertex(Vector3())
	end = evaluate.getVector3FromXMLElement(xmlElement)
	largeArcFlag = evaluate.getEvaluatedBoolean(True, 'largeArcFlag', xmlElement)
	radius = lineation.getComplexByPrefix('radius', complex(1.0, 1.0), xmlElement )
	sweepFlag = evaluate.getEvaluatedBoolean(True, 'sweepFlag', xmlElement)
	xAxisRotation = math.radians(evaluate.getEvaluatedFloat(0.0, 'xAxisRotation', xmlElement ))
	arcComplexes = svg_reader.getArcComplexes(begin.dropAxis(), end.dropAxis(), largeArcFlag, radius, sweepFlag, xAxisRotation)
	path = []
	if len(arcComplexes) < 1:
		return []
	incrementZ = (end.z - begin.z) / float(len(arcComplexes))
	z = begin.z
	for pointIndex in xrange(len(arcComplexes)):
		pointComplex = arcComplexes[pointIndex]
		z += incrementZ
		path.append(Vector3(pointComplex.real, pointComplex.imag, z))
	if len(path) > 0:
		path[-1] = end
	return path

def processXMLElement(xmlElement):
	"""Process the xml element."""
	xmlElement.parent.xmlObject.vertexes += getArcPath(xmlElement)
