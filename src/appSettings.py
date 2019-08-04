import os
import miniEnv as env
from errorManager import miniErrorManager as em, ReturnCode
from configobj import ConfigObj

# This class manages the Miniquery program "settings" (not to be confused
# with the database "configurations").

class appSettings():
    # The global program settings are stored in
    # $MINI_CONFIG/mini.cfg.
    # These can be customized at the user level with $HOME/.mini.rc.

    def __init__(self):
        self.settings = None

    def loadSettings(self):
        # Load the application-level settings. There is an application settings
        # file which the user may supplement/override with their own file.
        globalSettingsFile = env.MINI_CONFIG + '/mini.cfg'
        userSettingsFile = env.HOME + '/mini.rc'
        if not os.path.isfile(globalSettingsFile):
            return em.setError(ReturnCode.MISSING_SETTINGS_FILE, globalSettingsFile)
        self.settings = ConfigObj(globalSettingsFile)
        if os.path.isfile(userSettingsFile):
            userSettings = ConfigObj(userSettingsFile)
            self.settings.merge(userSettings)
        return ReturnCode.SUCCESS

# Initialize a global object that can be made visible everywhere with
# an easy import. Function main() will populate it. 
# Better than passing it all over as a function parameter.
miniSettings = appSettings()
