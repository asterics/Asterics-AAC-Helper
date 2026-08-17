import requests  # Used for making HTTP requests
import json  # Used for working with JSON data
import constants
import credentials
import util

# Define constants for the script
CHUNK_SIZE = 1024  # Size of chunks to read/write at a time
XI_API_KEY = credentials.ELEVENLABS_KEY  # Your API key for authentication

providerId = "elevenlabs_data"

def getProviderId():
    return providerId

def getVoiceType():
    return constants.VOICE_TYPE_EXTERNAL_DATA

def getVoices():
    try:
        headers = {
          "Accept": "application/json",
          "xi-api-key": XI_API_KEY,
          "Content-Type": "application/json"
        }
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers=headers,
            timeout=10  # Avoid hanging forever
        )
        response.raise_for_status()  # Raises for 4xx/5xx responses

        data = response.json()

        voices = []
        for voice in data.get("voices", []):
            voices.append({
                "id": voice["voice_id"],
                "name": voice["name"],
                "lang": "de",
                "local": False
            })
            voices.append({
                "id": voice["voice_id"],
                "name": voice["name"],
                "lang": "en",
                "local": False
            })

        return voices

    except requests.exceptions.ConnectionError:
        print("Could not connect to the ElevenLabs API.")
        return []

    except requests.exceptions.Timeout:
        print("The request to ElevenLabs timed out.")
        return []

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return []

    except requests.exceptions.RequestException as e:
        # Catches any other requests-related exceptions
        print(f"Request failed: {e}")
        return []

    except ValueError:
        # response.json() failed
        print("Invalid JSON received from the API.")
        return []
        
#def getVoices():
#    headers = {
#      "Accept": "application/json",
#      "xi-api-key": XI_API_KEY,
#      "Content-Type": "application/json"
#    }
#    response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
#    data = response.json()
#    list = []
#    for voice in data['voices']:
#      list.append({"id": voice['voice_id'], "name": voice['name'], "lang": "de", "local": False}) # optional boolean property "local" to determine of online/offline voice
#      list.append({"id": voice['voice_id'], "name": voice['name'], "lang": "en", "local": False}) # optional boolean property "local" to determine of online/offline voice
#    return list

def getSpeakData(text, voiceId=None):
    # Construct the URL for the Text-to-Speech API request
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voiceId}/stream"
    headers = {
        "Accept": "application/json",
        "xi-api-key": XI_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    response = requests.post(tts_url, headers=headers, json=data, stream=True)
    path = util.getTempFileFullPath(providerId)
    if response.ok:
        # Open the output file in write-binary mode
        with open(path, "wb") as f:
            # Read the response in chunks and write to the file
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
        # Inform the user of success
        print("Audio stream saved successfully.")
        return util.getTempFileData(providerId)
    else:
        # Print the error message if the request was not successful
        print(response.text)
    return None
