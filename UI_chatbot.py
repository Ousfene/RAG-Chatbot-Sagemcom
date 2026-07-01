import gradio as gr
from gradio.themes.base import Base
from chatbot import get_bot_answer, get_chatbot_backend
import os
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
import base64


backend = get_chatbot_backend()
# Example simple Gradio app


class SagemcomTheme(Base):
    def __init__(self):
        super().__init__(primary_hue="cyan", secondary_hue="blue", neutral_hue="gray")

BOT_AVATAR = "bot-de-discussion.png"
USER_AVATAR = "utilisateur.png"
LOGO_PATH = "logo-sagemcom-new-charte-header.png"
BACKGROUND_IMG = "shydzynr-f8j9du8HWdQ-unsplash.jpg"
CUSTOM_CSS = """


/* Keep inner containers transparent so the image is visible */
.gradio-container > * {
    background-color: transparent !important;
}

.header-container {
    background: white;
    padding: 0;
    margin-bottom: 0;
    box-shadow: none;
    border-bottom: none;
    text-align: center;
    margin-bottom: 10px !important;
}
.sagemcom-logo {
    font-size: 4rem;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(90deg, #00d1d5, #0080fe, #0097f2, #00c9d9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
    margin-top: 0;
}
.welcome-container {
    margin: 0 auto 10px auto !important;
    text-align: center;
    max-width: 800px;
}
.welcome-text {
    font-size: 1.2rem;
    font-weight: 600;
    color: #FFD700;
    text-align: center;
    margin: 0 0 5px 0 !important;
    padding: 0 !important;
}
.sources-box {
    background: #fefefe;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    font-size: 0.95rem;
    color: #0080fe;
    min-height: 60px;
}
.input-container {
    margin-top: 0;
    margin-bottom: 0;
}
#send-button {
    background: linear-gradient(135deg, #00d1d5, #0080fe);
    color: white;
    border: none;
    width: 42px !important;
    height: 42px !important;
    min-width: 42px !important;
    min-height: 42px !important;
    font-size: 18px;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 !important;
    line-height: 1 !important;
}
#send-button:hover {
    background: #FFD700;
    transform: scale(1.1);
}
.chatbot-container {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
"""

def chat_with_bot(message, history):
    if not message.strip():
        return "", history or [], ""

    history = history or []
    history.append({"role": "user", "content": message})

    try:
        cleaned_history = []
        user_msg = None
        for msg in history:
            if msg["role"] == "user":
                user_msg = msg["content"]
            elif msg["role"] == "assistant" and user_msg is not None:
                bot_msg = msg["content"]
                cleaned_history.append([user_msg, bot_msg])

        bot_message, sources_html = get_bot_answer(backend, message, cleaned_history)
        response = f"✨ {bot_message}"
        history.append({"role": "assistant", "content": response})

    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Erreur: {e}"})
        sources_html = ""

    return "", history, sources_html


with gr.Blocks(theme=SagemcomTheme(), css=CUSTOM_CSS, title="Sagemcom Chatbot") as iface:
    with gr.Column(scale=1):
        gr.Image(
            value=LOGO_PATH,
            show_label=False,
            height=120,
            scale=1,
            min_width=300,
            show_download_button=False,
            container=False
        )
        
        with gr.Column(elem_classes="chatbot-container"):
            gr.HTML('<div class="welcome-text">Bienvenue sur Sagemcom Qualité Chatbot</div>')
            
            chatbot = gr.Chatbot(
                type="messages",
                avatar_images=(USER_AVATAR, BOT_AVATAR),
                height=400,
                show_copy_button=True,
                label="Conversation"
            )
            with gr.Row(elem_classes="input-container"):
                user_input = gr.Textbox(
                    show_label=False,
                    placeholder="Saisissez votre question...",
                    container=False,
                    scale=8
                )
                send = gr.Button("➤", elem_id="send-button", scale=0)
            
            sources_box = gr.HTML('<div class="sources-box" id="sources-box"></div>')

    # Hook up actions
    user_input.submit(chat_with_bot, [user_input, chatbot], [user_input, chatbot, sources_box])
    send.click(chat_with_bot, [user_input, chatbot], [user_input, chatbot, sources_box])

if __name__ == "__main__":
    iface.launch(
        inbrowser=True,
        show_error=True,
        show_api=False
    )
