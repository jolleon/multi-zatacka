import copy
import os
import time
import logging
import json
import gevent
from flask import Flask, render_template
from flask_sockets import Sockets


import math
import random


app = Flask(__name__)
app.debug = True #'DEBUG' in os.environ

sockets = Sockets(app)



@app.route('/')
def index():
    return render_template('index.html')


@sockets.route('/submit')
def submit(ws):
    player = Player()
    zatacka.register_player(player)
    while ws.socket is not None:
        gevent.sleep(0.01)
        message = ws.receive()

        if message:
            app.logger.info('received: {}'.format(message))
            player.process(message)
    zatacka.remove_player(player)


@sockets.route('/receive')
def receive(ws):
    # register ws
    zatacka.register_observer(ws)

    while ws.socket is not None:
        gevent.sleep(0.01)


class Grid(object):

    def __init__(self, width, height, wrap=True):
        self.width = width
        self.height = height
        self.wrap = wrap
        self.grid = self.empty_grid(width, height)

    def empty_grid(self, w, h):
        return [[0] * h for _ in xrange(w)]

    def get(self, x, y):
        if self.wrap:
            if not 0 <= x < self.width:
                x = x % self.width
            if not 0 <= y < self.height:
                y = y % self.height

        return self.grid[x][y]

    def set(self, x, y, v):
        if self.wrap:
            if not 0 <= x < self.width:
                x = x % self.width
            if not 0 <= y < self.height:
                y = y % self.height

        self.grid[x][y] = v


nSnakes = 0
# TODO: needs lock?
def get_id():
    global nSnakes
    nSnakes += 1
    return nSnakes


class Snake(object):

    def __init__(self):
        self.id = get_id()
        self.speed = 2
        self.turn_speed = 0.05
        self.radius = 2
        self.direction = random.random() * 2 * math.pi
        self.x = random.random() * 400
        self.y = random.random() * 400
        self.old_x = self.x
        self.old_y = self.y

    def move(self, width, height):
        self.old_x = self.x
        self.old_y = self.y
        self.x += self.speed * math.cos(self.direction)
        self.y -= self.speed * math.sin(self.direction)

        if self.x > width: self.x = 0
        if self.y > height: self.y = 0
        if self.x < 0: self.x = width
        if self.y < 0: self.y = height

    def turn_right(self):
        self.direction -= self.turn_speed

    def turn_left(self):
        self.direction += self.turn_speed

    def update_grid(self, grid):
        dx = self.x - self.old_x
        dy = self.y - self.old_y
        #x = self.old_x + i/length * dx
        #y = self.old_y + i/length * dy
        x = self.old_x
        y = self.old_y
        for w in xrange(2 * self.radius):
            for h in xrange(2 * self.radius):
                xx = int(round(x - self.radius + w))
                yy = int(round(y - self.radius + h))
                grid.set(xx, yy, self.id)

    def collision(self, grid):
        sensors_x = [int(round(
            self.x + self.radius * math.cos(self.direction + math.pi * i / 6)))
            for i in xrange(-2, 3)]
        sensors_y = [int(round(
            self.y - self.radius * math.sin(self.direction + math.pi * i / 6)))
            for i in xrange(-2, 3)]

        if any(grid.get(x, y) for (x, y) in zip(sensors_x, sensors_y)):
            s = ''
            xx = (min(sensors_x) - 10, max(sensors_x) + 10)
            yy = (min(sensors_y) - 10, max(sensors_y) + 10)
            s += 'id: %d\n' % self.id
            s += 'xx: %s, yy: %s\n' % (xx, yy)
            s += 'x, y: %d, %d   old: %d, %d\n' % (self.x, self.y, self.old_x, self.old_y)
            for y in range(*yy):
                s += ''.join(
                    '%d%s' % (grid.get(x, y),
                        '*' if x == int(self.x) and y == int(self.y)
                        else 'X' if x == int(self.old_x) and y == int(self.old_y)
                        else '!' if (x, y) in zip(sensors_x, sensors_y)
                        else ' ')
                    for x in range(*xx)
                )
                s += '\n'
            app.logger.info(s)
            return True


COLORS = ['#f00', '#0f0', '#00f', '#ff0', '#f0f', '#0ff']

class Player(object):

    def __init__(self):
        self.id = get_id()
        self.alive = True
        self.score = 0
        self.name = 'guest'
        self.snake = Snake()
        self.command = None
        self.color = COLORS[random.randint(0, len(COLORS)-1)]

    def process(self, message):
        message = json.loads(message)
        if 'name' in message:
            self.name = message['name']
        if 'command' in message:
            if message['command'] in ('left', 'right', 'straight'):
                self.command = message['command']

    def update(self, grid):
        if not self.alive:
            return
        if self.command == 'left':
            self.snake.turn_left()
        if self.command == 'right':
            self.snake.turn_right()
        self.snake.move(grid.width, grid.height)
        if self.snake.collision(grid):
            self.alive = False
        self.snake.update_grid(grid)

    def serialize(self):
        return {'name': self.name, 'x': self.snake.x, 'y': self.snake.y, 'color': self.color}


class Zatacka(object):

    def __init__(self):
        self.clients = list()
        self.players = list()
        self.game_history = []
        self.width = 800
        self.height = 600


    def register_observer(self, socket):
        self.clients.append(socket)
        self.send_size(socket)
        self.broadcast_players()
        for step in self.game_history:
            self.send_frame(socket, step)

    def broadcast_players(self):
        for client in self.clients:
            self.send_scores(client)

    def send_frame(self, client, data):
        self.send(client, {'type': 'step', 'content': data})

    def send_scores(self, client):
        players = [{
            'id': player.id,
            'name': player.name,
            'score': player.score,
            'color': player.color,
            } for player in self.players]
        self.send(client, {'type': 'players', 'content': players})

    def send_size(self, client):
        self.send(client, {'type': 'size', 'width': self.width, 'height': self.height})

    def register_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        self.players.remove(player)

    def send(self, client, data):
        try:
            data = json.dumps(data)
            client.send(data)
        except Exception:
            self.clients.remove(client)

    def run(self):
        while True:
            app.logger.info('creating new game')
            self.grid = Grid(self.width, self.height)
            self.game_history = []
            self.start_time = time.time()
            self.frame_time = 0.0133
            self.frame = 0

            for client in self.clients:
                self.send_size(client)

            for client in self.clients:
                self.send(client, {'type': 'restart'})

            self.broadcast_players()
            for player in self.players:
                player.alive = True

            alive_players = copy.copy(self.players)

            while len(alive_players) > 0:
                self.frame += 1
                for player in alive_players:
                    player.update(self.grid)

                data = list()
                for player in alive_players:
                    data.append(player.serialize())

                self.game_history.append(data)

                # remove dead players only after broadcasting their last state
                someone_died = False
                for player in alive_players:
                    if not player.alive:
                        someone_died = True
                        alive_players.remove(player)

                if someone_died:
                    app.logger.info('someone died')
                    for player in alive_players:
                        player.score += 1

                for client in self.clients:
                    self.send_frame(client, data)
                    if someone_died:
                        self.send_scores(client)

                next_frame_time = self.start_time + self.frame * self.frame_time
                sleep_time = max(0, next_frame_time - time.time())
                gevent.sleep(sleep_time)

            gevent.sleep(3)



    def start(self):
        gevent.spawn(self.run)


zatacka = Zatacka()
zatacka.start()
