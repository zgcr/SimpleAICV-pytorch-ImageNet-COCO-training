import os
import sys
import warnings

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(FILE_DIR)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
warnings.filterwarnings('ignore')

import cv2
import gradio as gr
import random
import numpy as np
from PIL import Image

import torch

from simpleAICV.instance_segmentation import models
from simpleAICV.instance_segmentation import decode
from simpleAICV.instance_segmentation.common import load_state_dict

from simpleAICV.instance_segmentation.datasets.cocodataset import COCO_CLASSES, COCO_CLASSES_COLOR

seed = 0
model_name = 'convformerm36_solov2'
decoder_name = 'SOLOV2Decoder'
# coco class
model_num_classes = 80
classes_name = COCO_CLASSES
classes_color = COCO_CLASSES_COLOR

trained_model_path = '/root/autodl-tmp/pretrained_models/solov2_train_on_coco/convformerm36_solov2_yoloresize1024-metric40.296.pth'
input_image_size = 1024
# 'retina_style', 'yolo_style'
image_resize_type = 'yolo_style'
keep_score_threshold = 0.3
mask_area_threshold = 100

os.environ['PYTHONHASHSEED'] = str(seed)
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

# assert model_name in models.__dict__.keys(), 'Unsupported model!'
model = models.__dict__[model_name](**{
    'num_classes': model_num_classes,
})
if trained_model_path:
    load_state_dict(trained_model_path, model)
else:
    print('No pretrained model load!')
model.eval()

assert decoder_name in decode.__dict__.keys(), 'Unsupported decoder!'
decoder = decode.__dict__[decoder_name](
    **{
        'keep_score_threshold': keep_score_threshold,
    })


def preprocess_image(image, resize, resize_type):
    assert resize_type in ['retina_style', 'yolo_style']

    # PIL image(RGB) to opencv image(RGB)
    image = np.asarray(image).astype(np.float32)

    origin_image = image.copy()
    h, w, _ = origin_image.shape

    origin_size = [h, w]

    if resize_type == 'retina_style':
        ratio = 1333. / 800
        scales = (resize, int(round(resize * ratio)))

        max_long_edge, max_short_edge = max(scales), min(scales)
        factor = min(max_long_edge / max(h, w), max_short_edge / min(h, w))
    else:
        factor = resize / max(h, w)

    resize_h, resize_w = int(round(h * factor)), int(round(w * factor))
    image = cv2.resize(image, (resize_w, resize_h))

    pad_w = 0 if resize_w % 32 == 0 else 32 - resize_w % 32
    pad_h = 0 if resize_h % 32 == 0 else 32 - resize_h % 32

    padded_img = np.zeros((resize_h + pad_h, resize_w + pad_w, 3),
                          dtype=np.float32)
    padded_img[:resize_h, :resize_w, :] = image
    scale = factor

    # normalize
    padded_img = padded_img.astype(np.float32) / 255.

    scaled_size = [resize_h, resize_w]

    return origin_image, padded_img, scale, scaled_size, origin_size


def predict(image):
    origin_image, resized_img, scale, scaled_size, origin_size = preprocess_image(
        image, input_image_size, image_resize_type)
    resized_img = torch.tensor(resized_img).permute(2, 0, 1).unsqueeze(0)
    scaled_size = [scaled_size]
    origin_size = [origin_size]

    with torch.no_grad():
        outputs = model(resized_img)

    batch_masks, batch_labels, batch_scores = decoder(outputs, scaled_size,
                                                      origin_size)
    one_image_masks, one_image_labels, one_image_scores = batch_masks[
        0], batch_labels[0], batch_scores[0]

    origin_image = cv2.cvtColor(origin_image, cv2.COLOR_RGB2BGR)
    origin_image = origin_image.astype('uint8')

    print('1111', one_image_masks.shape, one_image_labels.shape,
          one_image_scores.shape, origin_image.shape)

    masks_num = one_image_masks.shape[0]

    masks_class_color = []
    for _ in range(masks_num):
        masks_class_color.append(list(np.random.choice(range(256), size=3)))

    print("1212", masks_num, len(masks_class_color), masks_class_color[0])

    per_image_mask = np.zeros(
        (origin_image.shape[0], origin_image.shape[1], 3))
    per_image_contours = []
    for i in range(masks_num):
        per_mask = one_image_masks[i, :, :]
        per_mask_score = one_image_scores[i]

        if np.sum(per_mask) < mask_area_threshold:
            continue

        per_mask_color = np.array(
            (masks_class_color[i][0], masks_class_color[i][1],
             masks_class_color[i][2]))

        per_object_mask = np.nonzero(per_mask == 1.)
        per_image_mask[per_object_mask[0], per_object_mask[1]] = per_mask_color

        # get contours
        new_per_image_mask = np.zeros(
            (origin_image.shape[0], origin_image.shape[1]))
        new_per_image_mask[per_object_mask[0], per_object_mask[1]] = 255
        contours, _ = cv2.findContours(new_per_image_mask.astype('uint8'),
                                       cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        per_image_contours.append(contours)

    per_image_mask = per_image_mask.astype('uint8')
    per_image_mask = cv2.cvtColor(per_image_mask, cv2.COLOR_RGBA2BGR)

    all_object_mask = np.nonzero(per_image_mask != 0)
    per_image_mask[all_object_mask[0], all_object_mask[1]] = cv2.addWeighted(
        origin_image[all_object_mask[0], all_object_mask[1]], 0.5,
        per_image_mask[all_object_mask[0], all_object_mask[1]], 1, 0)
    no_class_mask = np.nonzero(per_image_mask == 0)
    per_image_mask[no_class_mask[0],
                   no_class_mask[1]] = origin_image[no_class_mask[0],
                                                    no_class_mask[1]]
    for contours in per_image_contours:
        cv2.drawContours(per_image_mask, contours, -1, (255, 255, 255), 1)

    per_image_mask = cv2.cvtColor(per_image_mask, cv2.COLOR_BGR2RGB)
    per_image_mask = Image.fromarray(np.uint8(per_image_mask))

    return per_image_mask


title = '实例分割'
description = '选择一张图片进行实例分割吧！'
inputs = gr.Image(type='pil')
outputs = gr.Image(type='pil')
gradio_demo = gr.Interface(fn=predict,
                           title=title,
                           description=description,
                           inputs=inputs,
                           outputs=outputs,
                           examples=[
                               'test_coco_images/000000001551.jpg',
                               'test_coco_images/000000010869.jpg',
                               'test_coco_images/000000011379.jpg',
                               'test_coco_images/000000015108.jpg',
                               'test_coco_images/000000016656.jpg',
                           ])
# local website: http://127.0.0.1:6006/
gradio_demo.launch(share=True,
                   server_name='0.0.0.0',
                   server_port=6006,
                   show_error=True)
