import os
import jellyfin_queries

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

def process_jellyfin_shows():
    start = datetime.now()

    shows = get_jellyfin_shows()
    for show in shows:
        print(show['Name'])
        show_start_time = datetime.now()

        for season in show['seasons']:
            print(season['Name'])
            season_start_time = datetime.now()

            file_paths = []
            for episode in season['episodes']:
                if 'Path' in episode:
                    file_paths.append(episode['Path'])
            result = process_directory(file_paths=file_paths)

            season_end_time = datetime.now()
            print('processed season [%s] in %s' % (season['Name'], str(season_end_time - season_start_time)))

        show_end_time = datetime.now()
        print('processed show [%s] in %s' % (show['Name'], str(show_end_time - show_start_time)))

    end = datetime.now()
    print("total runtime: " + str(end - start))

if __name__ == '__main__':
    process_jellyfin_shows()