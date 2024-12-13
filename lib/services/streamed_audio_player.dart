// Import necessary packages
import 'package:flutter_pcm_sound/flutter_pcm_sound.dart';
import 'dart:typed_data';
import 'package:logging/logging.dart';
import 'websocket_service.dart';

class AudioPlaybackHandler {
  final WebSocketService _webSocketService = WebSocketService();
  final Logger _logger = Logger('AudioPlaybackHandler');
  final List<Uint8List> _buffer = [];
  bool _isPlaying = false;
  bool _playTriggered = false;

  AudioPlaybackHandler() {
    _logger.info("Initializing AudioPlaybackHandler.");
    _webSocketService.connect();

    // Initialize the PCM audio system
    FlutterPcmSound.setup(sampleRate: 22050, channelCount: 1).then((_) {
      FlutterPcmSound.setFeedThreshold(8000);
      FlutterPcmSound.setFeedCallback(_feedPcmData);
    });

    // Listen to WebSocket messages
    _webSocketService.messages.listen(
      (data) {
        _handleIncomingPCM(data);
      },
      onError: (error) {
        _logger.severe("Error receiving PCM data: $error");
      },
      onDone: () {
        _logger.info("WebSocket connection closed.");
      },
    );
  }

  // Handle incoming PCM data
  void _handleIncomingPCM(dynamic data) {
    if (data is Uint8List) {
      _buffer.add(data);
      _logger.info("Buffered PCM data of size: ${data.length}");

      // Start playback as soon as enough data is buffered
      if (!_playTriggered && _buffer.length > 3) {
        // Adjust threshold as needed
        _playBufferedAudio();
      }
    } else {
      _logger.warning("Received non-PCM data.");
    }
  }

  // Feed PCM data to the player
  void _feedPcmData(int remainingFrames) async {
    if (_buffer.isEmpty) {
      _logger.warning("Buffer underrun: no PCM data available.");
      return;
    }

    final Uint8List chunk = _buffer.removeAt(0);
    await FlutterPcmSound.feed(
        PcmArrayInt16.fromList(chunk.buffer.asInt16List()));
    _logger.info("Fed PCM data of size: ${chunk.length}");
  }

  // Play buffered PCM data
  void _playBufferedAudio() async {
    if (_isPlaying) return;

    _isPlaying = true;
    _playTriggered = true;

    try {
      FlutterPcmSound.start();
      _logger.info("Playback started for PCM data.");
    } catch (e) {
      _logger.severe("Error starting PCM audio playback: $e");
      _isPlaying = false;
      _playTriggered = false;
    }
  }

  // Send a test message to the WebSocket server
  void handleTestMessage(String message) {
    try {
      _logger.info("Button pressed. Sending message to WebSocket: $message");
      _webSocketService.sendMessage(message);
    } catch (e) {
      _logger.severe("Failed to handle button press: $e");
    }
  }

  // Dispose resources
  void dispose() {
    _logger.info("Disposing AudioPlaybackHandler.");
    FlutterPcmSound.release();
    _webSocketService.disconnect();
  }
}
