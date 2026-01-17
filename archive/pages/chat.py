import streamlit as st
from constants import chat_style

st.set_page_config(layout="wide",
    page_title="The Milkmaid - Prototype",
    page_icon="figs/favicon.ico",
)
st.markdown(
    chat_style,
    unsafe_allow_html=True
)

st.header("Chat about the milkmaid")

# Initialize chat history
if "messages" not in st.session_state or st.session_state.get("reset_chat", False):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello visitor, you are speaking with Johannes Vermeer. "
                "I am glad you are interested in my painting 'The Milkmaid', "
                "one of my favourite ones. What would you like to know about my artwork?"
            )
        }
    ]
    st.session_state.reset_chat = False  # reset the flag

# ---------------- Back Button ----------------
if st.button("<  Go back"):
    st.session_state.reset_chat = True  # mark chat for reset next visit
    st.switch_page("app.py")

st.write("---")

# ---------------- Display Chat Messages ----------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

st.write("---")

# ---------------- Predefined Questions ----------------
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
    key = f"preset_{i}"
    with cols[i % 3]:
        if st.button(question, key=key):
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()  # immediately update UI
    i += 1

# ---------------- Free Text Input ----------------
def handle_user_input():
    user_query = st.session_state.user_input
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.session_state.messages.append({
            "role": "assistant",
            "content": "This is a static demo. No real generation yet."
        })
        # Clear the input for the next message
        st.session_state.user_input = ""  # this is safe inside the callback

# The callback is triggered when user presses Enter
user_query = st.text_input(
    "Ask anything:",
    key="user_input",
    on_change=handle_user_input,
)

