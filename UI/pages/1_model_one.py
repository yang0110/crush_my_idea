import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="VLM: Qwen 2.5 VL",
    page_icon="📈",
)

st.title("Dashboard 📈")
st.write("This page yesy Qwen2.5 VL Model.")

# Create some dummy data
chart_data = pd.DataFrame(
    np.random.randn(20, 3),
    columns=['a', 'b', 'c']
)

zip_folder = st.file_uploader('Pleae Upload You GroundTruth Label')
cols = st.columns(3)
for index, col in enumerate(cols):
    with col:
        checkbox = st.checkbox(f'select metric {index}')
button = st.button('Get evaluation Metric')
output = st.write('Evaluation Results')

# st.line_chart(chart_data)
# st.subheader("Interactive elements:")
# col1, col2 = st.columns(2)
# with col1:
#     slider_val = st.slider("Select a value", 0, 100, 50)
#     st.write(f"You selected: {slider_val}")
# with col2:
#     checkbox_val = st.checkbox("Show details")
#     if checkbox_val:
#         st.info("Here are some details about the data.")