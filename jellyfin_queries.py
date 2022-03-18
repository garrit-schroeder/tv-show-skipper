import os
from time import sleep

def map_path(path, path_map):
    new_path = path

    for mapping in path_map:
        if mapping[1] in path:
            remainder = path[len(mapping[1]) + 1:] if str(path[len(mapping[1]):]).startswith('/') else path[len(mapping[1]):]
            new_path = os.path.join(mapping[0], remainder)
            break
    return new_path

def get_shows(client = None, path_map = []):
    if client == None:
        return False

    result = client.jellyfin.user_items(params={
                'Recursive': True,
                'includeItemTypes': (
                    "Series"
                ),
                'enableImages': False,
                'enableUserData': False,
                'Fields': (
                    "ProviderIds",
                    "Path"
                ),
                #'Limit': 1
            })

    if 'Items' in result and result['Items']:
        for item in result['Items']:
            print(item['Name'])
            print(item['Id'])
            if 'Path' in item:
                print(map_path(item['Path'], path_map))
            get_seasons(client, path_map, item['Id'])
            sleep(0.2)
        print('found %s shows' % len(result['Items']))

def get_seasons(client = None, path_map = [], seriesID = ''):
    if client == None or seriesID == '':
        return False

    result = client.jellyfin.get_seasons(seriesID)

    if 'Items' in result and result['Items']:
        for item in result['Items']:
            print(item['Name'])
            print(item['Id'])
            if 'Path' in item:
                print(map_path(item['Path'], path_map))
            get_season(client, path_map, seriesID, item['Id'])
            sleep(0.2)
        print('found %s seasons' % len(result['Items']))

def get_season(client = None, path_map = [], seriesID = '', seasonID = ''):
    if client == None or seriesID == '' or seasonID == '':
        return False

    result = client.jellyfin.shows("/%s/Episodes" % seriesID, {
            'UserId': "{UserId}",
            'SeasonId': seasonID,
            'Fields': (
                "ProviderIds",
                "Path"
            )
        })
    
    if 'Items' in result and result['Items']:
        for item in result['Items']:
            print(item['Name'])
            print(item['Id'])
            if 'Path' in item:
                print(map_path(item['Path'], path_map))
        print('found %s episodes' % len(result['Items']))