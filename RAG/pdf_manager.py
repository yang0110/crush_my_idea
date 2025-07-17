import os
import shutil
import pymupdf
import json
from PIL import Image, ImageDraw

class PDF2Image:
    def __init__(self, output_folder='./pages', max_pages=None):
        self.output_folder = output_folder
        self.max_pages = max_pages

    def clear_and_recreate_dir(self):
        '''
        Not in used current, maybe used in production stage
        '''
        print(f"Clearing output folder {self.output_folder}")
        if os.path.exists(self.output_folder):
            shutil.rmtree(self.output_folder)
        os.makedirs(self.output_folder)
        
    def save_pdf_pages_as_images(self, pdf_path):
        self.pdf_path = pdf_path
        self.pdf_name = self.pdf_path.split('/')[-1].split('.')[0]
        print('--- pdf_name', self.pdf_name)
        os.makedirs(f'{self.output_folder}/{self.pdf_name}', exist_ok=True)
        self.doc = pymupdf.open(self.pdf_path)
        print('--- pdf_path', self.pdf_path)
        print('--- pdf_name', self.pdf_name)
        print('--- page_num', len(self.doc))
        print('--- doc', self.doc)

        # save the each page as image
        image_paths = []
        page_num_list = []
        for page_index, page in enumerate(self.doc):
            pix = page.get_pixmap()
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            save_page_path = f"{self.output_folder}/{self.pdf_name}/page_{page_index+1}.png"
            image.save(save_page_path)
            image_paths.append(save_page_path)
            page_num_list.append(str(page_index+1))  # page numbers are 1-indexed
            print('--- save page {}/{} as image in {}'.format(page_index, len(self.doc), save_page_path))
            if self.max_pages and page_index+1 >= self.max_pages:
                print('--- Reached max pages limit: {}. Stopping.'.format(self.max_pages))
                break
        print('--- All pages of pdf file {} are saved as images in {}'.format(self.pdf_path, self.output_folder+self.pdf_name))
        return image_paths, self.pdf_name, page_num_list



