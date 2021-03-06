from paddleocr import PaddleOCR,draw_ocr
import os

BASE_PPOCR_UTILS_PATH = './ppocr/utils/'
BASE_MODEL_PATH = './models/'
BASE_INFERENCE_PATH = './inference/'

os.environ["CUDA_VIIBLE_DEVICES"] = "1"

cls_model_dir=str(BASE_MODEL_PATH + "cls/ch_ppocr_mobile_v2.0_cls_infer")
det_model_dir=str(BASE_INFERENCE_PATH + "ch_ppocr_mobile_v2.0_det_infer")
rec_model_dir=str(BASE_INFERENCE_PATH + "rec_en_number_lite/inference")

e2e_char_dict_path=str(BASE_PPOCR_UTILS_PATH + "ic15_dict.txt")
rec_char_dict_path=str(BASE_PPOCR_UTILS_PATH + "dict/vi_dict.txt")

ocr = PaddleOCR(cls_model_dir=cls_model_dir, det_model_dir=det_model_dir, rec_model_dir=rec_model_dir, \
                e2e_char_dict_path=e2e_char_dict_path, rec_char_dict_path=rec_char_dict_path,\
                 use_angle_cls=True, lang='vi', warmup=True) # need to run only once to download and load model into memory
# img_path = '../dataset/corner_dataset/images/train/crawl_00081_0.jpg'
img_path = '../dataset/corner_dataset/images/test/stage0_00118.jpg'
result = ocr.ocr(img_path, cls=True)
for line in result:
    # print('or this shit')
    print(line)

# draw result
from PIL import Image
image = Image.open(img_path).convert('RGB')
boxes = [line[0] for line in result]
txts = [line[1][0] for line in result]
scores = [line[1][1] for line in result]
im_show = draw_ocr(image, boxes, txts, scores, font_path='../paddle-ocr/fonts/en_standard.ttf')
im_show = Image.fromarray(im_show)
im_show.save('result.jpg')