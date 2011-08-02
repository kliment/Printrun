"""
Help has buttons and menu items to open help, blog and forum pages in your primary browser.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	"""Get new repository."""
	return HelpRepository()


class HelpRepository:
	"""A class to handle the help settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_utilities.skeinforge_help.html', self)
		settings.LabelDisplay().getFromName('- Announcements -', self )
		settings.LabelDisplay().getFromName('Fabmetheus Blog, Announcements & Questions:', self )
		settings.HelpPage().getFromNameAfterHTTP('fabmetheus.blogspot.com/', 'Fabmetheus Blog', self )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Documentation -', self )
		settings.LabelDisplay().getFromName('Local Documentation Table of Contents: ', self )
		settings.HelpPage().getFromNameSubName('Contents', self, 'contents.html')
		settings.LabelDisplay().getFromName('Wiki Manual with Pictures & Charts: ', self )
		settings.HelpPage().getFromNameAfterHTTP('fabmetheus.crsndoo.com/wiki/index.php/Skeinforge', 'Wiki Manual', self )
		settings.LabelDisplay().getFromName('Skeinforge Overview: ', self )
		settings.HelpPage().getFromNameSubName('Skeinforge Overview', self, 'skeinforge_application.skeinforge.html')
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Forums -', self )
		settings.LabelDisplay().getFromName('Bits from Bytes Software Board:', self )
		settings.HelpPage().getFromNameAfterWWW('bitsfrombytes.com/fora/user/index.php?board=4.0', 'Bits from Bytes Software Board', self )
		settings.LabelDisplay().getFromName('Makerbot Operators:', self )
		settings.HelpPage().getFromNameAfterHTTP('groups.google.com/group/makerbot', 'Makerbot Operators', self )
		settings.LabelDisplay().getFromName('Skeinforge Contributions Thread:', self )
		settings.HelpPage().getFromNameAfterHTTP('dev.forums.reprap.org/read.php?12,27562', 'Skeinforge Contributions Thread', self )
		settings.LabelDisplay().getFromName('Skeinforge Settings Thread:', self )
		settings.HelpPage().getFromNameAfterHTTP('dev.forums.reprap.org/read.php?12,27434', 'Skeinforge Settings Thread', self )
		settings.LabelDisplay().getFromName('Skeinforge Troubleshooting Thread:', self )
		settings.HelpPage().getFromNameAfterHTTP('forums.reprap.org/list.php?154', 'Skeinforge Troubleshooting Thread', self )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Search -', self )
		settings.LabelDisplay().getFromName('Reprap Search:', self )
		settings.HelpPage().getFromNameAfterHTTP('members.axion.net/~enrique/search_reprap.html', 'Reprap Search', self )
		settings.LabelDisplay().getFromName('Skeinforge Search:', self )
		settings.HelpPage().getFromNameAfterHTTP('members.axion.net/~enrique/search_skeinforge.html', 'Skeinforge Search', self )
		settings.LabelDisplay().getFromName('Web Search:', self )
		settings.HelpPage().getFromNameAfterHTTP('members.axion.net/~enrique/search_web.html', 'Web Search', self )
		settings.LabelSeparator().getFromRepository(self)
		self.wikiManualPrimary = settings.BooleanSetting().getFromValue('Wiki Manual Primary', self, True )
		self.wikiManualPrimary.setUpdateFunction( self.save )

	def save(self):
		"""Write the entities."""
		settings.writeSettingsPrintMessage(self)
