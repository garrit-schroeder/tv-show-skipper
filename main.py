import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from os import path
from pathlib import Path

import cv2
import imagehash
import numpy
from PIL import Image

executor = ThreadPoolExecutor(max_workers=3)


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
    frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    success, frame = video.read()
    count = 0
    Path("fingerprints/" + replace(path) + "/frames").mkdir(parents=True, exist_ok=True)
    while count < int(frames / 4):
        if debug:
            cv2.imwrite("fingerprints/" + replace(path) + "/frames/frame%d.jpg" % count, frame)
        image = Image.fromarray(numpy.uint8(frame))
        frame_fingerprint = str(imagehash.dhash(image))
        video_fingerprint += frame_fingerprint
        if count % 1000 == 0:
            print(path + " " + str(count) + "/" + str(int(frames / 4)))
        success, frame = video.read()
        count += 1
    if video_fingerprint == "":
        raise Exception("video fingerprint empty created " + path)
    return video_fingerprint


def get_equal_frames(print1, print2):
    equal_frames = []
    for j in range(0, int(len(print1) / 16 / check_frame)):
        if print1[j * 16 * check_frame:j * 16 * check_frame + 16] == print2[
                                                                     j * 16 * check_frame:j * 16 * check_frame + 16]:
            equal_frames.append(print1[j * 16 * check_frame:j * 16 * check_frame + 16])
    return equal_frames


def get_start_end(print1, print2):
    highest_equal_frames = []
    for k in range(0, int(len(print1) / 16 / check_frame)):
        equal_frames = get_equal_frames(print1[-k * 16 * check_frame:], print2)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
        equal_frames = get_equal_frames(print1, print2[k * 16 * check_frame:])
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    p = re.compile(".*?".join(highest_equal_frames))
    search = re.search(p, "".join(print1))
    search2 = re.search(p, "".join(print2))
    return (int(search.start() / 16), int(search.end() / 16)), (int(search2.start() / 16), int(search2.end() / 16))


def get_or_create_fingerprint(file):
    if path.exists("fingerprints/" + replace(file) + "/fingerprint.txt"):
        print(file + " fingerprint exists - loading it")
        with open("fingerprints/" + replace(file) + "/fingerprint.txt", "r") as text_file:
            fingerprint = text_file.read()
    else:
        print(file + " fingerprint does not exist - creating it")
        fingerprint = create_video_fingerprint(file)
        write_fingerprint(file, fingerprint)
    return fingerprint


start = datetime.now()
print(start)
debug = False
# take every X frame
# 1 works the best
# 2 sometimes works as good as 1 but not always
# 3 and further not tested
check_frame = 5  # 1 to 10 is fine
print("Check Frame: " + str(check_frame))
file_paths = [
    'samples/Modern Family (2009) S11E01.mkv',
    'samples/Modern Family (2009) S11E02.mkv',
    'samples/Modern Family (2009) S11E03.mkv',
    'samples/Modern Family (2009) S11E04.mkv',
    'samples/Modern Family (2009) S11E05.mkv',
    'samples/Modern Family (2009) S11E06.mkv',
    'samples/Modern Family (2009) S11E07.mkv',
    'samples/Modern Family (2009) S11E08.mkv',
    'samples/Modern Family (2009) S11E09.mkv',
    'samples/Modern Family (2009) S11E10.mkv',
    'samples/Modern Family (2009) S11E11.mkv',
    'samples/Modern Family (2009) S11E12.mkv',
    'samples/Modern Family (2009) S11E13.mkv',
    'samples/Modern Family (2009) S11E14.mkv',
    'samples/Modern Family (2009) S11E15.mkv',
    'samples/Modern Family (2009) S11E16.mkv',
    'samples/Modern Family (2009) S11E17.mkv',
    'samples/Modern Family (2009) S11E18.mkv',
]

futures = []
fingerprints = []
for file_path in file_paths:
    futures.append(executor.submit(get_or_create_fingerprint, file_path))

for future in futures:
    fingerprints.append(future.result())

counter = 0
while len(fingerprints) - 1 > counter:
    start_end = get_start_end(fingerprints[counter], fingerprints[counter + 1])
    print(file_paths[counter] + " start: " + str(start_end[0][0]) + " end " + str(start_end[0][1]))
    print(file_paths[counter + 1] + " start: " + str(start_end[1][0]) + " end " + str(start_end[1][1]))
    counter += 2

if (len(fingerprints) % 2) != 0:
    start_end = get_start_end(fingerprints[-2], fingerprints[-1])
    print(file_paths[-1] + " start: " + str(start_end[1][0]) + " end " + str(start_end[1][1]))

end = datetime.now()
print(end)
print("duration: " + str(end - start))
executor.shutdown()
