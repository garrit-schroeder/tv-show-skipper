import re
import sys
from datetime import datetime
from os import path
from pathlib import Path

import cv2
import imagehash
import numpy
from PIL import Image


def dict_by_value(dict, value):
    for name, age in dict.items():
        if age == value:
            return name


def write_fingerprint(path, fingerprint):
    path = "fingerprints/" + replace(path) + "/fingerprint.txt"
    with open(path, "w+") as text_file:
        text_file.write(fingerprint)


def replace(s):
    return re.sub('[^A-Za-z0-9]+', '', s)


def create_video_fingerprint(path):
    video_fingerprint = ""
    video = cv2.VideoCapture(path)
    max_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    success, frame = video.read()
    count = 0
    Path("fingerprints/" + replace(path) + "/frames").mkdir(parents=True, exist_ok=True)
    while count < int(max_frames / 4):
        if debug:
            cv2.imwrite("fingerprints/" + replace(path) + "/frames/frame%d.jpg" % count, frame)
        image = Image.fromarray(numpy.uint8(frame))
        frame_fingerprint = str(imagehash.dhash(image))
        video_fingerprint += frame_fingerprint
        if count % 1000 == 0:
            print(path + " " + str(count) + "/" + str(int(max_frames / 4)))
        success, frame = video.read()
        count += sample_frame
    if video_fingerprint == "":
        raise Exception("video fingerprint empty created " + path)
    return video_fingerprint


def get_equal_frames(print1, print2):
    equal_frames = []
    count = 0
    while min(len(print1), len(print2)) > count:
        if print1[count] == print2[count]:
            equal_frames.append(print1[count])
        count += 1
    return equal_frames


def get_start_end(print1, print2):
    highest_equal_frames = []
    for i in range(0, len(print1)):
        equal_frames = get_equal_frames(print1[-i:], print2)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
        equal_frames = get_equal_frames(print1, print2[i:])
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    p = re.compile(".*?".join(highest_equal_frames) + "*")
    search = re.search(p, "".join(print1))
    search2 = re.search(p, "".join(print2))
    return (int(search.start() / 16), int(search.end() / 16)), (int(search2.start() / 16), int(search2.end() / 16))


def for_files(files):
    fingerprints = []
    for file in files:
        if path.exists("fingerprints/" + replace(file) + "/fingerprint.txt"):
            print(file + " fingerprint exists - loading it")
            with open("fingerprints/" + replace(file) + "/fingerprint.txt", "r") as text_file:
                fingerprint = text_file.read()
        else:
            print(file + " fingerprint does not exist - creating it")
            fingerprint = create_video_fingerprint(file)
            write_fingerprint(file, fingerprint)
        fingerprints.append(re.findall("................", fingerprint))
    # todo use files list to calculate entries and display. temp only
    print(str(get_start_end(fingerprints[0], fingerprints[1])))
    print(str(get_start_end(fingerprints[2], fingerprints[3])))
    print(str(get_start_end(fingerprints[4], fingerprints[5])))
    print(str(get_start_end(fingerprints[6], fingerprints[7])))
    print(str(get_start_end(fingerprints[8], fingerprints[9])))
    print(str(get_start_end(fingerprints[10], fingerprints[11])))
    print(str(get_start_end(fingerprints[12], fingerprints[13])))
    print(str(get_start_end(fingerprints[14], fingerprints[15])))
    print(str(get_start_end(fingerprints[16], fingerprints[15])))


start = datetime.now()
print(start)
debug = False
# take every X frame
# 1 works the best
# 2 sometimes works as good as 1 but not always
# 3 and further not tested
sample_frame = 1
paths = [

]
for_files(paths)
end = datetime.now()
print(end)
print("untoken duration: " + str(end - start))
