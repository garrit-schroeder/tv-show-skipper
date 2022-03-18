import os

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
                )
            })
    if 'Items' in result and result['Items']:
        for item in result['Items']:
            print(item['Name'])
            print(item['Id'])
            print(map_path(item['Path'], path_map))
        print(len(result['Items']))
