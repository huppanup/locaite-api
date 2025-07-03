import pandas as pd
import numpy as np
import os
import os.path as osp
import utm
from math import ceil, floor
from collections import Counter

ROOT = os.getcwd()
FILLED_FLOOR = "0"

def get_closest_floor(pressure, floor_dict):
    cur_diff_dict = {k:abs(v-pressure) for k,v in floor_dict.items()}
    return list(cur_diff_dict.keys())[list(cur_diff_dict.values()).index(min(cur_diff_dict.values()))]

def train_process(INPUT_SITE_FOLDER, OUTPUT_SITE_FOLDER):
    pressure_id_dict = {}
    cur_floor = FILLED_FLOOR
    # get ground truth for floors
    for fname in os.listdir(osp.join(ROOT, INPUT_SITE_FOLDER)):
        if not fname.startswith("."):
            fpath = osp.join(ROOT, INPUT_SITE_FOLDER, fname)
            with open(fpath, "r") as f_in:
                for line in f_in.readlines()[9:]:
                    cur_record = line.strip("\n").split(",")
                    if len(cur_record)>1: # non-empty record
                        if cur_record[1][1:-1]=="15":
                            cur_floor = cur_record[5][1:-1]
                        if cur_record[1][1:-1]=="8" and cur_floor!=FILLED_FLOOR:
                            if cur_floor not in pressure_id_dict.keys():
                                pressure_id_dict[cur_floor] = [float(cur_record[3][1:-1])]
                            else:
                                pressure_id_dict[cur_floor].append(float(cur_record[3][1:-1]))
    press_id_dict = {k:sum(v)/len(v) for k, v in pressure_id_dict.items()}

    for wanted_floor in press_id_dict.keys():
        # get Xs and Ys # hold back wrong floors for unclassified, not making decision [system]
        # withhold decision for 1 & 6/R to wait for information, in order to have credibal results
        X_list = []
        Y_list = []
        cur_floor = FILLED_FLOOR
        for fname in os.listdir(osp.join(ROOT, INPUT_SITE_FOLDER)):
            if not fname.startswith("."):
                fpath = osp.join(ROOT, INPUT_SITE_FOLDER, fname)
                with open(fpath, "r") as f_in:
                    for line in f_in.readlines()[9:]:
                        cur_record = line.strip("\n").split(",")
                        if len(cur_record)>1: # non-empty record
                            if cur_record[1][1:-1]=="8":
                                cur_floor = get_closest_floor(float(cur_record[3][1:-1]), press_id_dict)
                            elif cur_record[1][1:-1]=="3" and cur_floor==wanted_floor:
                                cur_utm = utm.from_latlon(float(cur_record[3][1:-1]), float(cur_record[4][1:-1]))
                                X_list.append(cur_utm[0])
                                Y_list.append(cur_utm[1])
        min_X = min(X_list)
        min_Y = min(Y_list)
        max_X = max(X_list)
        max_Y = max(Y_list)

        # get AP list
        full_AP_list = []
        good_AP_list = []
        for fname in os.listdir(osp.join(ROOT, INPUT_SITE_FOLDER)):
            if not fname.startswith("."):
                fpath = osp.join(ROOT, INPUT_SITE_FOLDER, fname)
                with open(fpath, "r") as f_in:
                    for line in f_in.readlines()[9:]:
                        cur_record = line.strip("\n").split(",")
                        if len(cur_record)>1: # non-empty record
                            if cur_record[1][1:-1]=="8":
                                cur_floor = get_closest_floor(float(cur_record[3][1:-1]), press_id_dict)
                            elif cur_record[1][1:-1]=="1" and cur_floor==wanted_floor:
                                full_AP_list.append(cur_record[3][1:-1])
        cur_Counter = Counter(full_AP_list)
        cur_occurence_list = list(cur_Counter.values())
        mean_occurence = sum(cur_occurence_list)/len(cur_occurence_list)
        for k, v in dict(cur_Counter).items():
            if v>max(mean_occurence, 100):
                good_AP_list.append(k)
        print("AP generation done!")

        # get map for each good AP in the floor
        good_AP_dict = {}
        cur_i = -1
        cur_j = -1
        for cur_AP in good_AP_list:
            print("Working with AP: {}".format(cur_AP))
            cur_array = np.zeros((ceil(max_X)-floor(min_X), ceil(max_Y)-floor(min_Y)))
            for i in range(ceil(max_X)-floor(min_X)):
                for j in range(ceil(max_Y)-floor(min_Y)):
                    cur_array[i][j] = -100.0
            for fname in os.listdir(osp.join(ROOT, INPUT_SITE_FOLDER)):
                if not fname.startswith("."):
                    fpath = osp.join(ROOT, INPUT_SITE_FOLDER, fname)
                    with open(fpath, "r") as f_in:
                        for line in f_in.readlines()[9:]:
                            cur_record = line.strip("\n").split(",")
                            if len(cur_record)>1: # non-empty record
                                if cur_record[1][1:-1]=="8":
                                    cur_floor = get_closest_floor(float(cur_record[3][1:-1]), press_id_dict)
                                elif cur_record[1][1:-1]=="3" and cur_floor==wanted_floor:
                                    cur_utm = utm.from_latlon(float(cur_record[3][1:-1]), float(cur_record[4][1:-1]))
                                    cur_i = round(cur_utm[0]-min_X)
                                    cur_j = round(cur_utm[1]-min_Y)
                                elif cur_record[1][1:-1]=="1" and cur_floor==wanted_floor and cur_i>=0 and cur_j>=0:
                                    if cur_i<ceil(max_X)-floor(min_X) and cur_j<ceil(max_Y)-floor(min_Y):
                                        if cur_array[cur_i][cur_j]==-100.0 and cur_record[3][1:-1]==cur_AP:
                                            cur_array[cur_i][cur_j] = float(cur_record[6][1:-1])

            if np.amax(blurred_array)>-100.0:
                good_AP_dict[cur_AP] = blurred_array
        print("AP dict dictionary done!")

        # generate output_file
        with open(osp.join(OUTPUT_SITE_FOLDER, "{}F.csv").format(wanted_floor[0]), "w") as f_out, open(osp.join(OUTPUT_SITE_FOLDER, "{}F.txt").format(wanted_floor[0]), "w") as f_out2:
            f_out2.write(str(min_X))
            f_out2.write(",")
            f_out2.write(str(min_Y))
            f_out2.write("\n")
            f_out2.write("50")
            f_out2.write(",")
            f_out2.write('"Q"')
            f_out2.write("\n")

            f_out.write("X,Y,")
            for cur_AP in good_AP_list:
                f_out.write(cur_AP)
                f_out.write(",")
            f_out.write("\n")
            for i in range(ceil(max_X)-floor(min_X)):
                for j in range(ceil(max_Y)-floor(min_Y)):
                    f_out.write(str(i))
                    f_out.write(",")
                    f_out.write(str(j))
                    f_out.write(",")
                    for cur_AP in good_AP_list:
                        f_out.write(str(good_AP_dict[cur_AP][i][j]))
                        f_out.write(",")
                    f_out.write("\n")