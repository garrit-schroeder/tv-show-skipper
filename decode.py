import re
import os
import cv2
import imagehash
import shutil
import numpy
import sys, getopt

from time import sleep
from concurrent.futures import ThreadPoolExecutor, process
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image

from ffmpeg_fingerprint import get_fingerprint_ffmpeg

preroll_seconds = 3 # adjust the end time to return n seconds prior to the calculated end time
max_fingerprint_mins = 10
check_frame = 10  # 1 (slow) to 10 (fast) is fine 
workers = 4 # number of executors to use
target_image_height = 180 # scale frames to height of 180px

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

def get_scaled_image(image: Image, log_level):
    width, height = image.size

    new_width = width
    new_height = height
    
    while new_height >= target_image_height:
        tmp_width = new_width / 2
        tmp_height = new_height / 2
        if tmp_width < target_image_height:
            break
        if tmp_width % 2 != 0 or tmp_height % 2 != 0:
            break
        new_height = int(tmp_height)
        new_width = int(tmp_width)
    if new_height != height:
        return image.resize((new_width, new_height))
    return image

def create_video_fingerprint(profile, cleanup, log_level, slow_mode, use_ffmpeg):
    video_fingerprint = ""

    quarter_frames_or_first_X_mins = min(int(profile['total_frames'] / 4), int(profile['fps'] * 60 * max_fingerprint_mins))
    if use_ffmpeg:
        video_fingerprint = get_fingerprint_ffmpeg(profile['path'], quarter_frames_or_first_X_mins, log_level)
        if video_fingerprint != '':
            return video_fingerprint

    video = cv2.VideoCapture(profile['path'])
    sucess, frame = video.read()
    count = 0
    Path("fingerprints/" + replace(profile['path']) + "/frames").mkdir(parents=True, exist_ok=True)
    while count < quarter_frames_or_first_X_mins:  # what is less - the first quarter or the first 10 minutes
        #cv2.imwrite("fingerprints/" + replace(path) + "/frames/frame%d.jpg" % count, frame)
        #image = Image.fromarray(numpy.uint8(frame))
        image = get_scaled_image(Image.fromarray(numpy.uint8(frame)), log_level)
        frame_fingerprint = str(imagehash.phash(image))
        video_fingerprint += frame_fingerprint
        if count % 1000 == 0:
            if not cleanup:
                image.save("fingerprints/" + replace(profile['path']) + "/frames/frame%d.jpg" % count)
            if log_level > 1:
                print_debug(profile['path'] + " " + str(count) + "/" + str(int(profile['total_frames'] / 4)))
        success, frame = video.read()
        count += 1
        if slow_mode:
            sleep(0.005)
    if video_fingerprint == "":
        raise Exception("error creating fingerprint for video [%s]" % profile['path'])
    video.release()
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


def get_or_create_fingerprint(file, cleanup, log_level, slow_mode, use_ffmpeg):
    start = datetime.now()
    video = cv2.VideoCapture(file)
    fps = video.get(cv2.CAP_PROP_FPS)

    profile = {}
    profile['fps'] = fps
    profile['path'] = file
    profile['total_frames'] = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()

    if os.path.exists("fingerprints/" + replace(file) + "/fingerprint.txt"):
        if log_level > 0:
            print_debug('loading existing fingerprint for [%s]' % file)
        with open("fingerprints/" + replace(file) + "/fingerprint.txt", "r") as text_file:
            fingerprint = text_file.read()
    else:
        if log_level > 0:
            print_debug('creating new fingerprint for [%s]' % file)
        fingerprint = create_video_fingerprint(profile, cleanup, log_level, slow_mode, use_ffmpeg)
        if not cleanup:
            write_fingerprint(file, fingerprint)
    
    end = datetime.now()
    if log_level > 0:
        print_debug("processed fingerprint for [%s] in %s" % (file, str(end - start)))
    return fingerprint, profile

def check_files_exist(file_paths = []):
    if not file_paths:
        return False
    for file in file_paths:
        if not os.path.exists(file):
            return False
    return True

def reject_outliers(data, m = 3.):
    if not isinstance(data, numpy.ndarray):
        data = numpy.array(data)
    d = numpy.abs(data - numpy.median(data))
    mdev = numpy.median(d)
    s = d / (mdev if mdev else 1.)
    output = data[s<m].tolist()

    # sometimes numpy tolist() returns a nested list
    if type(output[0]) == list:
        return output[0]
    return output

def correct_errors(profiles, log_level):
    lengths = []
    for profile in profiles:
        lengths.append(profile['end_frame'] - profile['start_frame'])
    filtered_lengths = reject_outliers(lengths)

    size = len(filtered_lengths)
    sum = 0
    for f in filtered_lengths:
        sum += f
    average = int(sum / size)

    if log_level > 1:
        print_debug('average length in frames [%s] from %s of %s files' % (average, len(filtered_lengths), len(profiles)))

    conforming_profiles = []
    non_conforming_profiles = []
    for ndx in range(0, len(profiles)):
        if log_level > 1:
            print_debug('file [%s] diff from average %s' % (profiles[ndx]['path'], abs(profiles[ndx]['end_frame'] - profiles[ndx]['start_frame'] - average)))
        if abs(profiles[ndx]['end_frame'] - profiles[ndx]['start_frame'] - average) < int(2 * profiles[ndx]['fps']):
            conforming_profiles.append(ndx)
        else:
            non_conforming_profiles.append(ndx)
    if log_level > 1:
        print_debug('rejected start frame values from %s of %s results' % (len(non_conforming_profiles), len(profiles)))
    for nprofile in non_conforming_profiles:
        profiles[nprofile]['start_frame'] = profiles[nprofile]['end_frame'] - average


def process_directory(file_paths = [], log_level=0, cleanup=True, slow_mode=False, use_ffmpeg=False):
    start = datetime.now()
    if log_level > 0:
        print_debug('started at', start)
        print_debug("Check Frame: %s\n" % str(check_frame))
        if cleanup:
            print_debug('fingerprint files will be cleaned up')
        if slow_mode:
            print_debug('slow mode enabled')

    if not check_files_exist(file_paths):
        if log_level > 0:
            print_debug('input files invalid or cannot be accessed')
        return {}
    
    if len(file_paths) < 2:
        if log_level > 0:
            print_debug('file list size is less than 2 - skipping')
        return {}
    
    if log_level > 0:
        print_debug('processing %s files' % len(file_paths))
    
    if cleanup and os.path.isdir('fingerprints'):
        try:
            shutil.rmtree('fingerprints')
        except OSError as e:
            print_debug("Error: %s : %s" % ('fingerprints', e.strerror))

    profiles = []
    fingerprints = []

    if use_ffmpeg:
        for file_path in file_paths:
            fingerprint, profile = get_or_create_fingerprint(file_path, cleanup, log_level, slow_mode, use_ffmpeg)
            fingerprints.append(fingerprint)
            profiles.append(profile)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for file_path in file_paths:
                futures.append(executor.submit(get_or_create_fingerprint, file_path, cleanup, log_level, slow_mode, use_ffmpeg))

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
            if profiles[counter]['start_frame'] < 0:
                profiles[counter]['start_frame'] = 0
            profiles[counter]['end_frame'] = start_end[0][1]

            profiles[counter + 1]['start_frame'] = start_end[1][0] - check_frame + 1
            if profiles[counter + 1]['start_frame'] < 0:
                profiles[counter + 1]['start_frame'] = 0
            profiles[counter + 1]['end_frame'] = start_end[1][1]

            average += start_end[0][1] - start_end[0][0]
            average += start_end[1][1] - start_end[1][0]
        except:
            if log_level > 0:
                print_debug("could not compare fingerprints from files " + profiles[counter]['path'] + " " + profiles[counter + 1]['path'])
        counter += 2
        

    if (len(fingerprints) % 2) != 0:
        try:
            start_end = get_start_end(fingerprints[-2], fingerprints[-1])

            profiles[-1]['start_frame'] = start_end[1][0] - check_frame + 1
            if profiles[-1]['start_frame'] < 0:
                profiles[-1]['start_frame'] = 0
            profiles[-1]['end_frame'] = start_end[1][1]

            average += start_end[1][1] - start_end[1][0]
        except:
            print_debug("could not compare fingerprints from files " + profiles[-2]['path'] + " " + profiles[-1]['path'])

    correct_errors(profiles, log_level)
    for profile in profiles:
        if preroll_seconds > 0 and profile['end_frame'] > int(profile['fps'] * preroll_seconds):
            profile['end_frame'] -= int(profile['fps'] * preroll_seconds)
        get_timestamp_from_frame(profile)
        if log_level > 1:
            print_debug(profile['path'] + " start time: " + profile['start_time'] + " end time: " + profile['end_time'])
            

    end = datetime.now()
    if log_level > 0:
        print_debug("ended at", end)
        print_debug("duration: " + str(end - start))

    if cleanup and os.path.isdir('fingerprints'):
        try:
            shutil.rmtree('fingerprints')
        except OSError as e:
            print_debug("Error: %s : %s" % ('fingerprints', e.strerror))
    return profiles

def main(argv):

    path = ''
    log_level = 0
    cleanup = False
    slow_mode = False
    use_ffmpeg = False
    try:
        opts, args = getopt.getopt(argv,"hi:dvcf")
    except getopt.GetoptError:
        print_debug('decode.py -i <path> -v (verbose - some logging) -d (debug - most logging) -c (cleanup) -s (slow mode)\n')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_debug('decode.py -i <path> -v (verbose - some logging) -d (debug - most logging) -c (cleanup) -s (slow mode)\n')
            sys.exit()
        elif opt == '-i':
            path = arg
        elif opt == '-f':
            use_ffmpeg = True
        elif opt == '-d':
            log_level = 2
        elif opt == '-v':
            log_level = 1
        elif opt == '-c':
            cleanup = True
        elif opt == '-s':
            slow_mode = True

    if path == '' or not os.path.isdir(path):
        print_debug('decode.py -i <path> -v (verbose - some logging) -d (debug - most logging) -c (cleanup) -s (slow mode)\n')
        sys.exit(2)

    common_video_extensions = ['.webm', '.mkv', '.avi', '.mts', '.m2ts', '.ts', '.mov', '.wmv', '.mp4', '.m4v', '.mpg', '.mpeg', '.m2v' ]

    file_paths = []
    if os.path.isdir(path):
        child_dirs = os.listdir(path)
        for child in child_dirs:
            if child[0] == '.':
                continue
            matched_ext = False
            for ext in common_video_extensions:
                if child.endswith(ext):
                    matched_ext = True
            if matched_ext:
                file_paths.append(os.path.join(path, child))
        file_paths.sort()
    else:
        print_debug('input directory invalid or cannot be accessed')

    result = process_directory(file_paths=file_paths, log_level=log_level, cleanup=cleanup, slow_mode=slow_mode, use_ffmpeg=use_ffmpeg)
    print(result)

if __name__ == "__main__":
   main(sys.argv[1:])
