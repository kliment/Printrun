"""
Boolean geometry utilities.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def _getAccessibleAttribute(attributeName, xmlElement):
	"""Get the accessible attribute."""
	if attributeName in globalGetAccessibleAttributeSet:
		return getattr(Document(xmlElement), attributeName, None)
	return None


class Document:
	"""Class to get handle xmlElements in a document."""
	def __init__(self, xmlElement):
		"""Initialize."""
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this Document."""
		return self.xmlElement

	def getByID(self, idKey):
		"""Get element by id."""
		return self.getElementByID(idKey)

	def getByName(self, nameKey):
		"""Get element by name."""
		return self.getElementsByName(nameKey)

	def getCascadeFloat(self, defaultFloat, key):
		"""Get cascade float."""
		return self.xmlElement.getCascadeFloat(defaultFloat, key)

	def getElementByID(self, idKey):
		"""Get element by id."""
		elementByID = self.xmlElement.getXMLElementByImportID(idKey)
		if elementByID is None:
			print('Warning, could not get elementByID in getElementByID in document for:')
			print(idKey)
			print(self.xmlElement)
		return elementByID

	def getElementsByName(self, nameKey):
		"""Get element by name."""
		elementsByName = self.xmlElement.getXMLElementsByImportName(nameKey)
		if elementsByName is None:
			print('Warning, could not get elementsByName in getElementsByName in document for:')
			print(nameKey)
			print(self.xmlElement)
		return elementsByName

	def getElementsByTag(self, tagKey):
		"""Get element by tag."""
		elementsByTag = self.xmlElement.getXMLElementsByTag(tagKey)
		if elementsByTag is None:
			print('Warning, could not get elementsByTag in getElementsByTag in document for:')
			print(tagKey)
			print(self.xmlElement)
		return elementsByTag

	def getParent(self):
		"""Get parent element."""
		return self.getParentElement()

	def getParentElement(self):
		"""Get parent element."""
		return self.xmlElement.parent

	def getPrevious(self):
		"""Get previous element."""
		return self.getPreviousElement()

	def getPreviousElement(self):
		"""Get previous element."""
		return self.xmlElement.getPreviousXMLElement()

	def getPreviousVertex(self):
		"""Get previous element."""
		return self.xmlElement.getPreviousVertex()

	def getRoot(self):
		"""Get root element."""
		return self.getRootElement()

	def getRootElement(self):
		"""Get root element."""
		return self.xmlElement.getRoot()

	def getSelf(self):
		"""Get self element."""
		return self.getSelfElement()

	def getSelfElement(self):
		"""Get self element."""
		return self.xmlElement


globalAccessibleAttributes = 'getByID getByName getCascadeFloat getElementByID getElementsByName getElementsByTag'.split()
globalAccessibleAttributes += 'getParent getParentElement getPrevious getPreviousElement getPreviousVertex getRoot'.split()
globalAccessibleAttributes += 'getRootElement getSelf getSelfElement'.split()
globalGetAccessibleAttributeSet = set(globalAccessibleAttributes)
