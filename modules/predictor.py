import numpy as np
from PIL import Image
import time
import yaml
import os
import paddle
import cv2
import shutil

from .yolov5 import Yolo
from .vietocr import VietOCR
from .PaddleOCR.OCRSystem import OCRSystem
from .PICK.PICKSystem import PICKSystem
import modules.utils.preprocess as preprocess
import modules.utils.custom_plots as custom_plots
from modules.Key_information_extraction import KIE
from modules.PaddleOCR.ppocr.data import create_operators, transform

class Predictor:
    def __init__(self, config):
        self.config = config
        self.vietocr = VietOCR(config['VietOCR'])
        self.yolo = Yolo(config['Yolo'])
        self.ocr = OCRSystem(config)
        self.paddle_det = self.ocr.model_det
        self.paddle_rec = self.ocr.model_rec
        self.pick = PICKSystem()
        self.kie = KIE(config['key_information_extraction'])

        self.detect_algorithm = 'paddle'
        self.rec_algorithm = 'vietocr'
        self.text_line_detection = self.yolo
        self.text_line_recognition = self.vietocr

    def write_output_vietocr(self, rec_det_res, file_name):
        if not os.path.exists('result_trans'):
            os.mkdir('result_trans')
        result = ''
        for res in rec_det_res:
            bbox, value = res
            des = value
            s = [str(1)]
            for i, box in enumerate(bbox):
                xx, yy = box
                s.append(str(xx))
                s.append(str(yy))
            line = ','.join(s) + ',' + des
            result += line + '\n'
        result = result.rstrip('\n')
        result_file_path = 'result_trans/{}.tsv'.format(file_name.split('.')[0])
        with open(result_file_path, 'w', encoding='utf8') as res:
            res.write(result)

    def __call__(self, img_list):
	# Preprocessing: Corner Detection and Stretch
        if os.path.exists('./result_trans'):
            shutil.rmtree('./result_trans')
        if os.path.exists('./ori_im'):
            shutil.rmtree('./ori_im')
        if os.path.exists('./result_json'):
            shutil.rmtree('./result_json')
        os.mkdir('./ori_im')
        image = cv2.imread(img_list[0])
        cv2.imwrite('./ori_im/result.jpg', image)
        start_text_line_detection = time.time()
        if self.detect_algorithm == 'paddle':
            text_line_bboxes, img_list, image, dt_boxes = self.ocr.predict_det(img_list)
        else:
            text_line_bboxes = self.text_line_detection(img_list)
        end_text_line_detection = time.time()
        text_line_images = []
        if self.detect_algorithm == 'paddle':
            new_text_line = []
            for box in text_line_bboxes:
                tmp = []
                tmp.append(box[0][0])
                tmp.append(box[0][1])
                tmp.append(box[2][0])
                tmp.append(box[2][1])
                new_text_line.append(tmp)

        tlbrs = []
        for idx, text_line_bbox in enumerate(text_line_bboxes):
            if self.detect_algorithm != 'paddle':
                tlbr = preprocess.xyxy2tlbr(text_line_bbox[:4])
                tlbrs.append(np.array(tlbr))
            else:
                tlbr = text_line_bbox
            text_line_image = preprocess.four_point_transform(image, tlbr)
            text_line_images.append(text_line_image)

        if self.detect_algorithm != 'paddle':
            img_list = []
            for box in tlbrs:
                this_img = self.ocr.getImgFromBbox(image, box)
                img_list.append(this_img)
        text_line_texts = []

        start_text_line_recognition = time.time()
        if self.detect_algorithm == 'paddle' and self.rec_algorithm == 'paddle':
            text_line_text = self.ocr.predict_rec(img_list, dt_boxes)
            text_line_texts = [i[0] for i in text_line_text]
        elif self.detect_algorithm != 'paddle' and self.rec_algorithm == 'paddle':
            text_line_text = self.ocr.predict_rec(img_list, tlbrs)
            text_line_texts = [i[0] for i in text_line_text]
        else:
            text_line_texts = self.vietocr.predict_batch(text_line_images)
            boxes = tlbrs if self.detect_algorithm != 'paddle' else dt_boxes
            #write_result for the next step
            final_res = [[box.tolist(), res] for box, res in zip(boxes, text_line_texts)]
            self.write_output_vietocr(final_res, 'result.jpg')

        end_text_line_recognition = time.time()

        if self.detect_algorithm == 'paddle':
            draw_image = custom_plots.display(image, new_text_line, text_line_texts)
        else:
            draw_image = custom_plots.display(image, text_line_bboxes, text_line_texts)

        #PICK
        start_pick = time.time()
        # self.pick('ori_im', 'result_trans')
        if self.detect_algorithm == 'paddle':
            kie_result = self.kie.predict(image, new_text_line, text_line_texts)
        else:
            kie_result = self.kie.predict(image, text_line_bboxes, text_line_texts)
        stop_pick = time.time()
        print('text_line_detection time: ', end_text_line_detection - start_text_line_detection)
        print('text_line_recognition time: ', end_text_line_recognition - start_text_line_recognition)
        print('pick time: ', stop_pick - start_pick)
        return draw_image, kie_result