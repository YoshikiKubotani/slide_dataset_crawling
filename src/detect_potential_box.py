import os
import cv2
import pytesseract
import matplotlib.pyplot as plt
import nltk
import re
import numpy as np
from copy import deepcopy
import statistics
from functools import partial

def pytesseract_ocr_img(img):
    ocr_box_list = []
    img_h, img_w, img_c = img.shape
    d = pytesseract.image_to_data(img, config="--psm 6", output_type=pytesseract.Output.DICT)
    n_boxes = len(d['text'])
    for i in range(n_boxes):
        if int(d['conf'][i]) > 20 and d["level"][i] == 5:
            (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
            if w > img_w/2 and h > img_h/2:
                continue
            word = d["text"][i]
            if both_sym.match(word):
                print("{} is matched with both_sym".format(word))
                word = re.sub(both_sym, r"\2", word)
            elif init_sym.match(word):
                print("{} is matched with init_sym".format(word))
                word = re.sub(init_sym, r"\2", word)
            elif end_sym.match(word):
                print("{} is matched with end_sym".format(word))
                word = re.sub(end_sym, r"\1", word)

            if word.lower() in english_vocab and len(word) != 1:
                img = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                ocr_box_list.append(((x, y), (x + w, y + h)))
            elif word.lower() == "i" or word.lower() == "a":
                img = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                ocr_box_list.append(((x, y), (x + w, y + h)))
            else:
                img = cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                ocr_box_list.append(((x, y), (x + w, y + h)))
    return img, ocr_box_list

def split_chunk(img, top_pos, rows, cols, id_prefix=""):
    chunk_dict = {}
    y_pos = top_pos[1]
    for row_id, row_img in enumerate(np.array_split(img, rows, axis=0)):
        x_pos = top_pos[0]
        h_chunk = row_img.shape[0]
        y_top = y_pos
        y_pos += h_chunk
        for column_id, chunk in enumerate(np.array_split(row_img, cols, axis=1)):
            w_chunk = chunk.shape[1]
            x_left = x_pos
            x_pos += w_chunk
            chunk_id = row_id*cols + column_id
            h_chunk_id = id_prefix + str(chunk_id)
            top_left = (x_left, y_top)
            bottom_right = (x_pos, y_pos)
            value_dict = {"img": chunk, "bbox": (top_left, bottom_right)}
            chunk_dict[h_chunk_id] = value_dict
    return chunk_dict

def detection(chunk_dict, row, col, th_ratio=0.8):
    box = {}
    break_flag = False
    for h_chunk_id, value_dict in chunk_dict.items():
        chunk = value_dict["img"]
        curr_pos = value_dict["bbox"][0]
        h_level = len(h_chunk_id.split("_"))
        if h_level > 6:
            break_flag = True
        tab = "\t"*(h_level - 1)
        # chunkが背景のみの場合は、次のchunkへ
        if np.all(chunk == 255):
            continue
        # 背景以外を含む場合
        else:
            top = chunk[0, :] # 上辺
            bottom = chunk[-1:, :] # 下辺
            right = chunk[:, 0] # 右辺
            left = chunk[:, -1] # 左辺
            chunk_area = chunk.shape[0] * chunk.shape[1] # 面積
            back_area = np.count_nonzero(chunk == 255) # 背景の面積
            obj_area_ratio = 1 - back_area / chunk_area # chunk全体の面積に対して、背景以外の占める割合
            # chunkがほとんど背景の場合も次のchunkへ
            if obj_area_ratio < 0.001:
                continue
            # chunkの縁に物体がかかっていない場合は、potential boxBに分類
            if np.all(top == 255) and np.all(bottom == 255) and np.all(right == 255) and np.all(left == 255):
                # 4.a もっと細かく区切るべき
                # 4.b chunkの大部分がオブジェクトを占め、オブジェクト自体はchunkを横断していないが、複数のオブジェクトを含む可能性がある
                print("{} - Object is NOT crossed with the chunk edge".format(tab))
                if break_flag:
                    if obj_area_ratio > th_ratio:
                        box[h_chunk_id] = value_dict["bbox"]
                        print("{}Processing for {}".format(tab, h_chunk_id))
                        print("{} - Stopped but chunk stored".format(tab, obj_area_ratio))
                    continue
                child_chunk_dict = split_chunk(chunk, curr_pos, row, col, id_prefix=h_chunk_id+"_")
                box[h_chunk_id] = detection(child_chunk_dict, row, col, th_ratio=th_ratio*0.9)
            # chunkの縁に物体がかかっている場合は、potential boxAに分類
            else:
                # chunkの大部分がオブジェクトを占め、オブジェクト自体はchunkを横断している
                print("{} - Object is crossed with the chunk edge".format(tab))
                if obj_area_ratio > th_ratio:
                    print("{}Processing for {}".format(tab, h_chunk_id))
                    print("{} - Object area ratio is {}; higher than threshold".format(tab, obj_area_ratio))
                    box[h_chunk_id] = value_dict["bbox"]
                else:
                    #3.a もっと細かく区切るべき
                    print("{} - Object area is {}; lower than threshold".format(tab, obj_area_ratio))
                    if break_flag:
                        continue
                    child_chunk_dict = split_chunk(chunk, curr_pos, row, col, id_prefix=h_chunk_id+"_")
                    box[h_chunk_id] = detection(child_chunk_dict, row, col, th_ratio=th_ratio*0.9)
    return box


data_folder = os.path.join(os.getcwd(), "data/raw")

# これをターミナルから先に実行しておくこと
# nltk.download('words')
# nltk.download('reuters')
# nltk.download('brown')

english_vocab_words = set(w.lower() for w in nltk.corpus.words.words())
english_vocab_reuters = set(w.lower() for w in nltk.corpus.reuters.words())
english_vocab_brown = set(w.lower() for w in nltk.corpus.brown.words())

english_vocab = english_vocab_words| english_vocab_reuters | english_vocab_brown

both_sym = re.compile("(\W{1})([a-zA-Z]*)(\W{1})")
init_sym = re.compile("(\W{1})([a-zA-Z]*)")
end_sym = re.compile("([a-zA-Z]*)(\W{1})")


for dirpath, dirnames, filenames in os.walk(data_folder):
    last_dir = dirpath.split("/")[-1]
    if last_dir == "img":
        conference, year, paper_id, last_dir = dirpath.split("/")[-4:]
        box_json_save_folder = os.path.join(os.getcwd(), "data/potential_box_annotation", conference, year, paper_id, "box_json")
        box_vis_save_folder = os.path.join(os.getcwd(), "data/potential_box_annotation", conference, year, paper_id, "visualization")
        os.makedirs(box_json_save_folder, exist_ok=True)
        os.makedirs(box_vis_save_folder, exist_ok=True)

        print("Start processing {}".format(paper_id))
        for filename in filenames:
            slide_id = int(filename.split(".")[0][-3:])
            print("\tProcess the {}/{} slide image.".format(slide_id, len(filenames)))
            slide_img_path = os.path.join(dirpath, filename)


            img_BGR = cv2.imread(slide_img_path)

            img_height = img_BGR.shape[0]
            img_width = img_BGR.shape[1]
            print("\t({}, {})".format(img_height, img_width))
            row_split = 2
            col_split = 3

            # スライドの縁の数ピクセルは強制的に白とする
            img_BGR[0:2, :] = 255 # 上辺
            img_BGR[-2:, :] = 255 # 下辺
            img_BGR[:, 0:2] = 255 # 右辺
            img_BGR[:, -2:] = 255 # 左辺

            ocr_BGR_img, ocr_box_list = pytesseract_ocr_img(deepcopy(img_BGR))

            gray_img = cv2.cvtColor(img_BGR, cv2.COLOR_BGR2GRAY)
            inv_gray_img = cv2.bitwise_not(gray_img)
            th_inv_gray_img = cv2.threshold(inv_gray_img, 10, 255, cv2.THRESH_TOZERO)[1]
            th_gray_img = cv2.bitwise_not(th_inv_gray_img)

            chunk_dict = split_chunk(th_gray_img, (0,0), row_split, col_split)
            box_dict = detection(chunk_dict, row_split, col_split, th_ratio=0.9)

            bbox_pos_list = []

            for h_1, h_1_dict in box_dict.items():
                if isinstance(h_1_dict, dict):
                    for h_2, h_2_dict in h_1_dict.items():
                        if isinstance(h_2_dict, dict):
                            for h_3, h_3_dict in h_2_dict.items():
                                if isinstance(h_3_dict, dict):
                                    for h_4, h_4_dict in h_3_dict.items():
                                        if isinstance(h_4_dict, dict):
                                            for h_5, h_5_dict in h_4_dict.items():
                                                if isinstance(h_5_dict, dict):
                                                    for h_6, h_6_dict in h_5_dict.items():
                                                        if isinstance(h_6_dict, dict):
                                                            if len(h_6_dict) == 0:
                                                                # print("empty")
                                                                continue
                                                            for val in h_6_dict.values():
                                                                bbox_pos_list.append(val)
                                                        else:
                                                            bbox_pos_list.append(h_6_dict)
                                                else:
                                                    bbox_pos_list.append(h_5_dict)
                                        else:
                                            bbox_pos_list.append(h_4_dict)
                                else:
                                    bbox_pos_list.append(h_3_dict)
                        else:
                            bbox_pos_list.append(h_2_dict)
                else:
                    bbox_pos_list.append(h_1_dict)


            result_img = deepcopy(img_BGR)
            for pos in bbox_pos_list:
                result_img = cv2.rectangle(result_img, pos[0], pos[1], (0, 255, 0), thickness=-1)

            re_ocr_box_list = []
            for ocr_box in ocr_box_list:
                x1, y1 = ocr_box[0]
                x2, y2 = ocr_box[1]
                ocr_area_result_img = result_img[y1:y2, x1:x2, :]
                # print("({}, {}) - ({}, {})".format(x1,y1,x2,y2))
                # print(ocr_area_result_img.shape)
                is_green_area = np.logical_and.reduce((
                    ocr_area_result_img[:, :, 0] == 0,
                    ocr_area_result_img[:, :, 1] == 255,
                    ocr_area_result_img[:, :, 2] == 0
                ))
                green_pixel_count = np.count_nonzero(ocr_area_result_img[is_green_area])
                all_pixel_count = ocr_area_result_img.shape[0] * ocr_area_result_img.shape[1]
                green_area_ratio = green_pixel_count/all_pixel_count
                if green_area_ratio > 0.4:
                    re_ocr_box_list.append(ocr_box)

            # ocr_result_image = deepcopy(img_BGR)
            # for pos in re_ocr_box_list:
            #     ocr_result_image = cv2.rectangle(ocr_result_image, pos[0], pos[1], (0, 255, 0), -1)
            #     result_img = cv2.rectangle(result_img, pos[0], pos[1], (0, 255, 0), -1)

            grayed_result = cv2.cvtColor(deepcopy(result_img), cv2.COLOR_BGR2GRAY)
            _, bin_result = cv2.threshold(grayed_result, 150, 255, cv2.THRESH_BINARY)
            bin_result = cv2.bitwise_not(bin_result)

            # cnt_result = deepcopy(img_BGR)
            box_result = deepcopy(img_BGR)
            # 輪郭取得
            contours, _ = cv2.findContours(bin_result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            contours2 = list(filter(lambda x: cv2.contourArea(x) >= 25, contours))

            # for i, cnt in enumerate(contours2):
            #     cv2.drawContours(cnt_result, contours, -1, (0, 255, 0), 2)

            for i, cnt in enumerate(contours2):
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                cv2.drawContours(box_result,[box],0,(0,0,255),2)

            cv2.imwrite(os.path.join(box_vis_save_folder, "pbox_res_page{:03d}.png".format(slide_id)), box_result)