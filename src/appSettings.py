import os
import sys
import platform
import miniEnv as env
from errorManager import miniErrorManager, ReturnCode; em = miniErrorManager
from configobj import ConfigObj, ConfigObjError, flatten_errors
from validate import Validator, VdtValueError, VdtTypeError, VdtValueTooLongError, \
        VdtValueTooShortError, VdtValueTooBigError, VdtValueTooSmallError


fakePass = '-1.a###0q'

class MiniConfigObj(ConfigObj):
    # Init the superclass
    def __init__(self, *args, **kwargs):
        ConfigObj.__init__(self, *args, **kwargs)

    # Override write() to protect config file writes against exceptions
    def write(self, outfile=None, section=None):
        try:
            return ConfigObj.write(self, outfile, section)
        except PermissionError as ex:
            return em.setException(ex, "Unable to write: ")


# The appSettings class manages the Miniquery program "settings" (not to be confused
# with the database "configurations").
# The settings include customizable user preferences as well as system
# properties determined at startup such as the operating system type.
# The customizable settings are stored in $MINI_CONFIG/mini.cfg.
# They can be customized at the user level with $HOME/.minirc.

class appSettings():

    def __init__(self):
        self.settings = None
        self.isInputTty = sys.stdin.isatty()
        self.isOutputTty = sys.stdout.isatty()
        self.ostype = platform.system()

    def loadSettings(self, userSettingsFile):
        cfgSpec = os.path.join(env.MINI_CONFIG, 'configspec.cfg')
        validator = Validator()
        msg = ''

        # Load the settings from the user-specific file if it is available.
        if os.path.isfile(userSettingsFile):
            try:
                self.settings = MiniConfigObj(userSettingsFile, configspec=cfgSpec,
                        # file_error catches nonexistence of file
                        file_error=True)
                
                # Verify the connection string is provided in a section named
                # by the "definition type" attribute. If that section is missing
                # from the config, this check will raise a KeyError. We will
                # allow the other definition-type sections to be absent.
                hasConnString = self.settings['ConnectionString'][self.settings[ \
                        'ConnectionString']['definitionType']]

            # ConfigObjError catches file format problems. IOError goes with file_error.
            except (ConfigObjError, IOError) as e:
                return em.setError(ReturnCode.CONFIG_FILE_FORMAT_ERROR, userSettingsFile)
            except KeyError:    # Thrown if hasConnString (above) fails
#                hasConnString = False
#TODO The validation below doesn't catch this; that's why we handle it up here. 
#TODO Is this "setError()" the right way to handle this?
#TODO Also, dup. all fxy from userSettingsFile section to globalSettingsFile section below.
                return em.setError(ReturnCode.CONFIG_MISSING_REQUIRED_SECTION, userSettingsFile, 
                        self.settings['ConnectionString']['definitionType'])

            # Validation catches bad values in the config file
            # See  https://pythonhosted.org/theape/documentation/developer/
            #            explorations/explore_configobj/validation_errors.html
            # and  http://www.voidspace.org.uk/python/articles/configobj.shtml
            results = self.settings.validate(validator, preserve_errors=True)
            if results == True:
                return ReturnCode.SUCCESS
            else:
                msg = 'Validation failures:\n'
                for (section_list, key, error) in flatten_errors(self.settings, results):
                    
                    section_path = '.'.join(section_list)

                    if key is not None:

                        # Missing values
                        if error == False:
                            msg += '  Missing value: {}[{}]\n'.format(section_path, key)
                            continue

                        # Walk the section_list to get the datum
                        d = self.settings
                        for s in section_list:
                            d = d[s]

                        # Type-specific error handling of bad values
                        if isinstance(error, VdtTypeError):
                            desc = 'Incorrect data type'
                        elif type(error) is VdtValueError:
                            desc = 'Invalid option choice'
                        elif isinstance(error, (VdtValueTooLongError, VdtValueTooShortError)):
                            desc = 'String length outside legal range'
                        elif isinstance(error, (VdtValueTooBigError, VdtValueTooSmallError)):
                            desc = 'Numeric value is outside legal range'

                        msg += '  {}: {}[{}] = {} (error = {})\n'.format(desc, section_path, key, d[key], error)

                    else:
                        msg += '  Missing section: {}\n'.format(section_path)
                return em.setError(ReturnCode.CONFIG_VALIDATION_ERROR, userSettingsFile, msg)

        # Fall back on the global settings only if the user's are unavailable.
        globalSettingsFile = os.path.join(env.MINI_CONFIG, 'mini.cfg')
        if os.path.isfile(globalSettingsFile):
            try:
                self.settings = MiniConfigObj(globalSettingsFile, configspec=cfgSpec,
                        file_error=True)
            except (ConfigObjError, IOError) as e:
                return em.setError(ReturnCode.CONFIG_FILE_FORMAT_ERROR, cfgSpec)
            results = self.settings.validate(validator, preserve_errors=True)
            if results != True:
                for (section_list, key, error) in flatten_errors(self.settings, results):
                    if key is not None:
                        print ('The "{}" key in the section "{}" failed validation'.format(key, ', '.join(section_list)))
                    else:
                        print ('The following section was missing: {}'.format(', '.join(section_list)))
                return em.setError(ReturnCode.CONFIG_VALIDATION_ERROR, cfgSpec, msg)
            return ReturnCode.SUCCESS

# Instantiate a global object that can be made visible everywhere with
# an easy import. Function main() will populate it. 
# Better than passing it all over as a function parameter.
miniSettings = appSettings()
