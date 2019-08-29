import os
import miniEnv as env
from errorManager import miniErrorManager as em, ReturnCode
from configobj import ConfigObj

# This class manages the Miniquery program "settings" (not to be confused
# with the database "configurations").

class appSettings():
    # The global program settings are stored in $MINI_CONFIG/mini.cfg.
    # They can be customized at the user level with $HOME/.mini.rc.

    def __init__(self):
        self.settings = None

    def loadSettings(self):
        # Load the settings from the user-specific file if it is available.
        userSettingsFile = os.path.join(env.HOME, '.mini.rc')
        if os.path.isfile(userSettingsFile):
            self.settings = ConfigObj(userSettingsFile)
            return ReturnCode.SUCCESS

        # Fall back on the global settings only if the user's are unavailable.
        globalSettingsFile = os.path.join(env.MINI_CONFIG, 'mini.cfg')
        if not os.path.isfile(globalSettingsFile):
            return em.setError(ReturnCode.MISSING_SETTINGS_FILE, globalSettingsFile)
        self.settings = ConfigObj(globalSettingsFile)
        #self.settings.merge(userSettings)
        return ReturnCode.SUCCESS

# Instantiate a global object that can be made visible everywhere with
# an easy import. Function main() will populate it. 
# Better than passing it all over as a function parameter.
miniSettings = appSettings()
