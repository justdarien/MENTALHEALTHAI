import streamlit as st
import google.generativeai as genai
from datetime import datetime
import google.api_core.exceptions # For more specific error handling
import pandas as pd

# --- Configuration ---
PAGE_TITLE = "Mental Health Support Chatbot"
MODEL_NAME = "gemini-2.5-pro-exp-03-25" # Using the experimental model
HARDCODED_API_KEY = "AIzaSyA8gkngQrxQMiQqzqqDoo5mKArwcMBpqp8" # <--- PASTE YOUR ACTUAL API KEY HERE

# Basic keywords for distress detection (CASE-INSENSITIVE)
CRISIS_KEYWORDS = [
    "kill myself", "suicide", "want to die", "self harm",
    "can't go on", "end my life", "no reason to live", "hopeless"
]

# --- Guided Exercise Texts ---
BREATHING_EXERCISE_TEXT = """
**Simple Breathing Exercise (4-4-6 Count)**

1.  **Find a comfortable position:** Sit upright or lie down comfortably. Relax your shoulders.
2.  **Breathe in slowly:** Inhale gently and deeply through your nose for a count of 4. Feel your belly expand.
3.  **Hold gently:** Hold your breath softly for a count of 4. Don't strain.
4.  **Breathe out slowly:** Exhale smoothly and completely through your mouth for a count of 6. Let the breath release gently.
5.  **Repeat:** Continue this cycle for 1-3 minutes, focusing on the rhythm of your breath.
"""

GROUNDING_EXERCISE_TEXT = """
**5 Senses Grounding Technique**

This helps bring you back to the present moment. Gently notice and name:

1.  **5 Things You Can See:** Look around and name five objects. Notice colours, shapes, details. (e.g., "I see my blue pen, the green plant...")
2.  **4 Things You Can Touch/Feel:** Notice four sensations. (e.g., "I feel the smooth desk, my soft jumper, the cool air...")
3.  **3 Things You Can Hear:** Listen carefully and identify three sounds. (e.g., "I hear typing, birds outside, my own breathing...")
4.  **2 Things You Can Smell:** Notice two distinct smells. (e.g., "I smell coffee, the scent of rain...") If you can't smell anything, recall two favourite smells.
5.  **1 Thing You Can Taste:** Notice the taste in your mouth or sip some water and notice its taste. (e.g., "I taste mint from my toothpaste.")
"""

# --- Helper Functions ---

def configure_genai():
    """Configures the Google Generative AI library using a hardcoded API key."""
    if not HARDCODED_API_KEY or HARDCODED_API_KEY == "YOUR_API_KEY_HERE":
         st.error("API Key is missing or placeholder..."); st.stop(); return False
    try:
        genai.configure(api_key=HARDCODED_API_KEY)
        return True
    except google.api_core.exceptions.PermissionDenied:
         st.error("Error: Invalid API Key provided..."); st.stop(); return False
    except Exception as e:
        st.error(f"Failed to configure Generative AI: {e}"); st.stop(); return False

def initialize_chat_session():
    """Initializes the chat session, message history, and mood log."""
    if "chat_session" not in st.session_state:
        try:
            model = genai.GenerativeModel(MODEL_NAME)

            # 1. Define initial user prompt for API (NO timestamp, includes NEW topic awareness instruction)
            api_initial_user_prompt = {
                "role": "user",
                "parts": """
Ignore all previous instructions. You are Buddy, a friendly and empathetic AI assistant designed to provide supportive conversations related to mental well-being. Listen actively, show compassion, and offer encouragement. You cannot provide medical advice, diagnosis, or crisis intervention. If a user seems in distress or mentions self-harm or crisis, gently guide them towards professional help and provide the resources listed below. Never suggest actions that could be harmful. Keep responses thoughtful but concise.

**New Instruction:** Periodically, perhaps every 3-4 responses or when it feels natural, try to gently summarize the main topic being discussed or ask a clarifying question to show you are following the conversation's theme. For example: 'It sounds like we've been focusing on [topic], is that right?' or 'Just to recap, we were talking about [topic].' Do this subtly and naturally within the conversation flow.

Resources to suggest in crisis: National Suicide Prevention Lifeline (988 in US/Canada), Crisis Text Line (text HOME to 741741), or local emergency services (like 115 in Vietnam or 911/999 elsewhere). Check local resources if possible. Start the conversation by introducing yourself briefly and asking how the user is feeling.
"""
            }

            # 2. Define the model's first message separately (WITH timestamp for display)
            model_intro_message = {
                "role": "model",
                "parts": "Hi there! I'm Buddy, your supportive AI companion using an advanced experimental model. I'm here to listen and chat about how you're doing. How are you feeling today?",
                "timestamp": datetime.now()
            }

            # 3. Start the chat session
            st.session_state.chat_session = model.start_chat(history=[api_initial_user_prompt])

            # 4. Create the display message list
            display_messages = [model_intro_message] # Start display with model's intro

            # 5. Store display messages
            st.session_state.messages = display_messages
            st.session_state.mood_log = [] # Initialize mood log

        except Exception as e:
            st.error(f"Failed to initialize chat model: {e}"); st.stop()

def display_chat_history():
    """Displays the chat messages with timestamps stored in session state."""
    messages_to_display = st.session_state.get("messages", [])
    for message in messages_to_display:
        content = message.get('parts', '')
        role = message.get('role', 'user')
        ts = message.get('timestamp')
        display_role = "assistant" if role == "model" else role
        with st.chat_message(display_role):
             st.markdown(content)
             if ts: st.caption(ts.strftime("%Y-%m-%d %H:%M:%S"))

def show_distress_info(triggered_by_keyword=False):
     """Displays crisis resources."""
     if triggered_by_keyword:
         st.error("It sounds like you might be going through a very difficult time...", icon="🚨")
     st.warning(
         f"""**If you are in immediate distress or danger, please reach out for professional help.** *As of April 2025:* Vietnam (Hanoi): Call 111/113/115. USA/Canada: Call/text 988. USA Crisis Text: Text HOME to 741741. Other Regions: Search local hotlines/emergency services (999, 112). Remember, Buddy is an AI and cannot provide crisis support.""", icon="⚠️", )

def check_for_crisis_keywords(text):
    lower_text = text.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in lower_text: return True
    return False

def get_ai_response(prompt_text):
    """Sends prompt to AI and handles response/errors."""
    try:
        # Add context or instructions here if needed per-turn, e.g., regarding topic awareness
        # For now, relying on system prompt modification.
        response = st.session_state.chat_session.send_message(prompt_text)
        return response.text
    except google.api_core.exceptions.ResourceExhausted as quota_error:
         st.error(f"Quota Error (429) for '{MODEL_NAME}'. Limits may be low. {quota_error}")
    except Exception as e: st.error(f"Error getting response: {e}")
    return None

def display_mood_tracker():
    """Displays mood input and visualization."""
    st.sidebar.subheader("Mood Check-in")
    current_mood_logged = bool(st.session_state.get("mood_log"))
    mood_rating = st.sidebar.radio(
         "Overall mood? (1=Low, 5=High)", [1, 2, 3, 4, 5], index=2,
         horizontal=True, key="mood_radio", help="Log mood once per session.",
         disabled=current_mood_logged
    )
    if st.sidebar.button("Log Mood", key="log_mood_button", disabled=current_mood_logged):
         st.session_state.mood_log.append({"timestamp": datetime.now(), "rating": mood_rating})
         st.sidebar.success(f"Mood ({mood_rating}) logged!")
         st.rerun()

    if st.session_state.get("mood_log"):
        try:
            mood_data = pd.DataFrame(st.session_state.mood_log)
            if not mood_data.empty and 'timestamp' in mood_data.columns:
                mood_data.set_index('timestamp', inplace=True)
                st.sidebar.line_chart(mood_data['rating'])
        except Exception as chart_ex: st.sidebar.error(f"Chart error: {chart_ex}")

def display_guided_exercises():
    """Displays guided exercises in the sidebar using expanders."""
    st.sidebar.subheader("Guided Exercises")
    with st.sidebar.expander("Breathing Exercise"):
        st.markdown(BREATHING_EXERCISE_TEXT)
    with st.sidebar.expander("5 Senses Grounding"):
        st.markdown(GROUNDING_EXERCISE_TEXT)

# --- Main App Logic ---
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title("🤖 Mental Health Support Chatbot (Buddy - Experimental Model)")

if 'disclaimer_shown' not in st.session_state:
    st.info(
        """**Welcome!** I'm Buddy, an AI assistant. **Important:** I'm not a therapist and cannot provide diagnosis, medical advice, or crisis support. If you're in crisis, please use the 'Need immediate help' button or contact local services. Conversations are not permanently stored.""" , icon="👋" )
    st.session_state.disclaimer_shown = True

if configure_genai():
    initialize_chat_session() # Includes updated system prompt

    with st.sidebar:
        st.header("Controls & Tools")
        if st.button("⚠️ Need immediate help?", use_container_width=True): show_distress_info()
        if st.button("Clear Chat History", use_container_width=True):
            keys_to_reset = ["messages", "mood_log", "chat_session", "disclaimer_shown"]
            for key in keys_to_reset:
                 if key in st.session_state: del st.session_state[key]
            st.rerun()
        display_mood_tracker()
        display_guided_exercises() # Add exercises to sidebar

    st.subheader("Conversation")
    display_chat_history()

    if prompt := st.chat_input("How are you feeling today?"):
        timestamp = datetime.now()
        st.session_state.messages.append({"role": "user", "parts": prompt, "timestamp": timestamp})
        with st.chat_message("user"):
            st.markdown(prompt); st.caption(timestamp.strftime("%Y-%m-%d %H:%M:%S"))

        if check_for_crisis_keywords(prompt):
            show_distress_info(triggered_by_keyword=True)

        ai_response_text = None
        with st.spinner("Buddy (Experimental) is thinking..."):
            ai_response_text = get_ai_response(prompt)

        if ai_response_text:
            ai_timestamp = datetime.now()
            st.session_state.messages.append({"role": "model", "parts": ai_response_text, "timestamp": ai_timestamp})
            with st.chat_message("assistant"):
                st.markdown(ai_response_text); st.caption(ai_timestamp.strftime("%Y-%m-%d %H:%M:%S"))