import io
from threading import RLock

import constants
from pocket_tts import TTSModel
import scipy.io.wavfile

providerId = "pockettts"

supportedLanguages = (
    "english_2026-01",
    "english_2026-04",
    "english_2026-09",
    "english_2026-09_2",
    "english_2026-10",
    "english_drifting_26-09",
    "english_18m_2026-10",
    "english_18m_refl_2026-10",
    "english_7m_2026-10",
    "english_7m_refl_2026-10",
    "english_2m_2026-10",
    "english_2m_refl_2026-10",
    "english",
    "french",
    "french_24l",
    "german",
    "german_24l",
    "portuguese",
    "portuguese_24l",
    "italian",
    "italian_24l",
    "spanish",
    "spanish_24l",
    "dutch",
    "dutch_24l",
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

voicesByLanguage = {
    "english": ("en", englishVoices),
    "french": ("fr", (("estelle", "Estelle"),)),
    "german": ("de", (("juergen", "Juergen"),)),
    "portuguese": ("pt", (("rafael", "Rafael"),)),
    "italian": ("it", (("giovanni", "Giovanni"),)),
    "spanish": ("es", (("lola", "Lola"),)),
    "dutch": ("nl", (("daan", "Daan"),)),
}

speechModels = {}
voiceStates = {}
modelsLock = RLock()


def getProviderId():
    return providerId


def getVoiceType():
    return constants.VOICE_TYPE_EXTERNAL_DATA


def getVoices():
    allVoices = []
    for modelId in supportedLanguages:
        language = modelId.split("_", 1)[0]
        languageCode, voices = voicesByLanguage[language]
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
                speechModels[language] = TTSModel.load_model(language=language)


def getSpeakData(text, voiceId=None):
    model, voiceState = checkVoiceIdandGetModel(voiceId)

    audio = model.generate_audio(voiceState, text)
    samples = audio.detach().cpu().numpy()
    buffer = io.BytesIO()
    scipy.io.wavfile.write(buffer, model.sample_rate, samples)
    return buffer.getvalue()

def checkVoiceIdandGetModel(voiceId):
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
    allowedVoiceIds = {voice[0] for voice in voicesByLanguage[language][1]}
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
