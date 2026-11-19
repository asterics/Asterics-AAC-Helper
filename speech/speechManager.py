import config
import constants
import util

requiredFnsAll = ["getProviderId", "getVoiceType", "getVoices"]
requiredFnsPlaying = ["speak", "isSpeaking", "stop"]
requiredFnsData = ["getSpeakData"]
requiredVoiceKeys = ["id", "name"]

speechProviders = {}

def speak(text, providerId, voiceId=None):
    provider = speechProviders[providerId] if providerId in speechProviders else config.speechProviderList[0]
    if not hasattr(provider, "speak"):
        return print("ERROR: speech provider '{}' doesn't implement function 'speak'!".format(providerId))
    provider.speak(text, voiceId)

def getSpeakData(text, providerId, voiceId=None):
    if config.cacheData:
        cachedData = util.getCacheData(text, providerId, voiceId)
        if cachedData:
            return cachedData
    provider = speechProviders[providerId] if providerId in speechProviders else config.speechProviderList[0]
    if not hasattr(provider, "getSpeakData"):
        return print("ERROR: speech provider '{}' doesn't implement function 'getSpeakData'!".format(providerId))
    data = provider.getSpeakData(text, voiceId)
    if config.cacheData and data and len(data) > 0:
        util.saveCacheData(text, providerId, voiceId, data)
    return data

def isSpeaking():
    for provider in speechProviders.values():
        if hasattr(provider, "isSpeaking") and provider.isSpeaking():
            return True
    return False

def stop():
    for provider in speechProviders.values():
        if hasattr(provider, "stop"):
            provider.stop()

def getVoices():
    cachedVoices = util.getCachedVoices()
    if cachedVoices is not None and len(cachedVoices) > 0:
        print("Using cached voices from 'temp/voices.json'...")
        return cachedVoices

    print("Building voice catalog from speech providers...")
    allVoices = []
    for provider in config.speechProviderList:
        voices = provider.getVoices()
        for voice in voices:
            voice["providerId"] = provider.getProviderId()
            voice["type"] = provider.getVoiceType()
            voice["name"] = voice["name"] + ", " + provider.getProviderId()
            allVoices.append(voice)

    util.saveCachedVoices(allVoices)
    return allVoices

def initProviders():
    for provider in config.speechProviderList:
        id = provider.getProviderId() if hasattr(provider, "getProviderId") else "fill_provider_id"
        if id == "fill_provider_id":
            raise Exception("ERROR: '{}' is an invalid provider ID!".format(id))

        if id in speechProviders:
            raise Exception("ERROR: duplicated speech provider with ID '{}'!".format(id))

        for fnName in requiredFnsAll:
            if not hasattr(provider, fnName):
                raise Exception("ERROR: speech provider '{}' doesn't implement function '{}'!".format(id, fnName))

        voiceType = provider.getVoiceType()
        additionalRequiredFns = None
        if voiceType == constants.VOICE_TYPE_EXTERNAL_PLAYING:
            additionalRequiredFns = requiredFnsPlaying
        elif voiceType == constants.VOICE_TYPE_EXTERNAL_DATA:
            additionalRequiredFns = requiredFnsData
        else:
            raise Exception("ERROR: voice type of provider '{}' invalid (must be '{}' or '{}')!".format(id, constants.VOICE_TYPE_EXTERNAL_PLAYING, constants.VOICE_TYPE_EXTERNAL_DATA))

        for fnName in additionalRequiredFns:
            if not hasattr(provider, fnName):
                raise Exception("ERROR: speech provider '{}' doesn't implement function '{}'!".format(id, fnName))

        voices = provider.getVoices()
        for voice in voices:
            name = voice["id"] or voice["name"] or "noVoiceName"
            for key in requiredVoiceKeys:
                if key not in voice:
                    raise Exception("ERROR: voice '{}' of provider '{}' doesn't have required key '{}'!".format(name, id, key))

        speechProviders[id] = provider # store in map

initProviders()
