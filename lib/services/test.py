import asyncio
import websockets

# WebSocket server address (replace with your backend server's IP)
SERVER_URI = "ws://192.168.1.4:8080"

async def test_websocket():
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            # Send the test text
            test_text = "this is a test"
            print(f"Sending: {test_text}")
            await websocket.send(test_text)

            # Receive and print the audio stream data
            print("Receiving audio data...")
            while True:
                audio_chunk = await websocket.recv()
                print(audio_chunk)
                print(f"Received audio chunk of size {len(audio_chunk)} bytes")
    except Exception as e:
        print(f"Error: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_websocket())
