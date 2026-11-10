import io
from threading import RLock

import constants
from pocket_tts import TTSModel
import scipy.io.wavfile
import sounddevice as sd
import numpy as np

speaking = False
providerId = "pockettts"

supportedLanguages = (
#    "english_2026-01",
#    "english_2026-04",
#    "english_2026-09",
#    "english_2026-09_2",
#    "english_2026-10",
#    "english_drifting_26-09",
#    "english_18m_2026-10",
#    "english_18m_refl_2026-10",
#    "english_7m_2026-10",
#    "english_7m_refl_2026-10",
    "english_2m_2026-10",
#    "english_2m_refl_2026-10",
    "english",
    "french",
#    "french_24l",
    "german",
#    "german_24l",
#    "portuguese",
#    "portuguese_24l",
#    "italian",
#    "italian_24l",
    "spanish",
#    "spanish_24l",
#    "dutch",
#    "dutch_24l",
)

englishVoices = (
    ("alba", "Alba"),
    ("anna", "Anna"),
    ("azelma", "Azelma"),
    ("bill_boerst", "Bill Boerst"),
    ("caro_davy", "Caro Davy"),
    ("charles", "Charles"),
    ("cosette", "Cosette"),
    ("eponine", "Eponine"),
    ("eve", "Eve"),
    ("fantine", "Fantine"),
    ("george", "George"),
    ("jane", "Jane"),
    ("jean", "Jean"),
    ("javert", "Javert"),
    ("marius", "Marius"),
    ("mary", "Mary"),
    ("michael", "Michael"),
    ("paul", "Paul"),
    ("peter_yearsley", "Peter Yearsley"),
    ("stuart_bell", "Stuart Bell"),
    ("vera", "Vera"),
)

lang2LangCode = {
    "english": "en",
    "french": "fr",
    "german": "de",
    "portuguese": "pt",
    "italian": "it",
    "spanish": "es",
    "dutch": "nl",
}

voicesByLanguage = {
    "english": ((englishVoices)),
    "french": (("estelle", "Estelle"),),
    "german": (("juergen", "Juergen"),) + englishVoices,
    "portuguese": (("rafael", "Rafael"),),
    "italian": (("giovanni", "Giovanni"),),
    "spanish": (("lola", "Lola"),)+englishVoices,
    "dutch": (("daan", "Daan"),)
}

speechModels = {}
voiceStates = {}
modelsLock = RLock()


def getProviderId():
    return providerId


def getVoiceType():
    return constants.VOICE_TYPE_EXTERNAL_PLAYING


def getVoices():
    allVoices = []
    for modelId in supportedLanguages:
        language = modelId.split("_", 1)[0]
        languageCode = lang2LangCode.get(language, "en")
        voices = voicesByLanguage[language]
        for voiceId, voiceName in voices:
            allVoices.append({
                "id": "{}--{}".format(modelId, voiceId),
                "name": "{} ({})".format(voiceName, modelId),
                "lang": languageCode,
                "local": True,
            })
    return allVoices


def preload_models():
    with modelsLock:
        for language in supportedLanguages:
            if language not in speechModels:
                speechModels[language] = TTSModel.load_model(language=language,temp=0.0,quantize=True)

def speak(text, voiceId=None):
    # directly speak the text with the given voiceId
    print("Pocket TTS speak: '{}' with voiceId: {}".format(text, voiceId))
    global speaking
    stop()
    if speaking:
        return

    speaking = True
    model, voiceState = checkVoiceIdandGetModel(voiceId)
    
    with sd.OutputStream(samplerate=model.sample_rate, channels=1, dtype="float32") as stream:
        for chunk in model.generate_audio_stream(voiceState, text):
            samples = chunk.detach().cpu().numpy().astype(np.float32, copy=False)
            stream.write(samples.reshape(-1, 1))
    sd.wait()
    speaking = False

def isSpeaking():
    # return True if currently speaking
    global speaking
    return speaking

def stop():
    # stop speaking
    global speaking
    sd.stop()
    speaking = False
    return

def checkVoiceIdandGetModel(voiceId):
    print("Pocket TTS voiceId: {}".format(voiceId))
    if voiceId:
        if "--" in voiceId:
            modelId, _, presetVoiceId = voiceId.partition("--")
            if modelId not in supportedLanguages:
                raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))
        elif voiceId == "alba":
            modelId, presetVoiceId = "english", voiceId
        else:
            raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))
    else:
        modelId, presetVoiceId = "english", "alba"

    language = modelId.split("_", 1)[0]
    allowedVoiceIds = {voice[0] for voice in voicesByLanguage[language]}
    print("Allowed voice IDs for language '{}': {}".format(language, allowedVoiceIds))
    if presetVoiceId not in allowedVoiceIds:
        raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))

    with modelsLock:
        model = speechModels.get(modelId)
        if model is None:
            raise RuntimeError("Pocket TTS model '{}' has not been preloaded".format(modelId))

        stateKey = (modelId, presetVoiceId)
        voiceState = voiceStates.get(stateKey)
        if voiceState is None:
            voiceState = model.get_state_for_audio_prompt(presetVoiceId)
            voiceStates[stateKey] = voiceState
    return model,voiceState


preload_models()
