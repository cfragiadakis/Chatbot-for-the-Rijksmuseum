import streamlit as st
import base64

st.set_page_config(
    page_title="Rijksmuseum Artist Chat • Prototype",
    layout="wide"
)

# ------------ HELPER: CONVERT IMAGE TO BASE64 ------------
def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bg_image_path = "figs/milkmaid.png"
encoded_bg = get_base64(bg_image_path)

# ------------ APPLY BACKGROUND ------------
page_bg = f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: url("data:image/jpg;base64,{encoded_bg}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}

[data-testid="stHeader"] {{
    background: rgba(0,0,0,0);
    height: 0px;
}}

.chat-bubble {{
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 10px;
    max-width: 80%;
}}
.user-msg {{
    background-color: #DCF8C6;
    align-self: flex-end;
}}
.bot-msg {{
    background-color: #FFFFFF;
    border: 1px solid #ddd;
}}
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)



st.markdown(
    "<h1 style='color:white; text-shadow:0 0 10px black;'>Prototype phase</h1>",
    unsafe_allow_html=True
)

for i in range(32):
    st.write("")

col1, col2, col3 = st.columns([0.1, 0.65, 0.25])

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #cc4c28;
        color: white;
        padding: 0.6em 1.2em;

        transition: 0.2s;
        font-size: 4px;
    }

    div.stButton > button:hover {
        background-color: white;
        color: black;
    }
    </style>
    """, unsafe_allow_html=True)

with col3:
    if st.button("Start Chat"):
        st.switch_page("pages/chat.py")
