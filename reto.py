import time
import datetime
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
plt.rcParams["animation.html"] = "jshtml"
matplotlib.rcParams['animation.embed_limit'] = 2**128

import pandas as pd
import numpy as np

from mesa import Agent
from mesa import Model
from mesa.space import SingleGrid
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector

from threading import Timer

import json

# --------------------------------------------- #
# ------------------- AGENT ------------------- #
# --------------------------------------------- #

class Cars(Agent):
    def __init__(self, uniqueId, model, theChosenOne):
        super().__init__(uniqueId, model)
        self.speed = 4
        self.wantChange = False
        self.preference = np.random.choice([0,2])
        self.locked = theChosenOne
        self.stepStop = 6

    def checkSpeedFront(self, neighbor):
        if neighbor.speed != self.speed and neighbor.speed >= 0 and not self.locked:
            self.speed = neighbor.speed
            if self.pos[0] == 1 and self.speed <= 3:
                self.wantChange = True

    def checkSpeedSide(self, neighbor):
        if neighbor.speed < self.speed and neighbor.speed >= 0:
            if neighbor.pos[0] == 1:
                self.speed = 3

    def stopCar(self):
        if self.stepStop % 2 == 0 and self.stepStop >= 0:
            self.speed -= 1
        if self.stepStop != -1:
            self.stepStop -= 1

    def step(self):
        left = 0
        right = 0
        front = 0
        minfront = 5 * self.model.SPP
        if self.pos != None:
            if self.locked == True:
                if self.pos[1] > 400:
                    self.stopCar()
                if not (self.model.grid.out_of_bounds((self.pos[0], self.pos[1] + self.speed))):
                    self.model.grid.move_agent(self, (self.pos[0], self.pos[1] + self.speed))
            else:
                for neighbor in self.model.grid.iter_neighbors(self.pos, moore = True, include_center = False, radius = 5 * self.model.SPP):
                    x, y = neighbor.pos
                    if ((x == self.pos[0]) and (y <= (self.pos[1] + minfront) and y > self.pos[1])):
                        minfront = y - self.pos[1]
                        self.checkSpeedFront(neighbor)
                        front += 1
                    if ((self.pos[0] == 0 or self.pos[0] == 2) and x == 1 and y >= (self.pos[1] + 1)):
                        self.checkSpeedSide(neighbor)
                    if self.pos[0] == 1 and (x == 0 or x == 2) and (y <= self.pos[1] + 1):
                        if x == 0:
                            left += 1
                        else:
                            right += 1
                if not (self.model.grid.out_of_bounds((self.pos[0], self.pos[1] + self.speed))):
                    if self.wantChange and (left == 0 or right == 0) and (self.pos[0] == 1):
                        if self.preference == 0:
                            if left == 0:
                                self.model.grid.move_agent(self, (0, self.pos[1] + 1))
                            else:
                                self.model.grid.move_agent(self, (2, self.pos[1] + 1))
                        else:
                            if right == 0:
                                self.model.grid.move_agent(self, (2, self.pos[1] + 1))
                            else:
                                self.model.grid.move_agent(self, (0, self.pos[1] + 1))
                        self.speed = 2
                    else:
                        if front == 0:
                            self.speed = 4
                        self.model.grid.move_agent(self, (self.pos[0], self.pos[1] + self.speed))
                else:
                    self.model.grid.remove_agent(self)      

# --------------------------------------------- #
# ----------- GET GRID FOR ANIMATION ---------- #
# --------------------------------------------- #

def getGrid(model):
    grid = np.zeros( (model.grid.width, model.grid.height) )
    for (content, x, y) in model.grid.coord_iter():
        if model.grid.is_cell_empty((x, y)):
            grid[x][y] = 0
        else:
            grid[x][y] = 1
    return grid

# --------------------------------------------- #
# ------------------- MODEL ------------------- #
# --------------------------------------------- #

class Highway(Model):
    def __init__(self, time, timeStop, SPP):
        super().__init__()
        self.time = time
        self.startTime = time
        self.chosenchosen = False
        self.timeStop = timeStop
        self.SPP = SPP

        self.schedule = BaseScheduler(self)
        self.grid = SingleGrid(3, 1000, False)
        self.datacollector = DataCollector(model_reporters={"Grid" : getGrid})

    def step(self):
        if self.time > 0:
            doI = np.random.choice([0,1,2,3,4])
            if doI == 2 or doI == 3 or self.time == self.startTime:
                lane = np.random.choice([0,1,2])
                theChosen = False
                if (self.time <= (self.startTime - self.timeStop)) and lane == 1 and not self.chosenchosen:
                    theChosen = True
                    self.chosenchosen = True
                a = Cars(self.time, self, theChosen)
                self.schedule.add(a)
                self.grid.place_agent(a, (lane, 0))
            self.time -= 1
        self.datacollector.collect(self)
        self.schedule.step()

# --------------------------------------------- #
# ------------- INITIAL VARIABLES ------------- #
# --------------------------------------------- #

MAX_TIME_SECS = 30
STEPS_PER_SECOND = 4
TIME_STOP = 5

# --------------------------------------------- #
# -- INITIALIZATION AND DEVELOPMENT OF MODEL -- #
# --------------------------------------------- #

totalSteps = MAX_TIME_SECS * STEPS_PER_SECOND
last_step_time = 0
fraction = 1 / STEPS_PER_SECOND

model = Highway(totalSteps, (STEPS_PER_SECOND * TIME_STOP), STEPS_PER_SECOND)
# for i in range(totalSteps):
#     timer = Timer(fraction, model.step())
#     print(UNITY_GET(model))

# --------------------------------------------- #
# -------------------- API -------------------- #
# --------------------------------------------- #

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

def UNITY_GET(model):

    varsthingy = {}
    for agent in model.schedule.agent_buffer(False):
        if agent.pos != None:
            lane = agent.pos[0]
        else:
            lane = -1
        varsthingy[agent.unique_id] = {
            "id" : agent.unique_id,
            "speed" : agent.speed,
            "lane" : int(lane)
        }

    jsonOut = json.dumps(varsthingy, sort_keys=True)

    model.step()

    return jsonOut

class Server(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        jsonOut = UNITY_GET(model)
        
        self._set_response()
        
        self.wfile.write(str(jsonOut).encode('utf-8'))
        # self._set_response()
        # self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))
    
    # def do_POST(self):
    #     content_length = int(self.headers['Content-Length'])
    #     #post_data = self.rfile.read(content_length)
    #     post_data = json.loads(self.rfile.read(content_length))
    #     #logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
    #                 #str(self.path), str(self.headers), post_data.decode('utf-8'))
    #     logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
    #                 str(self.path), str(self.headers), json.dumps(post_data))

    #     jsonOut = UNITY_GET(model)
        
    #     self._set_response()

    #     self.wfile.write(str(jsonOut).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info("Starting httpd...\n") # HTTPD is HTTP Daemon!
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:   # CTRL+C stops the server
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")

if __name__ == '__main__':
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

# --------------------------------------------- #
# ----------------- ANIMATION ----------------- #
# --------------------------------------------- #

# allGrid = model.datacollector.get_model_vars_dataframe()
# fig, axs = plt.subplots(figsize = (18, 4))
# axs.set_xticks([])
# axs.set_yticks([])
# patch = plt.imshow(allGrid.iloc[0][0], cmap=plt.cm.binary)

# def animate(i):
#     patch.set_data(allGrid.iloc[i][0])

# anim = animation.FuncAnimation(fig, animate, frames=totalSteps)
# plt.show()