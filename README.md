# tv intro detection

This project tries to detect intros of tv series by comparing two episodes of the same series and trying to find the
largest common subset of frames with a bit of fuzziness.

## Running

1. Install python dependencies from `requirements.txt`
2. Install ffmpeg (optional)
3. To use with Jellyfin, run `jellyfin.py`. This will query Jellyfin for a list of series and their paths. By default the query to the server is limited to 1 series (for testing reasons). Comment out `'Limit': 1` in `jellyfin_queries.py` to remove this limit.
4. To process a directory manually, run `decode.py` and pass the parameter `-i` with the path to a directory containing at least **two** episodes of the same season

By default there is little/no output to stdout or stderr until the script has finished processing some media. Run `jellyfin.py` or `decode.py` with the `-d` parameter for verbose output

When using `jellyfin.py`, the results can be saved to `json` using the `-j` parameter. These will be saved in a sub-directory in `pwd`. Saving the results as json also allows them to be checked in subsequent runs to skip already processed files.

When using `jellyfin.py`, `path_map.txt` can be used to specify path mapping between the host and container if jellyfin is run with Docker.

## Disclaimer

Only work if the intro of an episode is similar / identical from episode to episode.<br>
And the intro indeed is the longest sequence in the first quarter of two episodes (should be in all cases)

## How it works
Each frame from the first quarter of each episode is extracted and a hash (https://pypi.org/project/ImageHash/) is made on the frame. Each frame hash is added to a long video hash.<br>
In pairs the longest identical string is searched from two video hashes.<br>
Assumption: this is the intro

## Troubleshooting
If the script is killed while processing media you may encounter issues the next time you run it. This is because corrupt `fingerprint` files are likely left over from the killed session. Simply remove the directory `fingerprints` before running the script again. The same can be done for `jellyfin_cache` though it is less likely to become corrupted

## Improvements

1. Make educated guesses on which parts to fingerpint. At the moment the first quarter of an episode is fingerprinted. Might be to much for longer episodes. etc.
2. Create a fingerprint that works for the whole season instead of finding the same fingerprint for every file.
