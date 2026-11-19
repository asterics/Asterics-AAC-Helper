"""Pocket TTS speech provider that streams generated audio to a local playback device.
   See https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/
"""

from pathlib import Path
from threading import RLock

import constants
from pocket_tts import TTSModel
import sounddevice as sd
import numpy as np

# Track playback state across calls because the provider has no persistent object.
speaking = False
providerId = "pockettts"

# Only models in this tuple are offered or accepted by the provider.
# Please have a look at the Pocket TTS API documentation for the latest 
# supported models and voices.

supportedModels = (
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
    "portuguese",
#    "portuguese_24l",
    "italian",
#    "italian_24l",
    "spanish",
#    "spanish_24l",
    "dutch",
#    "dutch_24l",
)

# The names (right) of the built-in voices are used in the provider's voice catalog, 
# while the IDs are used to select them.
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

# Voices to be cloned can be provided as WAV files in the "clones" subdirectory. 
# The voice name is derived from the file name.
clonedVoices = tuple(
    (wav_file.name, wav_file.stem.replace("_", " ").title()+" (Clone)")
    for wav_file in sorted((Path(__file__).parent / "clones").glob("*.wav"))
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

# Combine built-in voices and locally discovered clones for every language.
# This makes voices like Anna, Alba, and any user-provided clones available 
# for all supported languages.
voicesByLanguage = {
    "english": (englishVoices) + (clonedVoices),
    "french": (("estelle", "Estelle"),)+englishVoices + clonedVoices,
    "german": (("juergen", "Juergen"),) + englishVoices + clonedVoices,
    "portuguese": (("rafael", "Rafael"),)+englishVoices + clonedVoices,
    "italian": (("giovanni", "Giovanni"),)+englishVoices + clonedVoices,
    "spanish": (("lola", "Lola"),)+englishVoices + clonedVoices,
    "dutch": (("daan", "Daan"),)+englishVoices + clonedVoices
}

# Cache loaded models and voice states to avoid repeated initialization.
speechModels = {}
voiceStates = {}
modelsLock = RLock()

def getProviderId():
    """Return the stable identifier used to register this speech provider."""
    return providerId


def getVoiceType():
    """Return the provider mode indicating that playback uses an external audio device."""
    return constants.VOICE_TYPE_EXTERNAL_PLAYING


def getVoices():
    """Build the provider voice catalog with model, name, language, and locality data."""
    allVoices = []
    for modelId in supportedModels:
        # Derive the catalog language from the model name's language prefix.
        language = modelId.split("_", 1)[0]
        languageCode = lang2LangCode.get(language, "en")
        voices = voicesByLanguage[language]
        for voiceId, voiceName in voices:
            # The composite ID lets the provider select both model and voice.
            allVoices.append({
                "id": "{}--{}".format(modelId, voiceId),
                "name": "{} ({})".format(voiceName, modelId),
                "lang": languageCode,
                "local": True,
            })
    return allVoices

def speak(text, voiceId=None):
    """Stop existing playback, start audio synthesis streaming, and do local playback."""
    #print("Pocket TTS speak: '{}' with voiceId: {}".format(text, voiceId))
    global speaking
    # Repeated or overlapping requests must not start a second stream.
    stop()
    if speaking:
        return

    speaking = True
    model, voiceState = checkVoiceIdandGetModel(voiceId)
    
    with sd.OutputStream(samplerate=model.sample_rate, channels=1, dtype="float32") as stream:
        for chunk in model.generate_audio_stream(voiceState, text):
            # Pocket TTS produces tensors, while sounddevice accepts NumPy float32 arrays.
            samples = chunk.detach().cpu().numpy().astype(np.float32, copy=False)
            stream.write(samples.reshape(-1, 1))
    # Wait for queued playback to finish before exposing the idle state.
    sd.wait()
    speaking = False

def isSpeaking():
    """Return whether this provider currently considers playback active."""
    global speaking
    return speaking

def stop():
    """Stop audio output immediately and reset provider playback state."""
    global speaking
    sd.stop()
    speaking = False
    return

def checkVoiceIdandGetModel(voiceId):
    """Validate a composite voice ID and return its model and cached voice state.

    The voice ID format is "<model-id>--<voice-id>". A missing or invalid value raises
    ValueError so callers cannot silently receive an unsupported voice.
    """
    print("Pocket TTS voiceId: {}".format(voiceId))
    # English/Alba are retained as defaults for compatibility, though callers require an ID.
    modelId, presetVoiceId = "english", "alba"

    if voiceId:
        if "--" in voiceId:
            modelId, _, presetVoiceId = voiceId.partition("--")
            if modelId not in supportedModels:
                raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))
    else:
        raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))

    # Validate the voice against the voices available for this model's language.
    language = modelId.split("_", 1)[0]
    allowedVoiceIds = {voice[0] for voice in voicesByLanguage[language]}
    print("Allowed voice IDs for language '{}': {}".format(language, allowedVoiceIds))
    if presetVoiceId not in allowedVoiceIds:
        raise ValueError("Invalid Pocket TTS voice ID: '{}'".format(voiceId))

    with modelsLock:
        model = speechModels.get(modelId)
        if model is None:
            print("Loading Pocket TTS model for language '{}'".format(language))
            model = TTSModel.load_model(language=modelId,temp=0.0,quantize=True)
            speechModels[modelId] = model

        # Cache voice state independently per model and selected voice.
        stateKey = (modelId, presetVoiceId)
        voiceState = voiceStates.get(stateKey)
        if voiceState is None:
            if presetVoiceId not in {voice[0] for voice in clonedVoices}:
                print("Loading voice state for preset voice ID: '{}', modelId: '{}'".format(presetVoiceId, modelId))
                voiceState = model.get_state_for_audio_prompt(presetVoiceId)
                voiceStates[stateKey] = voiceState
            elif Path(__file__).parent / "clones" / presetVoiceId:
                print("Loading voice state for cloned voice ID: '{}', modelId: '{}'".format(presetVoiceId, modelId))
                voiceState = model.get_state_for_audio_prompt(str(Path(__file__).parent / "clones" / presetVoiceId))
                voiceStates[stateKey] = voiceState
    return model,voiceState
