// Import necessary packages
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'package:logging/logging.dart';

class WebSocketService {
  final String uri = 'ws://192.168.1.7:8080'; // Default WebSocket server URI
  WebSocketChannel? _channel;
  final Logger _logger = Logger('WebSocketService');

  WebSocketService();

  // Initialize WebSocket connection
  void connect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(uri));
      _logger.info("Connected to WebSocket server at $uri");

      // _channel!.stream.listen(
      //   (message) {
      //     _logger.info("Message received: $message");
      //   },
      //   onError: (error) {
      //     _logger.severe("Error receiving message: $error");
      //   },
      //   onDone: () {
      //     _logger.info("Connection closed by the server.");
      //   },
      // );
    } catch (e) {
      _logger.severe("Failed to connect to WebSocket server: $e");
    }
  }

  // Send message to WebSocket server
  void sendMessage(String message) {
    try {
      if (_channel != null) {
        _channel!.sink.add(message);
        _logger.info("Message sent: $message");
      } else {
        _logger.warning(
            "WebSocket is not connected. Please call connect() first.");
      }
    } catch (e) {
      _logger.severe("Failed to send message: $e");
    }
  }

  // Listen for messages from WebSocket server
  Stream get messages {
    try {
      if (_channel != null) {
        _logger.info("Listening for messages from WebSocket server.");
        return _channel!.stream.asBroadcastStream();
      } else {
        _logger.warning(
            "WebSocket is not connected. Please call connect() first.");
        throw Exception("WebSocket is not connected.");
      }
    } catch (e) {
      _logger.severe("Failed to listen for messages: $e");
      rethrow;
    }
  }

  // Close WebSocket connection
  void disconnect() {
    try {
      if (_channel != null) {
        _channel!.sink.close(status.normalClosure);
        _logger.info("Disconnected from WebSocket server");
      } else {
        _logger.warning("WebSocket is not connected.");
      }
    } catch (e) {
      _logger.severe("Failed to disconnect from WebSocket server: $e");
    }
  }
}
