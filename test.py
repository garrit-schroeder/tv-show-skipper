import concurrent
import re
from concurrent.futures._base import ALL_COMPLETED
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime

from fingerprint import Fingerprint

executor = ThreadPoolExecutor(max_workers=100)
frame_skipts = 1


def replace(s):
    return re.sub('[^A-Za-z0-9]+', '', s)


def load_fingerprint(file):
    with open("frames/" + replace(file) + "/aa_fingerprint.txt", "r") as text_file:
        return text_file.read()


def get_equal_frames(print1, print2):
    equal_frames = []
    count = 0
    while min(len(print1), len(print2)) > count:
        if print1[count] == print2[count]:
            equal_frames.append(print1[count])
        count += 1
    return equal_frames


def do():
    print(datetime.now())
    print1 = Fingerprint(load_fingerprint("samplesModern Family (2009) S11E01.mkv"))
    print2 = Fingerprint(load_fingerprint("samplesModern Family (2009) S11E02.mkv"))
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
    print("(.*)?".join(highest_equal_frames))


do()
