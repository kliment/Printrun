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


def processChildrenByIndexValue( function, index, indexValue, value, xmlElement ):
	"""Process children by index value."""
	if indexValue.indexName != '':
		function.localDictionary[ indexValue.indexName ] = index
	if indexValue.valueName != '':
		function.localDictionary[ indexValue.valueName ] = value
	function.processChildren(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	if xmlElement.xmlObject is None:
		xmlElement.xmlObject = IndexValue(xmlElement)
	if xmlElement.xmlObject.inSplitWords is None:
		return
	xmlProcessor = xmlElement.getXMLProcessor()
	if len( xmlProcessor.functions ) < 1:
		print('Warning, "for" element is not in a function in processXMLElement in for.py for:')
		print(xmlElement)
		return
	function = xmlProcessor.functions[-1]
	inValue = evaluate.getEvaluatedExpressionValueBySplitLine( xmlElement.xmlObject.inSplitWords, xmlElement )
	if inValue.__class__ == list or inValue.__class__ == str:
		for index, value in enumerate( inValue ):
			processChildrenByIndexValue( function, index, xmlElement.xmlObject, value, xmlElement )
		return
	if inValue.__class__ == dict:
		inKeys = inValue.keys()
		inKeys.sort()
		for inKey in inKeys:
			processChildrenByIndexValue( function, inKey, xmlElement.xmlObject, inValue[ inKey ], xmlElement )


class IndexValue:
	"""Class to get the in attribute, the index name and the value name."""
	def __init__(self, xmlElement):
		"""Initialize."""
		self.inSplitWords = None
		self.indexName = ''
		if 'index' in xmlElement.attributeDictionary:
			self.indexName = xmlElement.attributeDictionary['index']
		self.valueName = ''
		if 'value' in xmlElement.attributeDictionary:
			self.valueName = xmlElement.attributeDictionary['value']
		if 'in' in xmlElement.attributeDictionary:
			self.inSplitWords = evaluate.getEvaluatorSplitWords( xmlElement.attributeDictionary['in'] )
		else:
			print('Warning, could not find the "in" attribute in IndexValue in for.py for:')
			print(xmlElement)
			return
		if len( self.inSplitWords ) < 1:
			self.inSplitWords = None
			print('Warning, could not get split words for the "in" attribute in IndexValue in for.py for:')
			print(xmlElement)

