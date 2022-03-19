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
        return []

    shows = []

    try:
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
                    # added this limit for safety in case someone runs this without understanding what it does
                    # remove the limit to process all shows
                    'Limit': 1
                })

        if 'Items' in result and result['Items']:
            for item in result['Items']:
                show = {}
                show['Name'] = item['Name']
                show['SeriesId'] = item['Id']
                show['Path'] = map_path(item['Path'], path_map) if 'Path' in item else None
                shows.append(show)
    except:
        return []
    sleep(0.2)
    return shows

def get_seasons(client = None, path_map = [], series = None):
    if client == None or series == None:
        return []

    seasons = []

    try:
        result = client.jellyfin.get_seasons(series['SeriesId'])

        if 'Items' in result and result['Items']:
            for item in result['Items']:
                season = {}
                season['Name'] = item['Name']
                season['SeriesId'] = series['SeriesId']
                season['SeasonId'] = item['Id']
                season['Path'] = map_path(item['Path'], path_map) if 'Path' in item else None
                seasons.append(season)
    except:
        return []
    sleep(0.2)
    return seasons

def get_episodes(client = None, path_map = [], season = None):
    if client == None or season == None:
        return []

    episodes = []

    try:
        result = client.jellyfin.shows("/%s/Episodes" % season['SeriesId'], {
                'UserId': "{UserId}",
                'SeasonId': season['SeasonId'],
                'Fields': (
                    "ProviderIds",
                    "Path"
                )
            })
        
        if 'Items' in result and result['Items']:
            for item in result['Items']:
                episode = {}
                episode['Name'] = item['Name']
                episode['SeriesId'] = season['SeriesId']
                episode['SeasonId'] = season['SeasonId']
                episode['EpisodeId'] = item['Id']
                if 'Path' in item:
                    episode['Path'] = map_path(item['Path'], path_map)
                    episodes.append(episode)
    except:
        return []
    return episodes

