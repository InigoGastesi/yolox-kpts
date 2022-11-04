import os
import mmcv
import yaml
import shutil
from tqdm import tqdm
import json
import argparse

parser = argparse.ArgumentParser("YCB_PBR2COCO_PARSER")
parser.add_argument("--type", default="real", type=str, help="real, pbr or synt or bop")
parser.add_argument("--keyframes", default="/data/ssd/6d_pose/ycbv/keyframe.txt", type=str, help="path to the keyframes file list")
parser.add_argument("--split", default='train', type=str, help="Use selected frames")

args = parser.parse_args()

class_to_name = {
    0: "002_master_chef_can" , 1: "003_cracker_box" ,  2: "004_sugar_box" , 3: "005_tomato_soup_can",  4: "006_mustard_bottle",
    5: "007_tuna_fish_can",  6: "008_pudding_box" , 7: "009_gelatin_box", 8: "010_potted_meat_can",  9: "011_banana",
    10: "019_pitcher_base", 11: "021_bleach_cleanser",  12: "024_bowl", 13: "025_mug", 14: "035_power_drill",
    15: "036_wood_block", 16: "037_scissors", 17: "040_large_marker", 18: "051_large_clamp", 19: "052_extra_large_clamp",
    20: "061_foam_brick"
}

def convert_to_coco_json(merge=False):
    basepath = '/data/ssd/6d_pose/ycbv/{}_{}'.format(args.split, args.type)
    data_folders = sorted(os.listdir(basepath))

    outfile = '/data/ssd/6d_pose/ycbv/annotations/temp/instances_{}_{}.json'.format(args.split, args.type)
    if args.split == 'test':
        assert args.keyframes is not None, "keyframe file has to be specified"
        with open(args.keyframes):
            keyframes_list = list(open(args.keyframes))
        keyframes_list = ["00" + keyframe.rstrip()+".png" for keyframe in keyframes_list]

    for data_folder_idx, data_folder in enumerate(data_folders):
        data_path = os.path.join(basepath, data_folder)
        annotations_gt = dict()
        for f in ('scene_gt_info.json', 'scene_gt.json'):
            path = os.path.join(data_path,  f)
            if os.path.exists(path):
                print("Loading {}".format(path))
                with open(path) as foo:
                    annotations_gt[f.split('.')[0]] = json.load(foo)

        if not merge or data_folder_idx==0:
            coco = dict()
            coco["images"] = []
            coco["type"] = "instance"
            coco["categories"] = []
            coco["annotations"] = []

            for obj_class in class_to_name:
                category = dict([
                    ("supercategory", "object"),
                    ("id", obj_class),
                    ("name", class_to_name[obj_class])
                ])

                coco["categories"].append(category)

            obj_count = 0
            img_count = 0

        pbar = tqdm(enumerate(zip(list(annotations_gt['scene_gt'].items()), list(annotations_gt['scene_gt_info'].items()))), total=len(annotations_gt['scene_gt_info']))
        num_images = len(list(annotations_gt['scene_gt'].items()))
        for image_index, objects in pbar:
            objects_gt, objects_gt_info = objects[0], objects[1]
            if args.type == "real":
                filename = "{:06}".format(image_index+1) + '.png'
            elif args.type == "pbr":
                filename = "{:06}".format(image_index) + '.jpg'
            if args.keyframes is not None and args.split != 'train':
                print(os.path.join(data_folder, filename))
                if os.path.join(data_folder, filename) not in keyframes_list :
                    continue
            elif image_index%10 != 0 and args.type!="pbr":
                continue

            height, width = mmcv.imread(data_path + '/rgb/' + filename).shape[:2]
            image = dict([
                ("image_folder", data_folder),
                ("id", img_count), #
                ("file_name", filename),
                ("height", height),
                ("width", width),
            ])
            if "real" in path:
                image.update({'type': "real"})
            elif "pbr" in path:
                image.update({'type': "pbr"})
            else:
                image.update({'type': "syn"})

            coco["images"].append(image)
            for object_gt, object_gt_info  in zip(objects_gt[1], objects_gt_info[1]):
                if object_gt_info['visib_fract'] > 0:
                    annotation = dict([
                        ("image_id", img_count),
                        ("id", obj_count),
                        ("bbox", object_gt_info["bbox_visib"]),
                        ("area", object_gt_info["bbox_visib"][2] * object_gt_info["bbox_visib"][3]),
                        ("iscrowd", 0),
                        ("category_id", object_gt["obj_id"]-1),
                        ("R", object_gt["cam_R_m2c"]),
                        ("T", object_gt["cam_t_m2c"])
                    ])
                    obj_count += 1
                    coco["annotations"].append(annotation)
            img_count += 1
        pbar.close()

    mmcv.dump(coco, outfile)

def sort_images(src, train_dst, test_dst, test_list):
    for image_num in range(1214):
        filename = "{:04}".format(image_num) + '.png'
        if filename[:-4] in test_list:
            shutil.copy(os.path.join(src,filename), os.path.join(test_dst, filename))
        else:
            shutil.copy(os.path.join(src,filename), os.path.join(train_dst, filename))


if __name__ == "__main__":
        convert_to_coco_json(merge=True)
