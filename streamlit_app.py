import os
import json
import streamlit as st
from promptlayer import PromptLayer
from together import Together

PASSWORD = st.secrets["STREAMLIT_PASSWORD"]
PROMPTLAYER_API_KEY = st.secrets["PROMPTLAYER_API_KEY"]
pl_client = PromptLayer(api_key=PROMPTLAYER_API_KEY)
together = Together()


def authenticate(password):
    return password == PASSWORD


if "authenticated" not in st.session_state:
    password = st.text_input("Enter password:", type="password")
    if password and not authenticate(password):
        st.error("Invalid password. Access denied.")
        st.stop()
    st.success("Authenticated.")
    st.session_state.authenticated = True
    st.rerun()


# def load_fake_users():
#     with open(".data/product_managers.json", "r") as f:
#         users = json.load(f)["profiles"]
#     return {u["name"]: f"Imagine you are acting as a person... {json.dumps(u)}" for u in users}


# FAKE_USERS = load_fake_users()


def load_prompts():
    st.session_state.prompts = {
        "chat": {
            "side chat": pl_client.templates.get("side chat"),
            "main chat": pl_client.templates.get("main chat"),
            "side chat relaxed": pl_client.templates.get("side chat relaxed")
        },
        "insight": {
            "formulate insight from dialogue": pl_client.templates.get("formulate insight from dialogue")
        },
    }


def save_dialogue():
    filename = st.text_input("Enter filename", "chat_history.json")
    if st.button("Save Dialogue"):
        with open(filename, "w") as f:
            json.dump(st.session_state.messages, f, indent=4)
        st.success(f"Dialogue saved as {filename}")


if "prompts" not in st.session_state:
    load_prompts()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "first_question_asked" not in st.session_state:
    st.session_state.first_question_asked = False
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False


def chat_with_llm(messages, model, system_prompt):
    messages = [{"role": "system", "content": system_prompt}] + messages
    response = together.chat.completions.create(
        model=model, messages=messages, temperature=0.7, top_k=50, top_p=0.7, max_tokens=1500
    )
    return response.choices[0].message.content


def generate_insight():
    insight_prompt = st.session_state.prompts["insight"][st.session_state.selected_insight_prompt]["prompt_template"]["content"][0]["text"]
    insight_response = chat_with_llm(st.session_state.messages, st.session_state.insight_model, insight_prompt)
    st.chat_message("insight").markdown(insight_response)
    st.session_state.insight = insight_response


def handle_chat():
    if st.session_state.chat_started and not st.session_state.first_question_asked and st.session_state.selected_side_chat_prompt in ["side chat", "side chat relaxed"]:
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.selected_first_question})
        st.session_state.first_question_asked = True
    chat_input = st.chat_input("Ask a question")
    if chat_input:
        st.session_state.messages.append({"role": "user", "content": chat_input})
        response = chat_with_llm(st.session_state.messages, st.session_state.chat_model,
                                 st.session_state.prompts["chat"][st.session_state.selected_side_chat_prompt]["prompt_template"]["content"][0]["text"])
        st.session_state.messages.append({"role": "assistant", "content": response})
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])


def sidebar_controls():
    with st.sidebar:
        st.session_state.chat_model = st.selectbox("Chat Model", [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-V3",
        ])
        st.session_state.insight_model = st.selectbox("Insight Model", [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-V3",
        ])
        st.session_state.selected_side_chat_prompt = st.selectbox("Chat Prompt",
                                                                  st.session_state.prompts["chat"].keys())
        st.session_state.selected_insight_prompt = st.selectbox("Insight Prompt",
                                                                st.session_state.prompts["insight"].keys())
        first_questions = [
            "Tell me about your best day at work – not the most successful, but the one that felt most natural and energizing.",
            "When was the last time you were so absorbed in something you forgot to eat?"
        ]
        st.session_state.selected_first_question = st.selectbox("First Question", first_questions)
        if st.button("Start Chat"):
            st.session_state.chat_started = True
            st.session_state.messages = []  # Reset chat on start
            st.session_state.first_question_asked = False
        st.button("Generate Insight", on_click=generate_insight)
        save_dialogue()


def main():
    st.title("Chat with Ariadna")
    sidebar_controls()
    if st.session_state.chat_started:
        handle_chat()


if __name__ == "__main__":
    main()
