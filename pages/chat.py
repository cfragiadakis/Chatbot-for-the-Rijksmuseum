import streamlit as st
from app import get_base64


st.set_page_config(layout="wide")

st.title("Ask About the Painting")

# Back button
if st.button("← Back to Home"):
    st.switch_page("app.py")

st.write("---")

# Predefined questions + answers
presets = {
    "Who painted this artwork?": "Johannes Vermeer painted the Milkmaid.",
    "When was it created?": "It was created around 1657–1658.",
    "What is happening in the scene?": "A maid pours milk into a bowl, symbolizing domestic virtue.",
    "Why is this painting famous?": "It is known for its realism, light, and detailed textures.",
    "What materials were used?": "Oil paint on canvas.",
    "What symbolism does it contain?": "The bread and milk symbolize nourishment and humility."
}

st.subheader("Suggested Questions")

cols = st.columns(3)
i = 0
for question, answer in presets.items():
    with cols[i % 3]:
        if st.button(question):
            st.session_state["answer"] = answer
    i += 1

st.write("---")

# Text input
user_query = st.text_input("Ask anything:")

if user_query:
    st.session_state["answer"] = "This is a static demo. No real generation yet."

# Output box
if "answer" in st.session_state:
    st.chat_message("assistant").write(st.session_state["answer"])
