import re
import sys
from datetime import datetime
from os import path
from pathlib import Path

import cv2
import imagehash
from PIL import Image


def dict_by_value(dict, value):
    for name, age in dict.items():
        if age == value:
            return name


def write_fingerprint(path, fingerprint):
    path = "frames/" + replace(path) + "/aa_fingerprint.txt"
    with open(path, "w+") as text_file:
        text_file.write(fingerprint)


def replace(s):
    return re.sub('[^A-Za-z0-9]+', '', s)


def create_frame_fingerprint(image_path):
    image = Image.open(image_path)
    h = str(imagehash.dhash(image))
    return h


def create_video_fingerprint(path):
    video_fingerprint = ""
    video = cv2.VideoCapture(path)
    fps = video.get(cv2.CAP_PROP_FPS)
    success, image = video.read()
    count = 0
    while count < int(300.0 * fps) + 1:
        frame_path = "frames/" + replace(path)
        Path(frame_path).mkdir(parents=True, exist_ok=True)
        cv2.imwrite(frame_path + "/frame%d.jpg" % count, image)  # save frame as JPEG file
        frame_fingerprint = create_frame_fingerprint(frame_path + "/frame%d.jpg" % count)
        video_fingerprint += frame_fingerprint
        print(path + " " + str(count) + "/" + str(int(300.0 * fps) + 1) + " " + frame_fingerprint, success)
        success, image = video.read()
        count += sample_frame
    return video_fingerprint


def get_equal_frames(print1, print2):
    equal_frames = []
    count = 0
    while min(len(print1), len(print2)) > count:
        if print1[count] == print2[count]:
            equal_frames.append(print1[count])
        count += 1
    return equal_frames


def tokenize_fingerprints(video_fingerprints):
    unique_prints = set()
    for fingerprint in video_fingerprints:
        for frame_print in re.findall("................", fingerprint):
            unique_prints.add(frame_print)
    matrix = {}
    counter = 60
    for unique_print in unique_prints:
        matrix[unique_print] = chr(counter)
        counter += 1
    tokenprints = []
    for fingerprint in video_fingerprints:
        t = fingerprint
        for key in matrix.items():
            t = t.replace(key[0], str(key[1]))
        tokenprints.append(t.replace(".", ""))
    return tokenprints, matrix


def get_start_end(print1, print2):
    offset = len(print1)
    highest_equal_frames = []
    for i in range(0, offset):
        equal_frames = get_equal_frames(print1[-i:], print2)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    for i in range(0, offset):
        equal_frames = get_equal_frames(print1, print2[i:])
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    p = re.compile(".*?".join(highest_equal_frames))
    search = re.search(p, print1)
    search2 = re.search(p, print2)
    return (search.start(), search.end()), (search2.start(), search2.end())


def for_files(files):
    fingerprints = []
    for file in files:
        if path.exists("frames/" + replace(file) + "/aa_fingerprint.txt"):
            print(file + " fingerprint exists - loading it")
            with open("frames/" + replace(file) + "/aa_fingerprint.txt", "r") as text_file:
                fingerprint = text_file.read()
        else:
            print(file + " fingerprint does not exist - creating it")
            fingerprint = create_video_fingerprint(file)
            write_fingerprint(file, fingerprint)
        fingerprints.append(fingerprint)
    tokens, matrix = tokenize_fingerprints(fingerprints)
    print(files[0] + " - " + str(get_start_end(tokens[0], tokens[1])))
    print(files[0] + " - " + str(get_start_end(tokens[2], tokens[3])))
    print(files[0] + " - " + str(get_start_end(tokens[4], tokens[5])))


print(datetime.now())
seconds_from_start = 300  # 5 minuets
sample_frame = 1  # take every X frame
paths = [
]
for_files(paths)
print(datetime.now())
