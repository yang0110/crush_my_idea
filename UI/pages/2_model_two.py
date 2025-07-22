import streamlit as st

st.set_page_config(
    page_title="Analysis",
    page_icon="🔬",
)

st.title("Data Analysis 🔬")
st.write("This page is for performing detailed data analysis.")

st.markdown(
    """
    You can put your analytical scripts, model outputs,
    and more complex visualizations here.
    """
)

text_input = st.text_area("Enter your analysis notes here:")
if text_input:
    st.write("Your notes:")
    st.code(text_input)