#!/usr/bin/env python

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from urllib.parse import unquote
import speechManager
import config

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app)

@app.route('/voices/', methods=['GET'])
def voices():
    voices = speechManager.getVoices()
    return jsonify(voices)


@app.route('/speak/<path:text>/', methods=['POST', 'GET'])
@app.route('/speak/<path:text>/<providerId>/', methods=['POST', 'GET'])
@app.route('/speak/<path:text>/<providerId>/<voiceId>', methods=['POST', 'GET'])
def speak(text, providerId="", voiceId=""):
    text = unquote(text).lower()
    providerId = unquote(providerId)
    voiceId = unquote(voiceId)
    speechManager.speak(text, providerId, voiceId)
    return jsonify(True)

@app.route('/speakdata/<path:text>/', methods=['POST', 'GET'])
@app.route('/speakdata/<path:text>/<providerId>/', methods=['POST', 'GET'])
@app.route('/speakdata/<path:text>/<providerId>/<voiceId>', methods=['POST', 'GET'])
def speakData(text, providerId="", voiceId=""):
    text = unquote(text).lower()
    providerId = unquote(providerId)
    voiceId = unquote(voiceId)
    data = speechManager.getSpeakData(text, providerId, voiceId)
    response = make_response(data)
    response.headers.set('Content-Type', 'application/octet-stream')
    return response

@app.route('/cache/<path:text>/<providerId>/<voiceId>', methods=['POST', 'GET'])
def cacheData(text, providerId="", voiceId=""):
    if not config.cacheData:
        return jsonify(False)
    text = unquote(text).lower()
    providerId = unquote(providerId)
    voiceId = unquote(voiceId)
    speechManager.getSpeakData(text, providerId, voiceId)
    return jsonify(True)

@app.route('/speaking/', methods=['GET'])
def speaking():
    speaking = speechManager.isSpeaking()
    return jsonify(speaking)


@app.route('/stop/', methods=['GET', 'POST'])
def stop():
    speechManager.stop()
    return jsonify(True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, threaded=True)
