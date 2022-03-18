# tv intro detection

This project tries to detect intros of tv series by comparing two episodes of the same series and trying to find the
largest common subset of frames with a bit of fuzziness.

## Running

1. Install dependencies from `requirements.txt`
2. Modify `file_paths` variable in `main.py` and add the absolute path to at least **two** episodes of the same season


## Disclaimer

Only work if the intro of an episode is similar / identical from episode to episode.<br>
And the intro indeed is the longest sequence in the first quarter of two episodes (should be in all cases)

## How it works
Each frame from the first quarter of each episode is extracted and a hash (https://pypi.org/project/ImageHash/) is made on the frame. Each frame hash is added to a long video hash.<br>
In pairs the longest identical string is searched from two video hashes.<br>
Assumption: this is the intro

## Improvements

1. Dont extract every frame from video - does not speed up fingerprinting. Seeking in a file is slow
2. Make educated guesses on which parts to fingerpint. At the moment the first quarter of an episode is fingerprinted. Might be to much for longer episodes. etc.
3. Create a fingerprint that works for the whole season instead of finding the same fingerprint for every file.



