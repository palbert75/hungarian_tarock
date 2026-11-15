#!/usr/bin/env python3
"""Does a running game survive a restart of the server? A live trial.

A player sits down against three bots and plays into the fourth trick. Then
the server is restarted. The trial passes when the player hears the restart
notice, is put back at the same seat without doing anything, sees exactly the
same table, and the hand can be played to its end.

    tools/restart_trial.py                 a server started from this folder (port 8011)
    tools/restart_trial.py image NAME      the Docker image NAME with a data volume, as on the cluster
    tools/restart_trial.py prod            the live server: THIS RESTARTS IT (rollout restart)

Needs the socket client, which the server itself does not use:
    pip install "python-socketio[client]"
Run it with a Python that has it; the server is started with server/.venv.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

import socketio

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODE = sys.argv[1] if len(sys.argv) > 1 else 'local'
IMAGE = sys.argv[2] if MODE == 'image' and len(sys.argv) > 2 else None
if MODE not in ('local', 'image', 'prod') or (MODE == 'image' and not IMAGE):
    raise SystemExit(__doc__)

PORT = '8011'
URL = 'https://tarokk.onbased.cloud' if MODE == 'prod' else 'http://127.0.0.1:' + PORT
KUBECTL = ['kubectl', '--context', os.environ.get('KUBE_CONTEXT', 'do-ams3-general'), '-n', 'tarokk']
RUN_DIR = tempfile.mkdtemp(prefix='tarokk-trial-')
PLAYER = 'Proba'


class Local:
    """The server as a process of its own, with its data in a temporary folder."""

    def __init__(self):
        env = dict(os.environ, DEBUG='false', PORT=PORT, PYTHONPATH=SERVER_DIR, LOG_LEVEL='INFO')
        log = open(os.path.join(RUN_DIR, 'server.log'), 'a')
        self.process = subprocess.Popen([os.path.join(SERVER_DIR, '.venv', 'bin', 'python'), '-m', 'main'],
                                        cwd=RUN_DIR, env=env, stdout=log, stderr=subprocess.STDOUT)
        time.sleep(2.5)

    def stop(self):
        self.process.send_signal(signal.SIGTERM)
        self.process.wait(timeout=30)


class Container:
    """The image with a named volume for /app/data."""
    VOLUME = 'tarokk-trial-data'

    def __init__(self):
        self.cid = subprocess.check_output(
            ['docker', 'run', '-d', '-p', PORT + ':8000', '-e', 'DEBUG=false', '-v', self.VOLUME + ':/app/data',
             IMAGE]).decode().strip()
        time.sleep(8)

    def stop(self):
        # docker stop sends SIGTERM and waits, like the cluster does
        subprocess.run(['docker', 'stop', '-t', '30', self.cid], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['docker', 'rm', '-f', self.cid], stdout=subprocess.DEVNULL)


class Prod:
    """The live server; a restart is a rollout restart of the deployment, which brings up the new pod itself."""

    def stop(self):
        subprocess.run(KUBECTL + ['rollout', 'restart', 'deploy/app'], check=True, stdout=subprocess.DEVNULL)
        end = time.time() + 120
        while sio.connected and time.time() < end:  # until the old server has closed our connection
            time.sleep(0.1)


def start_server():
    return {'local': Local, 'image': Container, 'prod': Prod}[MODE]()


seen = {'state': None, 'joined': None, 'turn': None, 'notice': 0, 'connects': 0, 'errors': []}
sio = socketio.Client(reconnection=True, reconnection_delay=0.5, reconnection_delay_max=1)


@sio.event
def connect():
    seen['connects'] += 1
    if seen['joined']:
        # What the app does when the connection is back: return to the table it remembers
        sio.emit('join_room', {'room_id': seen['joined']['room_id'], 'player_name': PLAYER,
                               'player_id': seen['joined']['player_id']})


sio.on('joined', lambda data: seen.update(joined=data))
sio.on('game_state', lambda data: seen.update(state=data) if 'phase' in data else None)
sio.on('your_turn', lambda data: seen.update(turn=data))
sio.on('server_restarting', lambda data: seen.update(notice=seen['notice'] + 1))
sio.on('error', lambda data: seen['errors'].append(data))


def wait(condition, what, seconds=30):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return
        time.sleep(0.1)
    raise SystemExit('FAILED: no ' + what + ' within %d s; errors: %s' % (seconds, json.dumps(seen['errors'])[:400]))


def my_move():
    """When it is our turn, act the simplest legal way."""
    turn, seen['turn'] = seen['turn'], None
    if not turn:
        return
    data = turn.get('data', turn)
    hint = data.get('hint') or {}
    actions = data.get('valid_actions') or []
    if 'place_bid' in actions:
        sio.emit('place_bid', {'bid_type': 'pass' if 'pass' in data['valid_bids'] else data['valid_bids'][0]})
    elif 'discard_cards' in actions:
        sio.emit('discard_cards', {'card_ids': hint['payload']['card_ids']})
    elif 'call_partner' in actions:
        sio.emit('call_partner', hint['payload'])
    elif 'make_announcement' in actions:
        sio.emit('pass_announcement', {})
    elif 'play_card' in actions:
        sio.emit('play_card', {'card_id': data['valid_cards'][0]})


def table(state):
    """The table without who is connected, which a restart changes for a moment."""
    keep = json.loads(json.dumps(state))
    for p in keep.get('players', []):
        p.pop('is_connected', None)
    return keep


def main():
    if MODE == 'image':
        subprocess.run(['docker', 'volume', 'rm', Container.VOLUME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server = start_server()
    failed = []
    try:
        sio.connect(URL, transports=['websocket'])
        sio.emit('create_room', {'player_name': PLAYER})
        wait(lambda: seen['joined'], 'seat')
        sio.emit('set_bot_speed', {'speed': 'fast'})
        sio.emit('fill_bots', {})
        sio.emit('ready', {})
        wait(lambda: seen['state'], 'deal')

        # Into the fourth trick, then stop at our own turn: the table stands still while we "think"
        end = time.time() + 120
        while not (seen['state']['phase'] == 'playing' and seen['state'].get('trick_number', 0) >= 4 and seen['turn']):
            if seen['state']['phase'] == 'game_end':
                # Everybody passed or the hand ran out: deal again
                seen['state']['phase'] = 'waiting'
                sio.emit('next_hand', {})
            if time.time() > end:
                raise SystemExit('FAILED: the fourth trick was never reached')
            my_move()
            time.sleep(0.15)
        time.sleep(1.0)
        before = table(seen['state'])
        print('before the restart: trick %s, our turn' % before.get('trick_number'))

        seen['state'] = seen['turn'] = None
        connects, started = seen['connects'], time.time()
        server.stop()
        if MODE != 'prod':
            server = start_server()
        wait(lambda: seen['connects'] > connects and seen['state'], 'table after the restart', 180)
        print('back at the table %.1f s after the restart began' % (time.time() - started))

        after = table(seen['state'])
        if not seen['notice']:
            failed.append('the restart notice was not heard')
        if after != before:
            failed.append('the table differs: ' + ', '.join(k for k in sorted(set(before) | set(after))
                                                         if before.get(k) != after.get(k)))
        wait(lambda: seen['turn'], 'turn offered again', 15)

        end = time.time() + 150
        while time.time() < end and seen['state']['phase'] != 'game_end':
            my_move()
            time.sleep(0.15)
        if seen['state']['phase'] != 'game_end':
            failed.append('the hand did not finish after the restart')
        if seen['errors']:
            failed.append('errors from the server: ' + json.dumps(seen['errors'])[:300])
        sio.emit('leave_room', {})
        time.sleep(1)
    finally:
        if sio.connected:
            sio.disconnect()
        if MODE != 'prod':
            server.stop()
        if MODE == 'image':
            subprocess.run(['docker', 'volume', 'rm', Container.VOLUME], stdout=subprocess.DEVNULL)

    if failed:
        raise SystemExit('FAILED: ' + '; '.join(failed))
    print('PASSED: notice heard, same table, hand played to its end')


if __name__ == '__main__':
    main()
