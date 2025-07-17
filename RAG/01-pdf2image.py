from pdf_manager import PDF2Image
import os

pdf_folder = '/home/ubuntu/workspace/medical_rag/pdfs'
pdf_path_list = [os.path.join(pdf_folder, pdf_path) for pdf_path in os.listdir(pdf_folder) if pdf_path.endswith('.pdf')]
print(f"Found {len(pdf_path_list)} PDF files in {pdf_folder}")

converter = PDF2Image(output_folder='./pages', max_pages=None)
for pdf_path in pdf_path_list:
    print(f"Processing PDF: {pdf_path}")
    image_paths, pdf_name, page_num_list = converter.save_pdf_pages_as_images(pdf_path)