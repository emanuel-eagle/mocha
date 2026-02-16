from fastapi import FastAPI
from pydantic import BaseModel
from utilities.SmartDevice import SmartDevice
from utilities.FuzzyMatching import FuzzyMatching
from utilities.OllamaChat import OllamaChat

app = FastAPI()

devices = SmartDevice()
fuzzy_matching = FuzzyMatching()

available_devices = devices.list_devices()
fuzzy_matching.set_threshold(80)
fuzzy_matching.set_items(available_devices)

ollama_chat = OllamaChat(devices, fuzzy_matching)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):
    response = ollama_chat.chat(request.message)
    return {"response": response}


@app.get("/devices")
def list_devices():
    return devices.list_devices()
