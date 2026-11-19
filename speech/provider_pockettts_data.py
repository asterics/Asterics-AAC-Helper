"""Pocket TTS speech provider that returns the generated audio as WAV data.
   See https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/
"""

import provider_pockettts_utils
import constants
import io
import scipy.io.wavfile

def getProviderId():
    """Return the stable identifier used to register this speech provider."""
    return provider_pockettts_utils.getProviderId()

def getVoiceType():
    """Return the provider mode indicating that audio data is returned for external playback."""
    return constants.VOICE_TYPE_EXTERNAL_DATA

def getVoices():
    """Build the provider voice catalog with model, name, language, and locality data."""
    return provider_pockettts_utils.getVoices()

def getSpeakData(text, voiceId=None):
    """Return the generated audio data as a WAV data in bytes."""
    model, voiceState = provider_pockettts_utils.checkVoiceIdandGetModel(voiceId)

    # Generate the audio data for the given text and voice state.
    audio = model.generate_audio(voiceState, text)
    samples = audio.detach().cpu().numpy()

    # Convert the samples to WAV format and return as bytes.
    buffer = io.BytesIO()
    scipy.io.wavfile.write(buffer, model.sample_rate, samples)
    return buffer.getvalue()