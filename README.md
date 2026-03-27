# Asterics-AAC-Helper
Helper tools to enable [Asterics AAC](https://github.com/asterics/Asterics-AAC) to do actions on the operating system or integrations with external services, which aren't possible within the browser. 
Currently two types of helper applications are provided, one for speech and one for interaction (e.g. with COM/Serial ports) - see folder  [interaction](https://github.com/asterics/Asterics-AAC-Helper/tree/main/interaction).

## Speech
Normally Asterics AAC uses the [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) and therefore voices that are installed on the operating system (e.g. SAPI voices on Windows, or voices that are coming from a TTS module on Android). Sometimes it's interesting to use voices, which aren't available as system voices. This section describes how to use an external custom speech service using Python.

### Terms
* **Speech provider**: a Python module that implements access to a speech generating service like [MS Azure](https://azure.microsoft.com/en-us/products/ai-services/text-to-speech), [Amazon Polly](https://aws.amazon.com/polly/), [Piper](https://github.com/rhasspy/piper), [MycroftAI mimic3](https://github.com/MycroftAI/mimic3) or any others. Speech providers can have two types:
   * **type "playing"**: a speech provider where playing the audio file is done internally. Using a speech provider of this type only makes sense, if it's used on the same machine as Asterics AAC.
   * **type "data"**: a speech provider that generates the speech audio data, which then is used by Asterics AAC and played within the browser. This type is preferable, because it makes it possible to run the speech service on any device or server and also allows caching of the data.

### Installation and Usage
#### Speech Service
These steps are necessary to start the speech service that can be used by Asterics AAC:
* `pip install flask flask_cors` - for installing Flask, which is needed for providing the REST API
* `pip install pyttsx3` - only if you want to try the speech provider `provider_pytts_playing.py` which is configured by default in `config.py`, otherwise install any other dependencies needed by the used speech providers, see [predefined speech providers](#speech-providers).
* adapt [config.py](https://github.com/asterics/Asterics-AAC-Helper/blob/main/speech/config.py) for using the desired speech providers by importing them and adding them to the list `speechProviderList`.
* `python start.py` - to start the REST API

#### Asterics AAC
In Asterics AAC do the following steps to use the external speech provider:
* Go to `Settings -> General Settings -> Advanced general settings`
* Configure the `External speech service URL` with the IP/host where the API is running, port `5555`. If the speech service is running on the same computer, use `http://localhost:5555`.
* Reload Asterics AAC (`F5`)
* Go to `Settings -> User settings -> Voice` and enable `Show all voices`
* Verify that the additional voices are selectable and working. For the default `provider_pytts_playing` speech provider some voices like `<voice name>, pytts_playing` should be listed.

#### Caching
For speech providers with type "data", all generated speech data is automatically cached to the folder `speech/temp`. If you want to cache speech data for a whole Asterics AAC configuration follow these steps:
* configure Asterics AAC to use your desired speech provider / voice (see steps above)
* go to `Settings -> User settings -> Voice -> Advanced voice settings` and click the button `Cache all texts of current configuration using external voice`. This operation may take some time for big Asterics AAC configurations.

### Files
These are the important files within the folder `speech` of this repository:
* `config.py` configuration file where it's possible to define which speech providers should be used
* `provider_<name>_playing.py` implementation of a speech provider which generates speech and plays audio on its own
* `provider_<name>_data.py` implementation of a speech provider which generates speech audio data and returns the binary data, which then is played by Asterics AAC within the browser
* `start.py` main script providing a REST API which can be used by Asterics AAC
* `speechManager.py` script which manages different speech providers and is used to access them by the API defined in `start.py`

### Speech providers
This is a list of predefined speech providers with installation hints:
* **mimic3_data**: see [Mimic 3 installation steps](https://mycroft-ai.gitbook.io/docs/mycroft-technologies/mimic-tts/mimic-3), install in any way which provides `mimic3` as CLI-tool, which is used by the speech provider. The current implementation only uses the voice `en_UK/apope_low`, for further voices the file `provider_mimic3_data.py` must be adapted.
* **msazure_data, msazure_playing**:
   * run `pip install azure-cognitiveservices-speech`, for further information see [MS Azure TTS quickstart](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech?tabs=windows%2Cterminal&pivots=programming-language-python)
   * to get API credentials, you have to [sign-up at MS Azure](https://azure.microsoft.com/de-de/get-started/azure-portal) and create a `SpeechServices` resource.
   * Create a file `speech/credentials.py` including two lines `AZURE_KEY_1 = "<your-key>"` and `AZURE_REGION = "<your-region>"`
* **piper_data**: run `pip install piper-tts`, for more information see [Running Piper in Python](https://github.com/rhasspy/piper?tab=readme-ov-file#running-in-python).
* **pytts_playing**: run `pip install pyttsx3`
* **elevenlabs_data** run `pip install requests` and create a file `speech/credentials.py` with `ELEVENLABS_KEY = "<your-key>"`. Read [here how to get the API key](https://elevenlabs.io/docs/api-reference/text-to-speech#authentication).

#### Configuration
See [config.py](https://github.com/asterics/Asterics-AAC-Helper/blob/main/speech/config.py), where the speech providers to use can be imported and added to the list `speechProviderList`.

#### Adding new speech providers
Use the templates [provider_template_data.py](https://github.com/asterics/Asterics-AAC-Helper/blob/main/speech/provider_template_data.py) or [provider_template_playing.py](https://github.com/asterics/Asterics-AAC-Helper/blob/main/speech/provider_template_playing.py) depending on which type of speech provider you want to add and implement the predefined methods.

### REST API
The file `speech/start.py` starts the REST API with the following endpoints:
* `/voices` returns a list of voices that are existing within the current configuration.
* `/speak/<text>/<providerId>/<voiceId>` speaks the given text using the given provider and voice.
* `/speakdata/<text>/<providerId>/<voiceId>` returns the binary audio data for the text using the given provider and voice.
* `/cache/<text>/<providerId>/<voiceId>` caches the audio data for the given parameters to a file in `speech/temp` in order to be able to use it faster or without internet connection afterwards.
* `/speaking` returns `true` if the system is currently speaking (only applicable for voice type "speaking")

### Wordforms
Api to extract wordforms
For further reading click on [wordforms](wordforms/README.md)
