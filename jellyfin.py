import os
import jellyfin_queries

from jellyfin_api_client import jellyfin_login, jellyfin_logout


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

def parse_jellyfin_shows():
    if server_url == '' or server_username == '' or server_password == '':
        print('missing server info')
        return
    path_map = get_path_map()

    client = jellyfin_login(server_url, server_username, server_password)
    jellyfin_queries.get_shows(client, path_map)

    jellyfin_logout()
    print(path_map)

if __name__ == '__main__':
    parse_jellyfin_shows()