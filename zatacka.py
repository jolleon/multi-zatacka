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
        gevent.sleep()
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
        gevent.sleep()


class Snake(object):

    def __init__(self):
        self.speed = 2
        self.turn_speed = 0.2
        self.direction = random.random() * 2 * math.pi
        self.x = random.random() * 400
        self.y = random.random() * 400

    def move(self):
        self.x += self.speed * math.cos(self.direction)
        self.y += self.speed * math.sin(self.direction)

        if self.x > 400: self.x = 0
        if self.y > 400: self.y = 0
        if self.x < 0: self.x = 400
        if self.y < 0: self.y = 400

    def turn_right(self):
        self.direction -= self.turn_speed

    def turn_left(self):
        self.direction += self.turn_speed


class Player(object):

    def __init__(self):
        self.score = 0
        self.name = 'guest'
        self.snake = Snake()
        self.has_played = False

    def process(self, message):
        if 'name' in message:
            self.name = message['name']
        if 'command' in message and not self.has_played:
            if message['command'] == 'left':
                snake.turn_left()
            if message['command'] == 'right':
                snake.turn_right()
            self.has_played = True

    def update(self):
        self.snake.move()
        self.has_played = False

    def serialize(self):
        return {'name': self.name, 'x': self.snake.x, 'y': self.snake.y}


class Zatacka(object):

    def __init__(self):
        self.clients = list()
        self.players = list()

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
