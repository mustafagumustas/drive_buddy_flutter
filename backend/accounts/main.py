from langchain.agents import AgentExecutor, create_tool_calling_agent

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
from mem0 import Memory
import spotipy
import dotenv
import os
import base64
from io import BytesIO
from pydub import AudioSegment
from django.conf import settings
from django.http import JsonResponse


from pydantic import ConfigDict
from openai import OpenAI
import io

from music_manager import play_track_on_device
from accounts.voice_activity_detection import SpeechRecorder


llm = ChatOpenAI(model="gpt-4o-mini")

client = OpenAI()

drive_buddy_main_prompt = """You are a drive buddy application for drivers, a co-pilot.
It's a GPT that accompanies people who are driving, like a live radio.

Your job is to keeping company with the driver along the way.

At the first usage, if the user hasn't used you before, you need to get to know the driver. His name and surname, his age, where he lives, his car model, and favorite music genres are the most important ones. Then you can learn about his topic of interests. 
Then ask about what do they want to call you at the first time. Suggest the user "Drive Buddy" as a default name if they cannot decide. Your name is whatever the driver wants. 
Ask the questions one-by-one like you are having a chat, not like an interview.

If it's not the first time, welcome the user with their name, and give them information about the weather. (E.g., "Good morning, John! Ready to hit the road?")

You are a friend of the driver. You need to keep them updated along the way (like weather conditions, highway blocks, etc.). So, get to know where the driver wants to go.

You generally do the same thing as a radio station does, but you are also a friend of the driver. While playing the songs from the connected apps via API, you also give news about the topics he/she likes (including sports scores, stock market updates, or technology news, depending on the driver's preferences). This should happen like a normal radio show, using your voice like a female radio broadcaster. You are energetic, friendly, deeply connected, and warm. You can also encourage the driver to share their thoughts or stories.

Along the way, you keep learning about the driver. Don't let them lose their attention from the road and driving. You can ask them if they are tired or sleepy, giving them a reminder from time to time to drive safely. But do it in a friendly manner.

Update your language according to the user's main language and speak that language with them.
                                   
Use the provided context to personalize your responses and remember user preferences and past interactions.

Example Interaction Flow:

Initial Setup:
"Hi there! I'm your new driving companion. Can I get your name and a few details about you?"
Gather information about the driver's name, age, interests, car model, and favorite music genres.

Daily Commute:
"Good morning, Sarah! How's it going? Ready to drive your Ford Mustang today?"
"The weather looks clear, but there's some traffic on your usual route to work. Would you like me to find an alternative route?"

Music and Updates:
"Here's your favorite rock playlist to kickstart your day. Did you know that this song was a top hit in 1985?"
"In the news today, there's been an interesting development in tech…"

Safety Check:
"Hey Sarah, you've been driving for about two hours. How about a quick break at the next rest area? There's a nice coffee shop there."
"Remember, staying hydrated is important. Don't forget to drink some water!"

Engagement:
"Want to hear a fun fact about your car? The Mustang was first introduced in 1964 and has a fascinating history…"
"Feeling tired? Let's do a quick alertness exercise together."

                                   """
# Spotify API setup
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id="558d85247ba44b39b0f9f5bcc29fe7a3",
        client_secret="669db1d3587142aab4dd15f519c3407f",
        redirect_uri="http://localhost:8888/callback",
        scope="user-read-playback-state,user-modify-playback-state",
    )
)

# server neo4j
load_status = dotenv.load_dotenv("accounts/variables.txt")
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
USR = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
config = {
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": URI, "username": USR, "password": PASSWORD},
    },
    "version": "v1.1",
}

mem0 = Memory.from_config(config)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


# Define the State
class State(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]
    mem0_user_id: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


graph = StateGraph(State)

chat_history = []


def transform_data(data):
    transformed = []
    for item in data:
        # Create the string with square brackets instead of curly braces, and remove quotes
        transformed_item = f"[{item['destination']}, relation: {item['relation']}, source: {item['source']}]"
        transformed.append(transformed_item)
    return transformed


def chatbot(state: State):
    messages = state["messages"]
    user_id = state["mem0_user_id"]

    # mem0.delete_all(user_id="mustafa_gumustas")
    # Retrieve relevant memories
    memories = mem0.search(messages[-1].content, user_id=user_id, limit=5)
    context = "Relevant information from previous conversations:\n"
    if memories["entities"]:
        context += "Entities:\n"
        context += f"{transform_data(memories['entities'])}"
    if memories["memories"]:
        context += "Memories:\n"
        for memory in memories["memories"]:
            context += f"- {memory['memory']}\n"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", drive_buddy_main_prompt),
            ("placeholder", "{chat_history}"),
            ("human", messages[-1].content),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    tools = [play_track_on_device]
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    chat_history.append(HumanMessage(messages[-1].content))
    response = agent_executor.invoke(
        {
            "input": messages,
            "chat_history": chat_history,
        }
    )
    chat_history.append(AIMessage(response["output"]))
    mem0.add(
        f"User: {messages[-1].content}\nAssistant: {response["output"]}",
        user_id=user_id,
    )
    return {"messages": [AIMessage(content=response["output"])]}


graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", "chatbot")
compiled_graph = graph.compile()


def run_conversation(mem0_user_id: str, first_run: bool, audio_base64: str = None):
    first_run = first_run
    try:
        if first_run:
            print("this is the first run")
            user_info = mem0.search(
                f"who is {mem0_user_id}", user_id=mem0_user_id, limit=5
            )
            user_input = f"""Hello this is {mem0_user_id}. Please greet me using this info: {transform_data(user_info["entities"][:10])}"""
        else:
            print("this is the not the first run")
            if audio_base64:
                # Decode base64 to audio
                audio_data = base64.b64decode(audio_base64)
                audio_io = BytesIO(audio_data)

                # Use pydub to handle audio data as needed
                audio_segment = AudioSegment.from_file(audio_io, format="wav")

                # Process audio_segment as required for your application
                user_input = "Processed audio input"  # Replace with the actual transcription or further processing
            else:
                user_input = "No audio input provided"

        config = {"configurable": {"thread_id": mem0_user_id}}
        state = {
            "messages": [HumanMessage(content=user_input)],
            "mem0_user_id": mem0_user_id,
        }

        for event in compiled_graph.stream(state, config):
            for value in event.values():
                if value.get("messages"):
                    response_text = value["messages"][-1].content
                    return response_text
        return response_text
    finally:
        return response_text


def gpt_speech(gpt_response_text):
    with client.audio.speech.with_streaming_response.create(
        model="tts-1", voice="alloy", input=gpt_response_text
    ) as response:
        audio_data = response.read()
        # Save the MP3 file on the server
        audio_path = os.path.join(settings.MEDIA_ROOT, "speech.mp3")
        with open(audio_path, "wb") as audio_file:
            audio_file.write(response["data"])

    return audio_path
