import os
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from tools.path import face_detection_dataset_path

from simpleAICV.face_detection import models
from simpleAICV.face_detection import losses
from simpleAICV.face_detection import decode
from simpleAICV.face_detection.datasets.face_detection_dataset import FaceDetectionDataset
from simpleAICV.face_detection.common import YoloStyleResize, MainDirectionRandomRotate, RandomGaussianBlur, RandomCrop, RandomTranslate, RandomHorizontalFlip, RandomVerticalFlip, Normalize, FaceDetectionCollater, load_state_dict

import torch
import torchvision.transforms as transforms


class config:
    network = 'resnet50_retinaface'
    num_classes = 1
    input_image_size = [960, 960]

    # load backbone pretrained model or not
    backbone_pretrained_path = '/root/code/SimpleAICV_pytorch_training_examples_on_ImageNet_COCO_ADE20K/pretrained_models/resnet_train_from_scratch_on_imagenet1k/resnet50-acc76.300.pth'
    model = models.__dict__[network](**{
        'backbone_pretrained_path': backbone_pretrained_path,
        'anchor_num': 3,
    })

    # load total pretrained model or not
    trained_model_path = ''
    load_state_dict(trained_model_path, model)

    train_criterion = losses.__dict__['RetinaFaceLoss'](
        **{
            'anchor_sizes': [[8, 16, 32], [32, 64, 128], [128, 256, 512]],
            'strides': [8, 16, 32],
            'alpha': 0.25,
            'gamma': 2,
            'beta': 1.0 / 9.0,
            'focal_eiou_gamma': 0.5,
            'cls_loss_weight': 1.,
            'box_loss_weight': 1.,
            'box_loss_type': 'SmoothL1',
        })
    val_criterion = losses.__dict__['RetinaFaceLoss'](
        **{
            'anchor_sizes': [[8, 16, 32], [32, 64, 128], [128, 256, 512]],
            'strides': [8, 16, 32],
            'alpha': 0.25,
            'gamma': 2,
            'beta': 1.0 / 9.0,
            'focal_eiou_gamma': 0.5,
            'cls_loss_weight': 1.,
            'box_loss_weight': 1.,
            'box_loss_type': 'SmoothL1',
        })
    decoder = decode.__dict__['RetinaFaceDecoder'](
        **{
            'anchor_sizes': [[8, 16, 32], [32, 64, 128], [128, 256, 512]],
            'strides': [8, 16, 32],
            'max_object_num': 200,
            'min_score_threshold': 0.3,
            'topn': 1000,
            'nms_type': 'python_nms',
            'nms_threshold': 0.3,
        })

    train_dataset = FaceDetectionDataset(
        face_detection_dataset_path,
        set_name_list=[
            'wider_face',
            'UFDD',
        ],
        set_type='train',
        transform=transforms.Compose([
            RandomGaussianBlur(sigma=[0.5, 1.5], prob=0.3),
            MainDirectionRandomRotate(angle=[0, 90, 180, 270],
                                      prob=[0.55, 0.15, 0.15, 0.15]),
            RandomHorizontalFlip(prob=0.5),
            RandomVerticalFlip(prob=0.5),
            RandomCrop(prob=0.5),
            RandomTranslate(prob=0.5),
            YoloStyleResize(resize=input_image_size[0],
                            divisor=32,
                            stride=32,
                            multi_scale=True,
                            multi_scale_range=[0.8, 1.0]),
            Normalize(),
        ]))

    # 完整数据集必须在list中第0个位置
    val_dataset_name_list = [
        [
            'wider_face',
        ],
    ]

    val_dataset_list = []
    for per_sub_dataset_list in val_dataset_name_list:
        per_sub_val_dataset = FaceDetectionDataset(
            face_detection_dataset_path,
            set_name_list=per_sub_dataset_list,
            set_type='val',
            transform=transforms.Compose([
                YoloStyleResize(resize=input_image_size[0],
                                divisor=32,
                                stride=32,
                                multi_scale=False,
                                multi_scale_range=[0.8, 1.0]),
                Normalize(),
            ]))
        val_dataset_list.append(per_sub_val_dataset)

    train_collater = FaceDetectionCollater(resize=input_image_size[0])
    val_collater = FaceDetectionCollater(resize=input_image_size[0])

    seed = 0
    # batch_size is total size
    batch_size = 16
    # num_workers is total workers
    num_workers = 8
    accumulation_steps = 1

    optimizer = (
        'AdamW',
        {
            'lr': 1e-4,
            'global_weight_decay': False,
            # if global_weight_decay = False
            # all bias, bn and other 1d params weight set to 0 weight decay
            'weight_decay': 0,
            'no_weight_decay_layer_name_list': [],
        },
    )

    scheduler = (
        'MultiStepLR',
        {
            'warm_up_epochs': 0,
            'gamma': 0.1,
            'milestones': [200],
        },
    )

    epochs = 100
    print_interval = 50
    save_interval = 50

    eval_type = 'VOC'
    eval_epoch = [50, 100]
    eval_voc_iou_threshold_list = [
        0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95
    ]
    save_model_metric = 'IoU=0.50,area=all,maxDets=100,mAP'

    sync_bn = False
    use_amp = False
    use_compile = False
    compile_params = {
        # 'default': optimizes for large models, low compile-time and no extra memory usage.
        # 'reduce-overhead': optimizes to reduce the framework overhead and uses some extra memory, helps speed up small models, model update may not correct.
        # 'max-autotune': optimizes to produce the fastest model, but takes a very long time to compile and may failed.
        'mode': 'default',
    }

    use_ema_model = False
    ema_model_decay = 0.9999
