import os
import re
import sys
import getopt
import jellyfin_queries
import json
import shutil
import hashlib


from time import sleep
from pathlib import Path
from datetime import datetime
from jellyfin_api_client import jellyfin_login, jellyfin_logout
from decode import process_directory

server_url = os.environ['JELLYFIN_URL'] if 'JELLYFIN_URL' in os.environ else ''
server_username = os.environ['JELLYFIN_USERNAME'] if 'JELLYFIN_USERNAME' in os.environ else ''
server_password = os.environ['JELLYFIN_PASSWORD'] if 'JELLYFIN_PASSWORD' in os.environ else ''
env_path_map_str = os.environ['PATH_MAP'] if 'PATH_MAP' in os.environ else ''
env_reverse_sort_str = os.environ['REVERSE_SORT'] if 'REVERSE_SORT' in os.environ else ''
env_log_level_str = os.environ['LOG_LEVEL'] if 'LOG_LEVEL' in os.environ else ''


config_path = Path(os.environ['CONFIG_DIR']) if 'CONFIG_DIR' in os.environ else Path(Path.cwd() / 'config')
data_path = Path(os.environ['DATA_DIR']) if 'DATA_DIR' in os.environ else Path(config_path / 'data')

minimum_episode_duration = 15  # minutes
maximum_episodes_per_season = 30  # meant to skip daily shows like jeopardy
sleep_after_finish_sec = 300  # sleep for 5 minutes after the script finishes. If it runs automatically this prevents it rapidly looping

session_timestamp = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")


def print_debug(a=[], log=True, log_file=False):
    # Here a is the array holding the objects
    # passed as the argument of the function
    output = ' '.join([str(elem) for elem in a])
    if log:
        print(output, file=sys.stderr)
    if log_file:
        log_path = config_path / 'logs'
        log_path.mkdir(parents=True, exist_ok=True)
        with (log_path / ('log_%s.txt' % session_timestamp)).open('a') as logger:
            logger.write(output + '\n')


def replace(s):
    return re.sub('[^A-Za-z0-9]+', '', s)


def get_path_map(log_level=0):
    path_map = []

    if env_path_map_str != '':
        env_maps = env_path_map_str.strip().split(',')
        for m in env_maps:
            map = m.strip().split('::')
            if len(map) != 2:
                continue
            path_map.append((Path(map[0]), Path(map[1])))

    if (config_path / 'path_map.txt').exists():
        with (config_path / 'path_map.txt').open('r') as file:
            for line in file:
                if line.startswith('#'):
                    continue
                map = line.strip().split('::')
                if len(map) != 2:
                    continue
                path_map.append((Path(map[0]), Path(map[1])))

    if log_level > 1:
        print_debug(a=['path maps: [%s]' % path_map], log=True)
        for path in path_map:
            if Path(path[0]).exists() and Path(path[0]).is_dir():
                print_debug(a=['top level contents of mapped path [%s]' % str(path[0])], log=True)
                for child in Path(path[0]).iterdir():
                    print_debug(a=[str(child.resolve())], log=True)
            else:
                print_debug(a=['mapped path [%s] isn\'t accessible' % str(path[0])], log=True)

            if Path(path[1]).exists() and Path(path[1]).is_dir():
                print_debug(a=['top level contents of mapped path [%s]' % str(path[1])], log=True)
                for child in Path(path[1]).iterdir():
                    print_debug(a=[str(child.resolve())], log=True)
            else:
                print_debug(a=['mapped path [%s] isn\'t accessible' % str(path[1])], log=True)

    return path_map


def check_season_valid(season=None, episodes=[], log_level=0, log_file=False):
    if season is None or not episodes:
        return []

    path = data_path / 'jellyfin_cache' / str(season['SeriesId']) / str(season['SeasonId'])

    file_paths = []
    filtered_episodes = []
    failed_to_find_files = False

    if path.exists():
        for episode in episodes:
            if not Path(episode['Path']).exists():
                failed_to_find_files = True
                continue
            if not Path(path / (str(episode['EpisodeId']) + '.json')).exists():
                filtered_episodes.append(episode)
    else:
        for episode in episodes:
            if not Path(episode['Path']).exists():
                failed_to_find_files = True
                continue
            filtered_episodes.append(episode)

    if failed_to_find_files:
        print_debug(a=['season [%s] of show [%s] - failed to access some of the media files' % (season['Name'], season['SeriesName'])], log=log_level > 1)
        print_debug(a=['path for the first episode [%s]' % episodes[0]['Path']], log=log_level > 1)

    if not filtered_episodes:
        return []
    if len(filtered_episodes) > maximum_episodes_per_season:
        print_debug(a=['skipping season [%s] since it contains %s episodes (more than max %s)' % (season['Name'], len(filtered_episodes), maximum_episodes_per_season)], log=log_level > 1)
        return []
    
    duration_mins = int(filtered_episodes[0]['Duration'])
    if duration_mins > 0:
        duration_mins = duration_mins / 60 / 1000
    if filtered_episodes[0]['Duration'] < minimum_episode_duration * 60 * 1000:
        print_debug(a=['skipping season [%s] of show [%s] - episodes are too short (%s minutes) (less than minimum %s minutes)' % (season['Name'], season['SeriesName'], duration_mins, minimum_episode_duration)], log=log_level > 1)
        return []
    if len(filtered_episodes) < 2:
        print_debug(a=['skipping season [%s] of show [%s] - it doesn\'t contain at least 2 episodes' % (season['Name'], season['SeriesName'])], log=log_level > 1)
        return []

    if len(filtered_episodes) > 0 and len(episodes) - len(filtered_episodes) > 0:
        print_debug(a=['season [%s] of show [%s] - will skip %s of %s episodes' % (season['Name'], season['SeriesName'], len(episodes) - len(filtered_episodes), len(episodes))], log=log_level > 0, log_file=log_file)
    return filtered_episodes


def get_file_paths(season=None):
    if season is None or 'Episodes' not in season:
        return []

    file_paths = []
    for episode in season['Episodes']:
        file_paths.append(episode['Path'])
    return file_paths


def get_jellyfin_shows(reverse_sort=False, log_level=0, log_file=False):
    if server_url == '' or server_username == '' or server_password == '':
        print_debug(a=['missing server info'])
        return

    path_map = get_path_map(log_level)

    client = jellyfin_login(server_url, server_username, server_password, "TV Intro Detection Scanner")
    shows_query = jellyfin_queries.get_shows(client, path_map, reverse_sort)
    if not shows_query:
        print_debug(a=['Error - got 0 shows from jellyfin'])
        return []
    print_debug(a=['jellyfin has %s shows' % len(shows_query)])

    shows = []
    season_count = 0
    episode_count = 0
    for show in shows_query:
        should_skip_series = False
        if 'Path' in show and show['Path'] and Path(show['Path']).is_dir():
            for child in Path(show['Path']).iterdir():
                if child.name == '.ignore-intros':
                    print_debug(a=['ignoring series [%s]' % show['Name']], log=log_level > 0)
                    should_skip_series = True
                    break
        if should_skip_series:
            continue

        seasons = []
        seasons_query = jellyfin_queries.get_seasons(client, path_map, show)

        if not seasons_query:
            continue

        for season in seasons_query:
            should_skip_season = False
            if 'Path' in season and season['Path'] and Path(season['Path']).is_dir():
                for child in Path(season['Path']).iterdir():
                    if child.name == '.ignore-intros':
                        print_debug(a=['ignoring season [%s] of show [%s]' % (season['Name'], show['Name'])], log=log_level > 0)
                        should_skip_season = True
                        break
            if should_skip_season:
                continue

            episodes = jellyfin_queries.get_episodes(client, path_map, season)
            if not episodes:
                continue

            season['Episodes'] = check_season_valid(season, episodes, log_level, log_file)
            if season['Episodes']:
                episode_count += len(season['Episodes'])
                seasons.append(season)
        if seasons:
            season_count += len(seasons)
            show['Seasons'] = seasons
            shows.append(show)

    jellyfin_logout()

    print_debug(a=['found %s qualifying shows' % len(shows)], log_file=log_file and episode_count > 0)
    print_debug(a=['found %s qualifying seasons' % season_count], log_file=log_file and episode_count > 0)
    print_debug(a=['found %s qualifying episodes\n' % episode_count], log_file=log_file and episode_count > 0)

    return shows


def copy_season_fingerprint(result: list = [], dir_path: Path = None, debug: bool = False, log_file: bool = False):
    if not result or dir_path is None:
        return

    name = ''
    for profile in result:
        name += replace(profile['path'])
    hash_object = hashlib.md5(name.encode())
    name = hash_object.hexdigest()

    src_path = Path(data_path / 'fingerprints' / (name + '.json'))
    dst_path = Path(dir_path / ('season' + '.json'))
    dir_path.mkdir(parents=True, exist_ok=True)
    if src_path.exists():
        if debug:
            print_debug(a=['saving season fingerprint to jellyfin_cache'], log_file=log_file)
        shutil.copyfile(src_path, dst_path)


def save_season(season=None, result=None, save_json=False, debug=False, log_file=False):
    if not result or season is None:
        return
    path = data_path / 'jellyfin_cache' / str(season['SeriesId']) / str(season['SeasonId'])
    if save_json:
        copy_season_fingerprint(result, path, debug, log_file)

    for ndx in range(0, len(season['Episodes'])):
        if ndx >= len(result):
            if debug:
                print_debug(a=['episode index past bounds of result'], log_file=log_file)
            break
        if season['Episodes'][ndx]['Path'] == result[ndx]['path']:
            season['Episodes'][ndx].update(result[ndx])
            season['Episodes'][ndx].pop('path', None)
            print(season['Episodes'][ndx])
            season['Episodes'][ndx]['created'] = str(datetime.now())
            if save_json:
                Path(path).mkdir(parents=True, exist_ok=True)
                with Path(path / (str(season['Episodes'][ndx]['EpisodeId']) + '.json')).open('w+') as json_file:
                    json.dump(season['Episodes'][ndx], json_file, indent=4)
        elif debug:
            print_debug(a=['index mismatch'], log_file=log_file)


def process_jellyfin_shows(log_level=0, log_file=False, save_json=False, reverse_sort=False):
    start = datetime.now()
    print_debug(a=["\n\nstarted new session at %s\n" % start])
    if reverse_sort:
        print_debug(['will process shows in reverse order'])

    shows = get_jellyfin_shows(reverse_sort, log_level, log_file)
    
    if (data_path / 'fingerprints').is_dir():
        try:
            shutil.rmtree(data_path / 'fingerprints')
        except OSError as e:
            print_debug(a=["Error: %s : %s" % ('deleting fingerprints directory', e.strerror)], log_file=log_file)

    show_ndx = 0
    total_processed = 0
    for show in shows:
        show_ndx += 1
        show_start_time = datetime.now()

        print_debug(a=['%s/%s - %s' % (show_ndx, len(shows), show['Name'])], log_file=log_file)

        season_ndx = 1
        for season in show['Seasons']:
            season_ndx += 1

            season_start_time = datetime.now()
            file_paths = get_file_paths(season)
            result = []

            if file_paths:
                print_debug(a=['%s/%s - %s - %s episodes' % (season_ndx, len(show['Seasons']), season['Name'], len(season['Episodes']))], log_file=log_file)
                result = process_directory(file_paths=file_paths, cleanup=False, log_level=2 if log_level > 0 else 0, log_file=log_file, log_timestamp=session_timestamp)
                if result:
                    save_season(season, result, save_json, log_level > 0, log_file)
                    total_processed += len(result)
                else:
                    print_debug(a=['no results - the decoder may not have access to the specified media files'], log_file=log_file)
            if (data_path / 'fingerprints').is_dir():
                try:
                    shutil.rmtree(data_path / 'fingerprints')
                except OSError as e:
                    print_debug(a=["Error: %s : %s" % ('deleting fingerprints directory', e.strerror)], log_file=log_file)
            season_end_time = datetime.now()
            if result:
                print_debug(a=['processed season [%s] in %s' % (season['Name'], str(season_end_time - season_start_time))], log_file=log_file)
            if file_paths:
                sleep(2)
        show_end_time = datetime.now()
        print_debug(a=['processed show [%s] in %s\n' % (show['Name'], str(show_end_time - show_start_time))], log_file=log_file)

    end = datetime.now()
    print_debug(a=["total runtime: " + str(end - start)], log_file=log_file and total_processed > 0)
    if sleep_after_finish_sec > 0:
        print_debug(a=['sleeping for %s seconds' % sleep_after_finish_sec])
        sleep(300)


def main(argv):
    log_level = 0
    save_json = False
    log = False
    reverse_sort = False

    try:
        opts, args = getopt.getopt(argv, "hdvjlr", ["reverse"])
    except getopt.GetoptError:
        print_debug(['jellyfin.py -d (debug) -j (save json) -l (log to file)'])
        print_debug(['saving to json is currently the only way to skip previously processed files in subsequent runs\n'])
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_debug(['jellyfin.py -d (debug) -j (save json) -l (log to file)'])
            print_debug(['saving to json is currently the only way to skip previously processed files in subsequent runs\n'])
            sys.exit()
        elif opt == '-d':
            log_level = 2
        elif opt == '-v':
            log_level = 1
        elif opt == '-j':
            save_json = True
        elif opt == '-l':
            log = True
        elif opt in ("-r", "--reverse"):
            reverse_sort = True
    
    if server_url == '' or server_username == '' or server_password == '':
        print_debug(['you need to export env variables: JELLYFIN_URL, JELLYFIN_USERNAME, JELLYFIN_PASSWORD\n'])
        return

    if env_reverse_sort_str == 'TRUE':
        reverse_sort = True
    elif env_reverse_sort_str == 'FALSE':
        reverse_sort = False
    
    if env_log_level_str == 'DEBUG':
        log_level = 2
    elif env_log_level_str == 'VERBOSE':
        log_level = 1
    elif env_log_level_str == 'INFO':
        log_level = 0
    process_jellyfin_shows(log_level, log, save_json, reverse_sort)


if __name__ == "__main__":
    main(sys.argv[1:])
