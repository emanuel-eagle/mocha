import yaml
import streamlit as st
from utilities.SmartDevice import SmartDevice
from utilities.FuzzyMatching import FuzzyMatching
from utilities.OllamaChat import OllamaChat

with open("config.yaml") as f:
    config = yaml.safe_load(f)

@st.cache_resource
def init_services():
    devices = SmartDevice()
    fuzzy_matching = FuzzyMatching()
    available_devices = devices.list_devices()
    fuzzy_matching.set_threshold(config["FUZZY_MATCH_THRESHOLD"])
    fuzzy_matching.set_items(available_devices)
    return OllamaChat(devices, fuzzy_matching, model=config["MODEL"])

ollama_chat = init_services()

st.title(config["TITLE"])
st.caption(config["CAPTION"])

if "messages" not in st.session_state:
    greeting = ollama_chat.greet()
    st.session_state.messages = [{"role": "assistant", "content": greeting}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("e.g. Turn off the bedroom lights"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()

        def on_status(text):
            status_placeholder.markdown(f"*{text}*")

        response = ollama_chat.chat(prompt, on_status=on_status)
        status_placeholder.empty()
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
