import os
from urllib.parse import quote
import json

def getCachedVoices():
    """Returns the cached voices from 'temp/voices.json' if it exists, otherwise returns None."""
    currentDir = os.path.dirname(__file__)
    dirname = os.path.join(currentDir, "temp")
    if not os.path.exists(dirname):
        return None
    voicesFilePath = os.path.join(dirname, "voices.json")
    if not os.path.isfile(voicesFilePath):
        return None
    with open(voicesFilePath, "r") as voicesFile:
        voicesData = json.load(voicesFile)
    return voicesData

def saveCachedVoices(voicesList):
    """Saves the list of voices to 'temp/voices.json'."""
    currentDir = os.path.dirname(__file__)
    dirname = os.path.join(currentDir, "temp")
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    voicesFilePath = os.path.join(dirname, "voices.json")
    with open(voicesFilePath, "w") as voicesFile:
        json.dump(voicesList, voicesFile)

def getTempFilename(providerId):
    providerId = getSafeString(providerId)
    return "temp_{}.wav".format(providerId)

def getTempFileFullPath(providerId):
    providerId = getSafeString(providerId)
    currentDir = os.path.dirname(__file__)
    dirname = os.path.join(currentDir, "temp")
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    return os.path.join(dirname, getTempFilename(providerId))

def getCacheFileFullPath(text, providerId, voiceId):
    providerId = getSafeString(providerId)
    text = quote(text)
    voiceId = getSafeString(str(voiceId))
    currentDir = os.path.dirname(__file__)
    dirname = os.path.join(currentDir, "temp", providerId, voiceId)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return os.path.join(dirname, "{}.wav".format(text))

def getTempFileData(providerId):
    path = getTempFileFullPath(providerId)
    in_file = open(path, "rb")
    data = in_file.read()
    in_file.close()
    return data

def saveCacheData(text, providerId, voiceId, data):
    path = getCacheFileFullPath(text, providerId, voiceId)
    out_file = open(path, "wb")
    out_file.write(data)
    out_file.close()

def getCacheData(text, providerId, voiceId):
    data = None
    path = getCacheFileFullPath(text, providerId, voiceId)
    if os.path.isfile(path):
        in_file = open(path, "rb")
        data = in_file.read()
        in_file.close()
    return data

def getSafeString(string):
    keepcharacters = (' ','.','_', '-')
    return "".join(c for c in string if c.isalnum() or c in keepcharacters).rstrip()
