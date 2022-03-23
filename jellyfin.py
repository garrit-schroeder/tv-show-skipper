import os
import sys, getopt
import jellyfin_queries
import json
import signal


from time import sleep
from pathlib import Path
from datetime import datetime, timedelta
from jellyfin_api_client import jellyfin_login, jellyfin_logout
from decode import process_directory

server_url = os.environ['JELLYFIN_URL'] if 'JELLYFIN_URL' in os.environ else ''
server_username = os.environ['JELLYFIN_USERNAME'] if 'JELLYFIN_USERNAME' in os.environ else ''
server_password = os.environ['JELLYFIN_PASSWORD'] if 'JELLYFIN_PASSWORD' in os.environ else ''

minimum_episode_duration = 15 # minutes
maximum_episodes_per_season = 20 # meant to skip daily shows like jeopardy

should_stop = False

def print_debug(*a):
    # Here a is the array holding the objects
    # passed as the argument of the function
    print(*a, file = sys.stderr)

def get_path_map():
    path_map = []
    with open('path_map.txt', 'r') as file:
        for line in file:
            if line.startswith('#'):
                continue
            map = line.strip().split(':')
            if len(map) != 2:
                continue
            path_map.append((map[0], map[1]))
    return path_map

def get_jellyfin_shows():
    if server_url == '' or server_username == '' or server_password == '':
        print_debug('missing server info')
        return

    path_map = get_path_map()

    client = jellyfin_login(server_url, server_username, server_password)
    shows = jellyfin_queries.get_shows(client, path_map)
    for show in shows:
        seasons = jellyfin_queries.get_seasons(client, path_map, show)
        for season in seasons:
            season['Episodes'] = jellyfin_queries.get_episodes(client, path_map, season)
        show['Seasons'] = seasons
    jellyfin_logout()

    return shows

def save_season(season = None, result = None, save_json = False, debug = False):
    if not result or result == None or season == None:
        return
    path = "jellyfin_cache/" + str(season['SeriesId']) + "/" + str(season['SeasonId'])

    for ndx in range(0, len(season['Episodes'])):
        if ndx >= len(result):
            if debug:
                print_debug('episode index past bounds of result')
            break
        if season['Episodes'][ndx]['Path'] == result[ndx]['path']:
            season['Episodes'][ndx].update(result[ndx])
            season['Episodes'][ndx].pop('path', None)
            print(season['Episodes'][ndx])
            season['Episodes'][ndx]['created'] = str(datetime.now())
            if save_json:
                Path(path).mkdir(parents=True, exist_ok=True)
                with open(os.path.join(path, str(season['Episodes'][ndx]['EpisodeId']) + '.json'), "w+") as json_file:
                    json.dump(season['Episodes'][ndx], json_file, indent = 4)
        elif debug:
            print_debug('index mismatch')

def check_json_cache(season = None):
    path = "jellyfin_cache/" + str(season['SeriesId']) + "/" + str(season['SeasonId'])

    file_paths = []

    if os.path.exists(path):
        filtered_episodes = []
        for episode in season['Episodes']:
            if not os.path.exists(os.path.join(path, str(episode['EpisodeId']) + '.json')):
                filtered_episodes.append(episode)
        print_debug('processing %s of %s episodes' % (len(filtered_episodes), len(season['Episodes'])))
        season['Episodes'] = filtered_episodes

    for episode in season['Episodes']:
        file_paths.append(episode['Path'])
    return file_paths

def process_jellyfin_shows(log_level = 0, save_json=False, slow_mode=False):
    start = datetime.now()

    shows = get_jellyfin_shows()

    show_ndx = 1
    for show in shows:
        print_debug('%s/%s - %s' % (show_ndx, len(shows), show['Name']))
        show_ndx += 1
        show_start_time = datetime.now()

        season_ndx = 1
        for season in show['Seasons']:
            print_debug('%s/%s - %s' % (season_ndx, len(show['Seasons']), season['Name']))
            season_ndx += 1

            if len(season['Episodes']) < 2:
                print_debug('skipping season since it doesn\'t contain at least 2 episodes')
                continue
            if len(season['Episodes']) > maximum_episodes_per_season:
                print_debug('skipping season since it contains %s episodes (more than max %s)' % (len(season['Episodes']), maximum_episodes_per_season))
                continue
            if season['Episodes'][0]['Duration'] < minimum_episode_duration * 60 * 1000:
                print_debug('skipping season since episodes are too short (%s) (less than minimum %s minutes)' % (len(season['Episodes']), minimum_episode_duration))
                continue

            season_start_time = datetime.now()
            file_paths = check_json_cache(season)
            if file_paths:
                result = process_directory(file_paths=file_paths, log_level=log_level, slow_mode=slow_mode, use_ffmpeg=True)
                if result:
                    save_season(season, result, save_json, log_level > 0)
                else:
                    print_debug('no results - the decoder may not have access to the specified media files')
            season_end_time = datetime.now()
            print_debug('processed season [%s] in %s' % (season['Name'], str(season_end_time - season_start_time)))
            if file_paths:
                sleep(2)
            if should_stop:
                break
        show_end_time = datetime.now()
        print_debug('processed show [%s] in %s' % (show['Name'], str(show_end_time - show_start_time)))
        if should_stop:
            break

    end = datetime.now()
    print_debug("total runtime: " + str(end - start))

def main(argv):
    log_level = 0
    save_json = False
    slow_mode = False

    try:
        opts, args = getopt.getopt(argv,"hdjs")
    except getopt.GetoptError:
        print_debug('jellyfin.py -d (debug) -j (save json) -s (slow mode)')
        print_debug('use -s (slow mode) to limit cpu use')
        print_debug('saving to json is currently the only way to skip previously processed files in subsequent runs\n')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_debug('jellyfin.py -d (debug) -j (save json) -s (slow mode)')
            print_debug('use -s (slow mode) to limit cpu use')
            print_debug('saving to json is currently the only way to skip previously processed files in subsequent runs\n')
            sys.exit()
        elif opt == '-d':
            log_level = 2
        elif opt == '-v':
            log_level = 1
        elif opt == '-j':
            save_json = True
        elif opt == '-s':
            slow_mode = True
    
    if server_url == '' or server_username == '' or server_password == '':
        print_debug('you need to export env variables: JELLYFIN_URL, JELLYFIN_USERNAME, JELLYFIN_PASSWORD\n')

    process_jellyfin_shows(log_level, save_json, slow_mode)

def receiveSignal(signalNumber, frame):
    global should_stop
    print_debug('Received signal:', signalNumber)
    if signalNumber == signal.SIGINT:
        print_debug('will stop after current season')
        should_stop = True
    return

if __name__ == "__main__":
   main(sys.argv[1:])