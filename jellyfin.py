import os
import jellyfin_queries
import json

from pathlib import Path
from datetime import datetime, timedelta
from jellyfin_api_client import jellyfin_login, jellyfin_logout
from decode import process_directory

server_url = os.environ['JELLYFIN_URL']
server_username = os.environ['JELLYFIN_USERNAME']
server_password = os.environ['JELLYFIN_PASSWORD']

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
        print('missing server info')
        return

    path_map = get_path_map()

    client = jellyfin_login(server_url, server_username, server_password)
    shows = jellyfin_queries.get_shows(client, path_map)
    for show in shows:
        seasons = jellyfin_queries.get_seasons(client, path_map, show)
        for season in seasons:
            season['episodes'] = jellyfin_queries.get_episodes(client, path_map, season)
        show['seasons'] = seasons
    jellyfin_logout()

    return shows

def save_season_json(season = None, result = None):
    if not result or result == None or season == None:
        return
    path = "jellyfin_cache/" + str(season['SeriesId']) + "/" + str(season['SeasonId'])
    if not os.path.exists(path):
        print('path doesn\'t exist')
        return

    for ndx in range(0, len(season['episodes'])):
        if ndx >= len(result):
            print('episode index past bounds of result')
            break
        if season['episodes'][ndx]['Path'] == result[ndx]['path']:
            season['episodes'][ndx].update(result[ndx])
            season['episodes'][ndx]['created'] = str(datetime.now())
            season['episodes'][ndx].pop('path', None)
            with open(os.path.join(path, season['episodes'][ndx]['EpisodeId'] + '.json'), "w+") as json_file:
                json.dump(season['episodes'][ndx], json_file, indent = 4)
        else:
            print('index mismatch')

def check_json_cache(season = None):
    path = "jellyfin_cache/" + str(season['SeriesId']) + "/" + str(season['SeasonId'])

    file_paths = []

    if not os.path.exists(path):
        Path(path).mkdir(parents=True, exist_ok=True)
    else:
        filtered_episodes = []
        for episode in season['episodes']:
            if not os.path.exists(os.path.join(path, episode['EpisodeId'] + '.json')):
                filtered_episodes.append(episode)
        print('processing %s of %s episodes' % (len(filtered_episodes), len(season['episodes'])))
        season['episodes'] = filtered_episodes

    for episode in season['episodes']:
        file_paths.append(episode['Path'])
    return file_paths

def process_jellyfin_shows():
    start = datetime.now()

    shows = get_jellyfin_shows()
    for show in shows:
        print(show['Name'])
        show_start_time = datetime.now()

        for season in show['seasons']:
            print(season['Name'])
            season_start_time = datetime.now()

            file_paths = check_json_cache(season)
            result = process_directory(file_paths=file_paths)
            print(result)
            if result:
                save_season_json(season, result)
            season_end_time = datetime.now()
            print('processed season [%s] in %s' % (season['Name'], str(season_end_time - season_start_time)))

        show_end_time = datetime.now()
        print('processed show [%s] in %s' % (show['Name'], str(show_end_time - show_start_time)))

    end = datetime.now()
    print("total runtime: " + str(end - start))

if __name__ == '__main__':
    process_jellyfin_shows()