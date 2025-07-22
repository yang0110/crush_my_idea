import streamlit as st

st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
)

st.title("Settings ⚙️")
st.write("Adjust application settings here.")

option = st.selectbox(
    "Choose a theme:",
    ("Light", "Dark", "System Default")
)
st.write(f"Current theme: {option}")

password = st.text_input("Enter password (for demo, not secure):", type="password")
if password == "streamlit":
    st.success("Access granted!")
else:
    st.warning("Incorrect password.")