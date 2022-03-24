import os
import json
import arrow
import signal

from time import sleep
from datetime import datetime, timezone

from jellyfin_api_client import jellyfin_login, jellyfin_logout

server_url = os.environ['JELLYFIN_URL'] if 'JELLYFIN_URL' in os.environ else ''
server_username = os.environ['JELLYFIN_USERNAME'] if 'JELLYFIN_USERNAME' in os.environ else ''
server_password = os.environ['JELLYFIN_PASSWORD'] if 'JELLYFIN_PASSWORD' in os.environ else ''

TICKS_PER_MS = 10000

preroll_seconds = 3
minimum_intro_length = 10 # seconds

client = None

def monitor_sessions():
    global client

    if client == None:
        return

    start = datetime.now(timezone.utc)
    sessions = client.jellyfin.sessions()
    for session in sessions:
        if session['UserId'] != client.auth.jellyfin_user_id():
            continue
        if not 'PlayState' in session or session['PlayState']['CanSeek'] == False:
            continue
        if not 'Capabilities' in session or session['Capabilities']['SupportsMediaControl'] == False:
            continue
        if not 'LastPlaybackCheckIn' in session:
            continue
        if not 'NowPlayingItem' in session:
            continue

        sessionId = session['Id']

        #print('user id %s' % session['UserId'])
        print(session['DeviceName'])

        lastPlaybackTime = arrow.get(session['LastPlaybackCheckIn']).to('utc').datetime
        timeDiff = start - lastPlaybackTime

        item = session['NowPlayingItem']
        if not session['PlayState']['IsPaused'] and timeDiff.seconds < 5:
            print('currently playing %s - %s - Episode %s [%s]' % (item['SeriesName'], item['SeasonName'], item['ParentIndexNumber'], item['Name']))
            print('item id %s' % item['Id'])
        else:
            print('not playing or hasn\'t checked in')
            continue
        position_ticks = int(session['PlayState']['PositionTicks'])
        print('current position %s minutes' % (((position_ticks / TICKS_PER_MS) / 1000) / 60))

        file_path = 'jellyfin_cache/' + str(item['SeriesId']) + '/' + str(item['SeasonId']) + '/' + str(item['Id']) + '.json'
        start_time_ticks = 0
        end_time_ticks = 0
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                dict = json.load(json_file)
                if 'start_time_ms' in dict and 'end_time_ms' in dict:
                    start_time_ticks = int(dict['start_time_ms']) * TICKS_PER_MS
                    end_time_ticks = int(dict['end_time_ms']) * TICKS_PER_MS
        else:
            print('couldn\'t find data for item')
            continue
        
        if start_time_ticks == 0 and end_time_ticks == 0:
            print('no useable intro data')
            continue

        if position_ticks < start_time_ticks or position_ticks > end_time_ticks:
            continue

        if end_time_ticks - start_time_ticks < minimum_intro_length * 1000 * TICKS_PER_MS:
            print('intro is less than %ss - skipping' % minimum_intro_length)
            continue

        preroll_ticks = preroll_seconds * 1000 * TICKS_PER_MS
        if end_time_ticks - preroll_ticks >= 0:
            end_time_ticks -= preroll_ticks

        print('trying to send seek to client')
        client.jellyfin.sessions(handler="/%s/Message" % sessionId, action="POST", json={
            "Text": "Auto Skipping Intro",
            "TimeoutMs": 5000
        })

        sleep(1)
        params = {
            "SeekPositionTicks": end_time_ticks
        }
        client.jellyfin.sessions(handler="/%s/Playing/seek" % sessionId, action="POST", params=params)
        sleep(10)

def monitor_loop():
    global client
    if server_url == '' or server_username == '' or server_password == '':
        print('missing server info')
        return
    
    client = jellyfin_login(server_url, server_username, server_password)
    while client != None:
        monitor_sessions()
        sleep(5)


def receiveSignal(signalNumber, frame):
    global client
    print('Received signal:', signalNumber)
    if signalNumber == signal.SIGINT and client != None:
        jellyfin_logout()
        client = None
    return

if __name__ == "__main__":
    signal.signal(signal.SIGINT, receiveSignal)
    monitor_loop()