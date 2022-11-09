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

class Cars(Agent):
    def __init__(self, uniqueId, model):
        super().__init__(uniqueId, model)
        self.speed = 4
        self.wantChange = True
        self.preference = np.random.choice([0,2])
        # OTHER ATTRIBBUTES #

    def checkSpeedFront(self, neighbor):
        if neighbor.speed != self.speed and neighbor.speed >= 0:
            self.speed = neighbor.speed
            if self.pos[0] == 1 and self.speed <= 3:
                self.wantChange = True

    def checkSpeedSide(self, neighbor):
        if neighbor.speed < self.speed and neighbor.speed >= 0:
            if neighbor.pos[0] == 1:
                self.speed = 3

    def step(self):
        left = 0
        right = 0
        minfront = 5
        if self.pos != None:
            for neighbor in self.model.grid.iter_neighbors(self.pos, moore = True, include_center = False, radius = 5):
                x, y = neighbor.pos
                if (x == self.pos[0] and (y <= (self.pos[1] + minfront) and y > self.pos[1])):
                    minfront = y - self.pos[1]
                    self.checkSpeedFront(neighbor)
                if ((self.pos[0] == 0 or self.pos[0] == 2) and x == 1 and y >= (self.pos[1] + 1)):
                    self.checkSpeedSide(neighbor)
                if self.wantChange:
                    if (x == 0 or x == 2) and (y <= self.pos[1] + 1):
                        if x == 0:
                            left += 1
                        else:
                            right += 1

            if not (self.model.grid.out_of_bounds((self.pos[0], self.pos[1] + self.speed))):
                if self.wantChange and (left == 0 or right == 0) and (self.pos[0] == 1) and (self.pos[1] > 20):
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
                else:
                    self.model.grid.move_agent(self, (self.pos[0], self.pos[1] + self.speed))
            else:
                self.model.grid.remove_agent(self)

def getGrid(model):
    grid = np.zeros( (model.grid.width, model.grid.height) )
    for (content, x, y) in model.grid.coord_iter():
        if model.grid.is_cell_empty((x, y)):
            grid[x][y] = 0
        else:
            grid[x][y] = 1
    return grid

class Highway(Model):
    def __init__(self, numAgents):
        super().__init__()
        self.numAgents = numAgents
        self.schedule = BaseScheduler(self)
        self.grid = SingleGrid(3, 300, False)
        self.datacollector = DataCollector(model_reporters={"Grid" : getGrid})

    def step(self):
        if self.numAgents > 0:
            doI = np.random.choice([0,1,2,3,4])
            if doI == 2 or doI == 3:
                lane = np.random.choice([0,1,2])
                a = Cars(self.numAgents, self)
                self.schedule.add(a)
                self.grid.place_agent(a, (lane, 0))
                self.numAgents -= 1
        self.datacollector.collect(self)
        self.schedule.step()

numAgents = 50
model = Highway(numAgents)
MAX_ITER = 100
for i in range(MAX_ITER):
    model.step()

allGrid = model.datacollector.get_model_vars_dataframe()
fig, axs = plt.subplots(figsize = (18, 4))
axs.set_xticks([])
axs.set_yticks([])
patch = plt.imshow(allGrid.iloc[0][0], cmap=plt.cm.binary)

def animate(i):
    patch.set_data(allGrid.iloc[i][0])

anim = animation.FuncAnimation(fig, animate, frames=MAX_ITER)
plt.show()