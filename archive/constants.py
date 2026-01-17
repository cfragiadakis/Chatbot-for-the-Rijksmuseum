chat_style = """
    <style>
    /* Page background / default text */
    .stApp {
        background-color: rgb(49, 51, 63);
        color: #e0e0e0;
    }

    /* Less aggressive global rule: avoid selecting ALL divs */
    h1, h2, h3, h4, h5, h6, p, span {
        color: #e0e0e0;
    }

    /* Text input */
    div.stTextInput > div > input {
        color: #e0e0e0;
        background-color: black;
    }
    div.stTextInput > div > input::placeholder {
        color: #b0b0b0;
    }

    /* Chat messages */
    .stChatMessage .messageContent {
        color: #f0f0f0;
    }

    /* ---------- FORCE BUTTON TEXT TO BLACK (robust) ---------- */
    /* Target Streamlit button wrapper + many nested possibilities and children */
    .stButton > button,
    .stButton button,
    button[data-testid="stButton"],
    .stButton > button span,
    .stButton > button div,
    .stButton > button * {
        color: #000000 !important;
        /* If you also want bold/different weight:
           font-weight: 600 !important;
        */
    }

    /* If your app uses columns (Streamlit can add extra wrappers) */
    div.stButton > button, div.stButton button, div.stButton > button * {
        color: #000000 !important;
    }
    </style>"""


buttons_style = """
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
    </style>"""
