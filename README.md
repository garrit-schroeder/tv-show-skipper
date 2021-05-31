# tv-show-skipper

This project tries to detect intros of tv series by comparing two episodes of the same series and trying to find the
largest common subset of frames with a bit of fuzziness.

## Running

1. Install dependencies from `requirements.txt`
2. Modify `paths` variable in `main.py` and add the absolute path to at least **two** episodes of the same season.
   (Is hard coded to only work with 5 paths at the moment!!)
3. (Run this code only for one season of one show at a time)