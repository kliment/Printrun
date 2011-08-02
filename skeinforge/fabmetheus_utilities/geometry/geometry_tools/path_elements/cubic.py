"""
Cubic vertexes.

From:
http://www.w3.org/TR/SVG/paths.html#PathDataCubicBezierCommands

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCubicPath(xmlElement):
	"""Get the cubic path."""
	end = evaluate.getVector3FromXMLElement(xmlElement)
	previousXMLElement = xmlElement.getPreviousXMLElement()
	if previousXMLElement is None:
		print('Warning, can not get previousXMLElement in getCubicPath in cubic for:')
		print(xmlElement)
		return [end]
	begin = xmlElement.getPreviousVertex(Vector3())
	evaluatedControlPoints = evaluate.getTransformedPathByKey([], 'controlPoints', xmlElement)
	if len(evaluatedControlPoints) > 1:
		return getCubicPathByBeginEnd(begin, evaluatedControlPoints, end, xmlElement)
	controlPoint0 = evaluate.getVector3ByPrefix(None, 'controlPoint0', xmlElement)
	controlPoint1 = evaluate.getVector3ByPrefix(None, 'controlPoint1', xmlElement)
	if len(evaluatedControlPoints) == 1:
		controlPoint1 = evaluatedControlPoints[0]
	if controlPoint0 is None:
		oldControlPoint = evaluate.getVector3ByPrefixes(['controlPoint','controlPoint1'], None, previousXMLElement)
		if oldControlPoint is None:
			oldControlPoints = evaluate.getTransformedPathByKey([], 'controlPoints', previousXMLElement)
			if len(oldControlPoints) > 0:
				oldControlPoint = oldControlPoints[-1]
		if oldControlPoint is None:
			oldControlPoint = end
		controlPoint0 = begin + begin - oldControlPoint
	return getCubicPathByBeginEnd(begin, [controlPoint0, controlPoint1], end, xmlElement)

def getCubicPathByBeginEnd(begin, controlPoints, end, xmlElement):
	"""Get the cubic path by begin and end."""
	return svg_reader.getCubicPoints(begin, controlPoints, end, lineation.getNumberOfBezierPoints(begin, end, xmlElement))

def processXMLElement(xmlElement):
	"""Process the xml element."""
	xmlElement.parent.xmlObject.vertexes += getCubicPath(xmlElement)
