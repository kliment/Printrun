"""
Polygon path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def processXMLElement(xmlElement):
	"""Process the xml element."""
	functions = xmlElement.getXMLProcessor().functions
	if len(functions) < 1:
		print('Warning, there are no functions in processXMLElement in statement for:')
		print(xmlElement)
		return
	function = functions[-1]
	evaluate.setLocalAttribute(xmlElement)
	if xmlElement.xmlObject.value is None:
		print('Warning, xmlElement.xmlObject.value is None in processXMLElement in statement for:')
		print(xmlElement)
		return
	localValue = evaluate.getEvaluatedExpressionValueBySplitLine(xmlElement.xmlObject.value, xmlElement)
	keywords = xmlElement.xmlObject.key.split('.')
	if len(keywords) == 0:
		print('Warning, there are no keywords in processXMLElement in statement for:')
		print(xmlElement)
		return
	firstWord = keywords[0]
	if len(keywords) == 1:
		function.localDictionary[firstWord] = localValue
		return
	attributeName = keywords[-1]
	object = None
	if firstWord == 'self':
		object = function.classObject
	else:
		object = function.localDictionary[firstWord]
	for keywordIndex in xrange(1, len(keywords) - 1):
		object = object._getAccessibleAttribute(keywords[keywordIndex])
	object._setAccessibleAttribute(attributeName, localValue)
