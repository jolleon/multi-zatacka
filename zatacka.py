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


nSnakes = 0
# TODO: needs lock?
def get_id():
    nSnakes += 1
    return nSnakes


class Snake(object):

    def __init__(self):
        self.id = get_id()
        self.speed = 2
        self.turn_speed = 0.1
        self.radius = 2
        self.direction = random.random() * 2 * math.pi
        self.x = random.random() * 400
        self.y = random.random() * 400
        self.old_x = self.x
        self.old_y = self.y

    def move(self):
        self.old_x = self.x
        self.old_y = self.y
        self.x += self.speed * math.cos(self.direction)
        self.y -= self.speed * math.sin(self.direction)

        if self.x > 400: self.x = 0
        if self.y > 400: self.y = 0
        if self.x < 0: self.x = 400
        if self.y < 0: self.y = 400

    def turn_right(self):
        self.direction -= self.turn_speed

    def turn_left(self):
        self.direction += self.turn_speed

    def udpate_grid(self, grid):
        dx = self.x - self.old_x
        dy = self.y - self.old_y
        length = max(dx, dy)
        for i in xrange(length):
            x = self.old_x + i/length * dx
            y = self.old_y + i/length * dy
            for w in xrange(2 * self.radius):
                for h in xrange(2 * self.radius):
                    xx = round(x - self.radius + w)
                    yy = round(y - self.radius + h)
                    grid[xx][yy] = self.id


COLORS = ['#f00', '#0f0', '#00f', '#ff0', '#f0f', '#0ff']

class Player(object):

    def __init__(self):
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
        if self.command == 'left':
            self.snake.turn_left()
        if self.command == 'right':
            self.snake.turn_right()
        self.snake.move()
        self.snake.update_grid(grid)

    def serialize(self):
        return {'name': self.name, 'x': self.snake.x, 'y': self.snake.y, 'color': self.color}


class Zatacka(object):

    def __init__(self):
        self.clients = list()
        self.players = list()
        self.grid = self.empty_grid(800, 600)

    def empty_grid(self, w, h):
        return [[False] * h for _ in xrange(w)]

    def register_observer(self, socket):
        self.clients.append(socket)

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
            self.frame += 1
            for player in self.players:
                player.update()

            data = list()
            for player in self.players:
                data.append(player.serialize())

            for client in self.clients:
                self.send(client, data)

            next_frame_time = self.start_time + self.frame * self.frame_time
            sleep_time = max(0, next_frame_time - time.time())
            gevent.sleep(sleep_time)


    def start(self):
        self.start_time = time.time()
        self.frame_time = 0.01
        self.frame = 0
        gevent.spawn(self.run)


zatacka = Zatacka()
zatacka.start()
