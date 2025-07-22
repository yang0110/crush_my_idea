import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="VLLM Benchmark App",
    page_icon="🏠",
)

st.title("Welcome to the VLLM Benchmark App! 👋")
st.markdown(
    """
    ### What is this app about?
    This is a simple demo to show how to test VLM models on benchmarks in Streamlit.
    """
)
st.write("Navigate to VLM models using the sidebar on the left.")

# --- Dummy VLM Model Data ---
# In a real application, you might load this from a database, API, or config file
vlm_models = [
    {"Name": "CLIP (OpenAI)", "Type": "Text-Image Embedding", "Use Case": "Zero-shot image classification, image search", "Status": "Widely used"},
    {"Name": "ALIGN (Google)", "Type": "Text-Image Embedding", "Use Case": "Large-scale image-text pretraining", "Status": "Research"},
    {"Name": "BLIP (Salesforce)", "Type": "Image Captioning, VQA", "Use Case": "Generates image descriptions, answers questions about images", "Status": "Active Development"},
    {"Name": "BLIP-2 (Salesforce)", "Type": "Image Captioning, VQA, Chat", "Use Case": "Improved version of BLIP, more powerful", "Status": "Active Development"},
    {"Name": "Flamingo (DeepMind)", "Type": "Visual Question Answering (VQA)", "Use Case": "Few-shot VQA, visual dialogue", "Status": "Research"},
    {"Name": "LLaVA (Microsoft/UW)", "Type": "Visual Instruction Tuning", "Use Case": "General-purpose visual and language understanding, chatbots", "Status": "Open Source"},
    {"Name": "MiniGPT-4 (DAMO Academy)", "Type": "Multimodal Large Language Model", "Use Case": "Connects vision encoder to LLM for image understanding", "Status": "Open Source"},
    {"Name": "GPT-4o (OpenAI)", "Type": "Multimodal Large Language Model", "Use Case": "Generates text, images, audio, video from various inputs", "Status": "State-of-the-art (proprietary)"},
]

df_vlm = pd.DataFrame(vlm_models)

st.dataframe(df_vlm, use_container_width=True)
st.subheader('Model List')
divider = st.divider()

password = st.text_input("Enter UserNme (for demo, not secure):", type="password")
zip_folder = st.file_uploader('Pleae Upload You Data file in zip format')

