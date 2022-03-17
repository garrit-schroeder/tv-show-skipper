import re
import os
from concurrent.futures import ThreadPoolExecutor, process
from datetime import datetime
from os import path
import sys, getopt
from pathlib import Path

import cv2
import imagehash
import numpy
from PIL import Image

from datetime import timedelta

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


def get_timestamp_from_frame(path, start, end):
    video = cv2.VideoCapture(path)

    fps = video.get(cv2.CAP_PROP_FPS)
    start_time = 0 if start == 0 else round(start / fps)
    end_time = 0 if end == 0 else round(end / fps)
    video.release()
    return start_time, end_time

def create_video_fingerprint(path, debug):
    video_fingerprint = ""
    video = cv2.VideoCapture(path)
    frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    sucess, frame = video.read()
    count = 0
    Path("fingerprints/" + replace(path) + "/frames").mkdir(parents=True, exist_ok=True)
    while count < int(frames / 4):
        if debug:
            cv2.imwrite("fingerprints/" + replace(path) + "/frames/frame%d.jpg" % count, frame)
        image = Image.fromarray(numpy.uint8(frame))
        frame_fingerprint = str(imagehash.dhash(image))
        video_fingerprint += frame_fingerprint
        if count % 1000 == 0 and debug:
            print(path + " " + str(count) + "/" + str(int(frames / 4)))
        success, frame = video.read()
        count += 1
    if video_fingerprint == "":
        raise Exception("video fingerprint empty created " + path)
    return video_fingerprint


def get_equal_frames(print1, print2, check_frame):
    equal_frames = []
    for j in range(0, int(len(print1) / 16 / check_frame)):
        if print1[j * 16 * check_frame:j * 16 * check_frame + 16] == print2[
                                                                     j * 16 * check_frame:j * 16 * check_frame + 16]:
            equal_frames.append(print1[j * 16 * check_frame:j * 16 * check_frame + 16])
    return equal_frames


def get_start_end(print1, print2, check_frame):
    highest_equal_frames = []
    for k in range(0, int(len(print1) / 16)):
        equal_frames = get_equal_frames(print1[-k * 16:], print2, check_frame)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
        equal_frames = get_equal_frames(print1, print2[k * 16:], check_frame)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    regex_string = ".*?".join(highest_equal_frames) + "){1,}"
    regex_string = regex_string[:-21] + '(' + regex_string[-21:]
    p = re.compile(regex_string)
    search = re.search(p, "".join(print1))
    search2 = re.search(p, "".join(print2))
    return (int(search.start() / 16), int(search.end() / 16)), (int(search2.start() / 16), int(search2.end() / 16))


def get_or_create_fingerprint(file, debug):
    if path.exists("fingerprints/" + replace(file) + "/fingerprint.txt"):
        if debug:
            print(file + " fingerprint exists - loading it")
        with open("fingerprints/" + replace(file) + "/fingerprint.txt", "r") as text_file:
            fingerprint = text_file.read()
    else:
        if debug:
            print(file + " fingerprint does not exist - creating it")
        fingerprint = create_video_fingerprint(file, debug)
        write_fingerprint(file, fingerprint)
    print("finished processing [%s]" % file)
    return fingerprint


def process_directory(dir, debug=False):
    executor = ThreadPoolExecutor(max_workers=3)

    start = datetime.now()
    print('started at', start)
    check_frame = 10  # 1 (slow) to 10 (fast) is fine
    print("Check Frame: %s\n" % str(check_frame))
    file_paths = []
    if os.path.isdir(dir):
            child_dirs = os.listdir(dir)
            for child in child_dirs:
                if child[0] == '.':
                    continue
                file_paths.append(os.path.join(dir, child))

    file_paths.sort()

    futures = []
    fingerprints = []
    for file_path in file_paths:
        futures.append(executor.submit(get_or_create_fingerprint, file_path, debug))

    for future in futures:
        fingerprints.append(future.result())

    print('\n\n')

    counter = 0
    average = 0
    while len(fingerprints) - 1 > counter:
        try:
            start_end = get_start_end(fingerprints[counter], fingerprints[counter + 1], check_frame)

            start1_sec, end1_sec = get_timestamp_from_frame(file_paths[counter], start_end[0][0] - check_frame + 1, start_end[0][1])
            start1_str = str(timedelta(seconds=start1_sec)).split('.')[0]
            end1_str = str(timedelta(seconds=end1_sec)).split('.')[0]

            #print(file_paths[counter] + " start frame: " + str(start_end[0][0] - check_frame + 1) + " end frame: " + str(
            #    start_end[0][1]))
            print(file_paths[counter] + " start time: " + start1_str + " end time: " + end1_str)
            
            start2_sec, end2_sec = get_timestamp_from_frame(file_paths[counter + 1], start_end[1][0] - check_frame + 1, start_end[1][1])
            start2_str = str(timedelta(seconds=start2_sec)).split('.')[0]
            end2_str = str(timedelta(seconds=end2_sec)).split('.')[0]

            #print(file_paths[counter + 1] + " start frame: " + str(start_end[1][0] - check_frame + 1) + " end frame: " + str(
            #    start_end[1][1]))
            print(file_paths[counter + 1] + " start time: " + start2_str + " end time: " + end2_str)

            average += start_end[0][1] - start_end[0][0]
            average += start_end[1][1] - start_end[1][0]
        except:
            print("could not compare fingerprints from files " + file_paths[counter] + " " + file_paths[counter + 1])
        counter += 2
        

    if (len(fingerprints) % 2) != 0:
        try:
            start_end = get_start_end(fingerprints[-2], fingerprints[-1], check_frame)
            start_sec, end_sec = get_timestamp_from_frame(file_paths[-1], start_end[1][0], start_end[1][1])
            start_str = str(timedelta(seconds=start_sec)).split('.')[0]
            end_str = str(timedelta(seconds=end_sec)).split('.')[0]

            #print(file_paths[-1] + " start frame: " + str(start_end[1][0] - check_frame + 1) + " end frame: " + str(
            #    start_end[1][1]))
            print(file_paths[counter] + " start time: " + start_str + " end time: " + end_str)

            average += start_end[1][1] - start_end[1][0]
        except:
            print("could not compare fingerprints from files " + file_paths[-2] + " " + file_paths[-1])

    end = datetime.now()
    print("ended at", end)
    print("duration: " + str(end - start))
    #print("average: " + str(int(average / len(fingerprints)) + check_frame * 2 - 2))
    executor.shutdown()


def main(argv):

    path = ''
    debug = False

    try:
        opts, args = getopt.getopt(argv,"hi:d")
    except getopt.GetoptError:
        print('main.py -i <path> -d (debug)\n')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('main.py -i <path> -d (debug)\n')
            sys.exit()
        elif opt == '-i':
            path = arg
        elif opt == '-d':
            debug = True

    if path == '' or not os.path.isdir(path):
        print('main.py -i <path> -d (debug)\n')
        sys.exit(2)
    process_directory(path, debug)


if __name__ == "__main__":
   main(sys.argv[1:])
