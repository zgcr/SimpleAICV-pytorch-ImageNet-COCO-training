import os
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from tools.path import accv2022_dataset_path, accv2022_broken_list_path

from simpleAICV.masked_image_modeling import models
from simpleAICV.masked_image_modeling import losses
from simpleAICV.classification.datasets.accv2022traindataset import ACCV2022TrainDataset
from simpleAICV.classification.common import Opencv2PIL, TorchRandomResizedCrop, TorchRandomHorizontalFlip, TorchMeanStdNormalize, load_state_dict
from simpleAICV.masked_image_modeling.common import MAESelfSupervisedPretrainCollater

import torch
import torchvision.transforms as transforms


class config:
    network = 'vit_large_patch16_224_mae_pretrain_model'
    input_image_size = 224
    scale = 256 / 224

    model = models.__dict__[network](**{})

    # load pretrained model or not
    trained_model_path = '/root/code/SimpleAICV_pytorch_training_examples_on_ImageNet_COCO_ADE20K/pretrained_models/vit_mae_pretrain_on_imagenet1k/vit_large_patch16_224_mae_pretrain_model-loss0.378.pth'
    load_state_dict(trained_model_path, model)

    train_criterion = losses.__dict__['MSELoss']()

    train_dataset = ACCV2022TrainDataset(
        root_dir=accv2022_dataset_path,
        set_name='train',
        transform=transforms.Compose([
            Opencv2PIL(),
            TorchRandomResizedCrop(resize=input_image_size, scale=(0.2, 1.0)),
            TorchRandomHorizontalFlip(prob=0.5),
            TorchMeanStdNormalize(mean=[0.485, 0.456, 0.406],
                                  std=[0.229, 0.224, 0.225]),
        ]),
        broken_list_path=accv2022_broken_list_path)

    train_collater = MAESelfSupervisedPretrainCollater(
        image_size=input_image_size, patch_size=16, norm_label=True)

    seed = 0
    # batch_size is total size
    batch_size = 128
    # num_workers is total workers
    num_workers = 30
    accumulation_steps = 2

    optimizer = (
        'AdamW',
        {   # lr = base_lr:1.5e-4 * batch_size * accumulation_steps / 256
            'lr': 1.5e-4,
            'global_weight_decay': False,
            # if global_weight_decay = False
            # all bias, bn and other 1d params weight set to 0 weight decay
            'weight_decay': 5e-2,
            'no_weight_decay_layer_name_list': [],
            'beta1': 0.9,
            'beta2': 0.95,
        },
    )

    scheduler = (
        'CosineLR',
        {
            'warm_up_epochs': 10,
            'min_lr': 1e-6,
        },
    )

    epochs = 100
    print_interval = 100

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
