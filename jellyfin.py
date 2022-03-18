import os
import jellyfin_queries

from jellyfin_api_client import jellyfin_login, jellyfin_logout


server_url = os.environ['JELLYFIN_URL']
server_username = os.environ['JELLYFIN_USERNAME']
server_password = os.environ['JELLYFIN_PASSWORD']

def parse_jellyfin_shows():
    if server_url == '' or server_username == '' or server_password == '':
        print('missing server info')
        return
    client = jellyfin_login(server_url, server_username, server_password)

    jellyfin_queries.get_shows(client)

    jellyfin_logout()

if __name__ == '__main__':
    parse_jellyfin_shows()