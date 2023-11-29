import os
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from tools.path import accv2022_dataset_path, accv2022_broken_list_path

from simpleAICV.classification import backbones
from simpleAICV.classification import losses
from simpleAICV.classification.datasets.accv2022traindataset import ACCV2022TrainDataset
from simpleAICV.classification.common import Opencv2PIL, TorchRandomResizedCrop, TorchRandomHorizontalFlip, RandAugment, TorchResize, TorchCenterCrop, TorchMeanStdNormalize, RandomErasing, ClassificationCollater, MixupCutmixClassificationCollater, load_state_dict

import torch
import torchvision.transforms as transforms


class config:
    network = 'vit_large_patch16'
    num_classes = 5000
    input_image_size = 224
    scale = 256 / 224

    model = backbones.__dict__[network](**{
        'image_size': 224,
        'drop_path_prob': 0.1,
        'global_pool': True,
        'num_classes': num_classes,
    })

    # load pretrained model or not
    trained_model_path = '/root/code/SimpleAICV_pytorch_training_examples_on_ImageNet_COCO_ADE20K/pretrained_models/vit_mae_pretrain_on_accv2022_from_imagenet1k_pretrain/vit_large_patch16_224_mae_pretrain_model-loss0.424_encoder.pth'
    load_state_dict(trained_model_path,
                    model,
                    loading_new_input_size_position_encoding_weight=True)

    train_criterion = losses.__dict__['OneHotLabelCELoss']()
    test_criterion = losses.__dict__['CELoss']()

    train_dataset = ACCV2022TrainDataset(
        root_dir=accv2022_dataset_path,
        set_name='train',
        transform=transforms.Compose([
            Opencv2PIL(),
            TorchRandomResizedCrop(resize=input_image_size),
            TorchRandomHorizontalFlip(prob=0.5),
            RandAugment(magnitude=9,
                        num_layers=2,
                        resize=input_image_size,
                        mean=[0.485, 0.456, 0.406],
                        integer=True,
                        weight_idx=None,
                        magnitude_std=0.5,
                        magnitude_max=None),
            TorchMeanStdNormalize(mean=[0.485, 0.456, 0.406],
                                  std=[0.229, 0.224, 0.225]),
            RandomErasing(prob=0.25, mode='pixel', max_count=1),
        ]),
        broken_list_path=accv2022_broken_list_path)

    test_dataset = ACCV2022TrainDataset(
        root_dir=accv2022_dataset_path,
        set_name='train',
        transform=transforms.Compose([
            Opencv2PIL(),
            TorchResize(resize=input_image_size * scale),
            TorchCenterCrop(resize=input_image_size),
            TorchMeanStdNormalize(mean=[0.485, 0.456, 0.406],
                                  std=[0.229, 0.224, 0.225]),
        ]),
        broken_list_path=accv2022_broken_list_path)

    train_collater = MixupCutmixClassificationCollater(
        use_mixup=True,
        mixup_alpha=0.8,
        cutmix_alpha=1.0,
        cutmix_minmax=None,
        mixup_cutmix_prob=1.0,
        switch_to_cutmix_prob=0.5,
        mode='batch',
        correct_lam=True,
        label_smoothing=0.1,
        num_classes=5000)
    test_collater = ClassificationCollater()

    seed = 0
    # batch_size is total size
    batch_size = 128
    # num_workers is total workers
    num_workers = 20
    accumulation_steps = 32

    optimizer = (
        'Lion',
        {
            'lr':
            4e-4,
            'global_weight_decay':
            False,
            # if global_weight_decay = False
            # all bias, bn and other 1d params weight set to 0 weight decay
            'weight_decay':
            5e-2,
            # lr_layer_decay only support vit style model
            'lr_layer_decay':
            0.65,
            'lr_layer_decay_block':
            model.blocks,
            'block_name':
            'blocks',
            'no_weight_decay_layer_name_list': [
                'position_encoding',
                'cls_token',
            ],
        },
    )

    scheduler = (
        'CosineLR',
        {
            'warm_up_epochs': 5,
            'min_lr': 1e-6,
        },
    )

    epochs = 100
    print_interval = 10

    sync_bn = False
    use_amp = True
    use_compile = False
    compile_params = {
        # 'default': optimizes for large models, low compile-time and no extra memory usage.
        # 'reduce-overhead': optimizes to reduce the framework overhead and uses some extra memory, helps speed up small models, model update may not correct.
        # 'max-autotune': optimizes to produce the fastest model, but takes a very long time to compile and may failed.
        'mode': 'default',
    }

    use_ema_model = False
    ema_model_decay = 0.9999
