import json
from pprint import pprint
from jsonobject import *
import datetime
import iso8601

class ISOTimestampProperty(AbstractDateProperty):

    _type = datetime.datetime

    def _wrap(self, value):
        try:
            return iso8601.parse_date(value)
        except ValueError as e:
            raise ValueError(
                'Invalid ISO date/time {0!r} [{1}]'.format(value, e))

    def _unwrap(self, value):
        return value, value.isoformat()


class GradleSpecifier:
    '''
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    '''

    def __init__(self, name):
        components = name.split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]
        if len(components) == 4:
            self.classifier = components[3]
        else:
            self.classifier = None

    def toString(self):
        if self.classifier:
            return "%s:%s:%s:%s" % (self.group, self.artifact, self.version, self.classifier)
        else:
            return "%s:%s:%s" % (self.group, self.artifact, self.version)

    def isLwjgl(self):
        return self.group in ("org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

    def __lt__(self, other):
        return self.toString() < other.toString()

class GradleSpecifierProperty(JsonProperty):
    def wrap(self, value):
        return GradleSpecifier(value)

    def unwrap(self, value):
        return value, value.toString()

'''
Mojang index files look like this:
{
    "latest": {
        "release": "1.11.2",
        "snapshot": "17w06a"
    },
    "versions": [
        ...
        {
            "id": "17w06a",
            "releaseTime": "2017-02-08T13:16:29+00:00",
            "time": "2017-02-08T13:17:20+00:00",
            "type": "snapshot",
            "url": "https://launchermeta.mojang.com/mc/game/7db0c61afa278d016cf1dae2fba0146edfbf2f8e/17w06a.json"
        },
        ...
    ]
}
'''

class MojangIndexEntry(JsonObject):
    id = StringProperty()
    releaseTime = ISOTimestampProperty()
    time = ISOTimestampProperty()
    type = StringProperty()
    url = StringProperty()

class MojangIndex(JsonObject):
    latest = DictProperty(StringProperty)
    versions = ListProperty(MojangIndexEntry)

class MojangIndexWrap:
    def __init__(self, json):
        self.index = MojangIndex.wrap(json)
        self.latest = self.index.latest
        versionsDict = {}
        for version in self.index.versions:
            versionsDict[version.id] = version
        self.versions = versionsDict


class MojangArtifactBase (JsonObject):
    sha1 = StringProperty()
    size = IntegerProperty()
    url = StringProperty()

class MojangArtifact (MojangArtifactBase):
    path = StringProperty()

class MojangAssets (MojangArtifactBase):
    id = StringProperty()
    totalSize = IntegerProperty()

class MojangLibraryDownloads(JsonObject):
    artifact = ObjectProperty(MojangArtifact, exclude_if_none=True, default=None)
    classifiers = DictProperty(MojangArtifact, exclude_if_none=True, default=None)

class MojangLibraryExtractRules(JsonObject):
    exclude = ListProperty(StringProperty)

'''
            "rules": [
                {
                    "action": "allow"
                },
                {
                    "action": "disallow",
                    "os": {
                        "name": "osx"
                    }
                }
            ]
'''

class OSRule (JsonObject):
    name = StringProperty(choices=["osx", "linux", "windows"], required = True)
    version = StringProperty(exclude_if_none=True, default=None)

class MojangRule (JsonObject):
    action = StringProperty(choices=["allow", "disallow"], required = True)
    os = ObjectProperty(OSRule, exclude_if_none=True, default=None)

class MojangLibrary (JsonObject):
    extract = ObjectProperty(MojangLibraryExtractRules, exclude_if_none=True, default=None)
    name = GradleSpecifierProperty(required = True)
    downloads = ObjectProperty(MojangLibraryDownloads, exclude_if_none=True, default=None)
    natives = DictProperty(StringProperty, exclude_if_none=True, default=None)
    rules = ListProperty(MojangRule, exclude_if_none=True, default=None)

class MojangLoggingArtifact (MojangArtifactBase):
    id = StringProperty()

class MojangLogging (JsonObject):
    file = ObjectProperty(MojangLoggingArtifact, required = True)
    argument = StringProperty(required = True)
    type = StringProperty(required = True, choices=["log4j2-xml"])

class UnknownMojangVersionException(Exception):
    """Exception raised for unknown Mojang version file format versions.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message

def validateSupportedMojangVersion(version):
    supportedVersion = 18
    if version > supportedVersion:
        raise UnknownMojangVersionException("Unsupported Mojang format version: %d. Max supported is: %d" % (version, supportedVersion))

class MojangVersionFile (JsonObject):
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    assets = StringProperty(exclude_if_none=True, default=None)
    downloads = DictProperty(MojangArtifactBase, exclude_if_none=True, default=None)
    id = StringProperty(exclude_if_none=True, default=None)
    libraries = ListProperty(MojangLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    processArguments = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    minimumLauncherVersion = IntegerProperty(exclude_if_none=True, default=None, validators=validateSupportedMojangVersion)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    time = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)
    logging = DictProperty(MojangLogging, exclude_if_none=True, default=None)

class MultiMCVersionFile (JsonObject):
    name = StringProperty(required=True)
    version = StringProperty(required=True)
    fileId = StringProperty(required=True)
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    downloads = DictProperty(MojangArtifactBase, exclude_if_none=True, default=None)
    libraries = ListProperty(MojangLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    appletClass = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    time = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)

def MojangToMultiMC (file, name, fileId, version):
    mmcFile = MultiMCVersionFile(
        {
            "name": name,
            "fileId": fileId,
            "version": version
        }
    )
    mmcFile.assetIndex = file.assetIndex
    mmcFile.downloads = file.downloads
    mmcFile.libraries = file.libraries
    mmcFile.mainClass = file.mainClass
    mmcFile.minecraftArguments = file.minecraftArguments
    mmcFile.releaseTime = file.releaseTime
    # time should not be set.
    mmcFile.type = file.type
    return mmcFile

'''
The MultiMC static override file for legacy looks like this:
{
    "versions": [
        ...
        {
            "id": "c0.0.13a",
            "checksum": "3617fbf5fbfd2b837ebf5ceb63584908",
            "releaseTime": "2009-05-31T00:00:00+02:00",
            "type": "old_alpha",
            "mainClass": "com.mojang.minecraft.Minecraft",
            "appletClass": "com.mojang.minecraft.MinecraftApplet",
            "+traits": ["legacyLaunch", "no-texturepacks"]
        },
        ...
    ]
}
'''

class LegacyOverrideEntry(JsonObject):
    id = StringProperty()
    checksum = StringProperty()
    releaseTime = ISOTimestampProperty()
    type = StringProperty()
    mainClass = StringProperty()
    appletClass = StringProperty()
    addTraits = ListProperty(StringProperty, name="+traits")

class LegacyOverrideIndex(JsonObject):
    versions = ListProperty(LegacyOverrideEntry)

class LegacyOverrideIndexWrap:
    def __init__(self, json):
        self.index = MojangIndex.wrap(json)
        versionsDict = {}
        for version in self.index.versions:
            versionsDict[version.id] = version
        self.versions = versionsDict