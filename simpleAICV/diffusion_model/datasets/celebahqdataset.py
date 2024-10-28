import os
import cv2
import numpy as np

from torch.utils.data import Dataset


class CelebAHQDataset(Dataset):
    '''
    https://github.com/tkarras/progressive_growing_of_gans
    '''

    def __init__(self, root_dir, set_name='train', transform=None):
        assert set_name in ['train', 'val'], 'Wrong set name!'
        set_dir = os.path.join(root_dir, set_name)

        sub_class_name_list = []
        for per_sub_class_name in os.listdir(set_dir):
            sub_class_name_list.append(per_sub_class_name)
        sub_class_name_list = sorted(sub_class_name_list)

        self.image_path_list = []
        for per_sub_class_name in sub_class_name_list:
            per_sub_class_dir = os.path.join(set_dir, per_sub_class_name)
            for per_image_name in os.listdir(per_sub_class_dir):
                per_image_path = os.path.join(per_sub_class_dir,
                                              per_image_name)
                self.image_path_list.append(per_image_path)
        self.image_path_list = sorted(self.image_path_list)

        self.class_name_to_label = {
            sub_class_name: i
            for i, sub_class_name in enumerate(sub_class_name_list)
        }

        self.label_to_class_name = {
            i: sub_class_name
            for i, sub_class_name in enumerate(sub_class_name_list)
        }

        self.transform = transform

        print(f'Dataset Size:{len(self.image_path_list)}')
        print(f'Dataset Class Num:{len(self.class_name_to_label)}')

    def __len__(self):
        return len(self.image_path_list)

    def __getitem__(self, idx):
        path = self.image_path_list[idx]

        image = self.load_image(idx)
        label = self.load_label(idx)

        sample = {
            'path': path,
            'image': image,
            'label': label,
        }

        if self.transform:
            sample = self.transform(sample)

        return sample

    def load_image(self, idx):
        image = cv2.imdecode(
            np.fromfile(self.image_path_list[idx], dtype=np.uint8),
            cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        return image.astype(np.float32)

    def load_label(self, idx):
        label = self.class_name_to_label[self.image_path_list[idx].split('/')
                                         [-2]]
        label = np.array(label)

        return label.astype(np.float32)


if __name__ == '__main__':
    import os
    import random
    import numpy as np
    import torch
    seed = 0
    # for hash
    os.environ['PYTHONHASHSEED'] = str(seed)
    # for python and numpy
    random.seed(seed)
    np.random.seed(seed)
    # for cpu gpu
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    import os
    import sys

    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.append(BASE_DIR)

    from tools.path import CelebAHQ_path

    import torchvision.transforms as transforms
    from tqdm import tqdm

    from simpleAICV.diffusion_model.common import Resize, RandomHorizontalFlip, Normalize, DiffusionWithLabelCollater

    celebahqtraindataset = CelebAHQDataset(
        root_dir=CelebAHQ_path,
        set_name='train',
        transform=transforms.Compose([
            Resize(resize=256),
            RandomHorizontalFlip(prob=0.5),
            #    Normalize(),
        ]))

    count = 0
    for per_sample in tqdm(celebahqtraindataset):
        print(per_sample['path'], per_sample['image'].shape,
              per_sample['label'].shape, per_sample['label'],
              type(per_sample['image']), type(per_sample['label']))

        # temp_dir = './temp1'
        # if not os.path.exists(temp_dir):
        #     os.makedirs(temp_dir)

        # color = [random.randint(0, 255) for _ in range(3)]
        # image = np.ascontiguousarray(per_sample['image'], dtype=np.uint8)
        # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        # label = per_sample['label']
        # text = f'label:{int(label)}'
        # cv2.putText(image,
        #             text, (30, 30),
        #             cv2.FONT_HERSHEY_PLAIN,
        #             1.5,
        #             color=color,
        #             thickness=1)

        # cv2.imencode('.jpg', image)[1].tofile(
        #     os.path.join(temp_dir, f'idx_{count}.jpg'))

        if count < 2:
            count += 1
        else:
            break

    from torch.utils.data import DataLoader
    collater = DiffusionWithLabelCollater()
    train_loader = DataLoader(celebahqtraindataset,
                              batch_size=128,
                              shuffle=True,
                              num_workers=4,
                              collate_fn=collater)

    count = 0
    for data in tqdm(train_loader):
        images, labels = data['image'], data['label']
        print(images.shape, labels.shape)
        print(images.dtype, labels.dtype)
        if count < 2:
            count += 1
        else:
            break
