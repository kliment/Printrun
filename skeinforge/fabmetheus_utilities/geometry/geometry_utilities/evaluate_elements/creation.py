"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__


from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, xmlElement):
	"""Get the accessible attribute."""
	functionName = attributeName[len('get') :].lower()
	if functionName not in evaluate.globalCreationDictionary:
		print('Warning, functionName not in globalCreationDictionary in _getAccessibleAttribute in creation for:')
		print(functionName)
		print(xmlElement)
		return None
	pluginModule = archive.getModuleWithPath(evaluate.globalCreationDictionary[functionName])
	if pluginModule is None:
		print('Warning, _getAccessibleAttribute in creation can not get a pluginModule for:')
		print(functionName)
		print(xmlElement)
		return None
	return Creation(pluginModule, xmlElement).getCreation


class Creation:
	"""Class to handle a creation."""
	def __init__(self, pluginModule, xmlElement):
		"""Initialize."""
		self.pluginModule = pluginModule
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this creation."""
		return self.xmlElement

	def getCreation(self, *arguments):
		"""Get creation."""
		dictionary = {'_fromCreationEvaluator': 'true'}
		firstArgument = None
		if len(arguments) > 0:
			firstArgument = arguments[0]
		if firstArgument.__class__ == dict:
			dictionary.update(firstArgument)
			return self.pluginModule.getGeometryOutput(None, self.xmlElement.getCopyShallow(dictionary))
		copyShallow = self.xmlElement.getCopyShallow(dictionary)
		return self.pluginModule.getGeometryOutputByArguments(arguments, copyShallow)
