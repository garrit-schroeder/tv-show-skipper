import re
import os
import cv2
import imagehash
import shutil
import numpy
import sys, getopt

from concurrent.futures import ThreadPoolExecutor, process
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image

check_frame = 10  # 1 (slow) to 10 (fast) is fine 
 
def print_debug(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file = sys.stderr)

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


def get_timestamp_from_frame(profile):
    start_time = 0 if profile['start_frame'] == 0 else round(profile['start_frame'] / profile['fps'])
    end_time = 0 if profile['end_frame'] == 0 else round(profile['end_frame'] / profile['fps'])

    profile['start_time_ms'] = start_time * 1000
    profile['end_time_ms'] = end_time * 1000
    profile['start_time'] = str(timedelta(seconds=start_time)).split('.')[0]
    profile['end_time'] = str(timedelta(seconds=end_time)).split('.')[0]

def create_video_fingerprint(path, video, debug):
    video_fingerprint = ""
    
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
        #if count % 1000 == 0 and debug:
        #    print_debug(path + " " + str(count) + "/" + str(int(frames / 4)))
        success, frame = video.read()
        count += 1
    if video_fingerprint == "":
        raise Exception("error creating fingerprint for video [%s]" % path)
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
    for k in range(0, int(len(print1) / 16)):
        equal_frames = get_equal_frames(print1[-k * 16:], print2)
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
        equal_frames = get_equal_frames(print1, print2[k * 16:])
        if len(equal_frames) > len(highest_equal_frames):
            highest_equal_frames = equal_frames
    regex_string = ".*?".join(highest_equal_frames) + "){1,}"
    regex_string = regex_string[:-21] + '(' + regex_string[-21:]
    p = re.compile(regex_string)
    search = re.search(p, "".join(print1))
    search2 = re.search(p, "".join(print2))
    return (int(search.start() / 16), int(search.end() / 16)), (int(search2.start() / 16), int(search2.end() / 16))


def get_or_create_fingerprint(file, debug):
    video = cv2.VideoCapture(file)
    fps = video.get(cv2.CAP_PROP_FPS)

    profile = {}
    profile['fps'] = fps
    profile['path'] = file

    if os.path.exists("fingerprints/" + replace(file) + "/fingerprint.txt"):
        if debug:
            print_debug('loading existing fingerprint for [%s]' % file)
        with open("fingerprints/" + replace(file) + "/fingerprint.txt", "r") as text_file:
            fingerprint = text_file.read()
    else:
        if debug:
            print_debug('creating new fingerprint for [%s]' % file)
        fingerprint = create_video_fingerprint(file, video, debug)
        write_fingerprint(file, fingerprint)

    video.release()
    if debug:
        print_debug("processed fingerprint for [%s]" % file)
    return fingerprint, profile


def process_directory(dir=None, debug=False, cleanup=False):
    if dir == None:
        return

    start = datetime.now()
    if debug:
        print_debug('debug enabled')
        print_debug('started at', start)
        print_debug("Check Frame: %s\n" % str(check_frame))
    if cleanup:
        print_debug('fingerprint files will be cleaned up')

    file_paths = []
    if dir != None and os.path.isdir(dir):
        child_dirs = os.listdir(dir)
        for child in child_dirs:
            if child[0] == '.':
                continue
            file_paths.append(os.path.join(dir, child))
        file_paths.sort()
    else:
        print_debug('input directory invalid or cannot be accessed')
        return {}

    executor = ThreadPoolExecutor(max_workers=3)

    futures = []
    profiles = []
    fingerprints = []
    for file_path in file_paths:
        futures.append(executor.submit(get_or_create_fingerprint, file_path, debug))

    for future in futures:
        fingerprint, profile = future.result()
        fingerprints.append(fingerprint)
        profiles.append(profile)

    counter = 0
    average = 0
    while len(fingerprints) - 1 > counter:
        try:
            start_end = get_start_end(fingerprints[counter], fingerprints[counter + 1])
            
            profiles[counter]['start_frame'] = start_end[0][0] - check_frame + 1
            profiles[counter]['end_frame'] = start_end[0][1]
            get_timestamp_from_frame(profiles[counter])
            if debug:
                print_debug(profiles[counter]['path'] + " start time: " + profiles[counter]['start_time'] + " end time: " + profiles[counter]['end_time'])
            
            profiles[counter + 1]['start_frame'] = start_end[1][0] - check_frame + 1
            profiles[counter + 1]['end_frame'] = start_end[1][1]
            get_timestamp_from_frame(profiles[counter + 1])
            if debug:
                print_debug(profiles[counter + 1]['path'] + " start time: " + profiles[counter + 1]['start_time'] + " end time: " + profiles[counter + 1]['end_time'])

            average += start_end[0][1] - start_end[0][0]
            average += start_end[1][1] - start_end[1][0]
        except:
            print_debug("could not compare fingerprints from files " + profiles[counter]['path'] + " " + profiles[counter + 1]['path'])
        counter += 2
        

    if (len(fingerprints) % 2) != 0:
        try:
            start_end = get_start_end(fingerprints[-2], fingerprints[-1])

            profiles[-1]['start_frame'] = start_end[1][0] - check_frame + 1
            profiles[-1]['end_frame'] = start_end[1][1]
            get_timestamp_from_frame(profiles[-1])
            if debug:
                print_debug(profiles[-1]['path'] + " start time: " + profiles[-1]['start_time'] + " end time: " + profiles[-1]['end_time'])

            average += start_end[1][1] - start_end[1][0]
        except:
            print_debug("could not compare fingerprints from files " + profiles[-2]['path'] + " " + profiles[-1]['path'])

    end = datetime.now()
    if debug:
        print_debug("average: " + str(int(average / len(fingerprints)) + check_frame * 2 - 2))
        print_debug("ended at", end)
        print_debug("duration: " + str(end - start))

    executor.shutdown()
    if cleanup and os.path.isdir('fingerprints'):
        try:
            shutil.rmtree('fingerprints')
        except OSError as e:
            print_debug("Error: %s : %s" % ('fingerprints', e.strerror))
    return profiles

def main(argv):

    path = ''
    debug = False
    cleanup = False
    try:
        opts, args = getopt.getopt(argv,"hi:dc")
    except getopt.GetoptError:
        print_debug('decode.py -i <path> -d (debug) -c (cleanup)\n')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_debug('decode.py -i <path> -d (debug) -c (cleanup)\n')
            sys.exit()
        elif opt == '-i':
            path = arg
        elif opt == '-d':
            debug = True
        elif opt == '-c':
            cleanup = True

    if path == '' or not os.path.isdir(path):
        print_debug('decode.py -i <path> -d (debug) -c (cleanup)\n')
        sys.exit(2)

    process_directory(dir=path, debug=debug, cleanup=cleanup)

if __name__ == "__main__":
   main(sys.argv[1:])
