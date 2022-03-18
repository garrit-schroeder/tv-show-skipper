def get_shows(client = None, path_mapping = []):
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
            print(item['Path'])
        print(len(result['Items']))