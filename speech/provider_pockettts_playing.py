"""Pocket TTS speech provider that streams generated audio to a local playback device.
   See https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/
"""

import provider_pockettts_utils
import constants
import sounddevice as sd
import numpy as np

# Track playback state across calls because the provider has no persistent object.
speaking = False

def getProviderId():
    """Return the stable identifier used to register this speech provider."""
    return provider_pockettts_utils.getProviderId()

def getVoiceType():
    """Return the provider mode indicating that playback is performed locally."""
    return constants.VOICE_TYPE_EXTERNAL_PLAYING

def getVoices():
    """Build the provider voice catalog with model, name, language, and locality data."""
    return provider_pockettts_utils.getVoices()

def speak(text, voiceId=None):
    """Stop existing playback, start audio synthesis streaming, and do local playback."""
    #print("Pocket TTS speak: '{}' with voiceId: {}".format(text, voiceId))
    global speaking
    if isSpeaking():
        stop()        

    speaking = True
    model, voiceState = provider_pockettts_utils.checkVoiceIdandGetModel(voiceId)
    
    with sd.OutputStream(samplerate=model.sample_rate, channels=1, dtype="float32") as stream:
        for chunk in model.generate_audio_stream(voiceState, text):
            # Pocket TTS produces tensors, while sounddevice accepts NumPy float32 arrays.
            samples = chunk.detach().cpu().numpy().astype(np.float32, copy=False)
            stream.write(samples.reshape(-1, 1))
    # Wait for queued playback to finish before exposing the idle state.
    sd.wait()
    speaking = False

def stop():
    """Stop audio output immediately and reset provider playback state."""
    global speaking
    sd.stop()
    speaking = False
    return    

def isSpeaking():
    """Return whether this provider currently considers playback active."""
    return speaking
