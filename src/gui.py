import os

import pygame

from constants import *


CELL_PIXEL = 128
CIRCLE_RADIUS_PIXEL = int(0.4 * CELL_PIXEL)
TOP_EMPTY_SPACE_PIXEL = CELL_PIXEL
RIGHT_PANEL_PIXEL = CELL_PIXEL * 3
SIZE_X_PIXEL = SIZE_X * CELL_PIXEL
SIZE_Y_PIXEL = SIZE_Y * CELL_PIXEL

BLACK_COLOR = (0, 0, 0)
BLUE_COLOR = (40, 40, 200)
RED_COLOR = (200, 0, 0)
YELLOW_COLOR = (240, 240, 10)
BACKGROUND_COLOR = (240, 240, 240)


class GUI:
    def __init__(self, game, robot, ai):
        pygame.init()
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        self.display = pygame.display.set_mode((SIZE_X_PIXEL + RIGHT_PANEL_PIXEL, TOP_EMPTY_SPACE_PIXEL + SIZE_Y_PIXEL))
        pygame.display.set_caption("Puissance 4")
        self.text_font = pygame.font.Font('freesansbold.ttf', int(0.2 * CELL_PIXEL))

        self.game = game
        self.robot = robot
        self.ai = ai

    def draw(self):
        self.display.fill(BACKGROUND_COLOR)
        pygame.draw.rect(self.display, BLUE_COLOR, (0, TOP_EMPTY_SPACE_PIXEL, SIZE_X_PIXEL, SIZE_Y_PIXEL))
        if self.game.turn == YELLOW:
            pygame.draw.circle(self.display,
                               YELLOW_COLOR,
                               (self.robot.cur_column * CELL_PIXEL + CELL_PIXEL // 2, CELL_PIXEL // 2),
                               CIRCLE_RADIUS_PIXEL)
        for i in range(SIZE_X):
            for j in range(SIZE_Y):
                pygame.draw.circle(self.display,
                                   RED_COLOR if self.game.state[i][j] == RED else YELLOW_COLOR if self.game.state[i][j] == YELLOW else BACKGROUND_COLOR,
                                   (i * CELL_PIXEL + CELL_PIXEL // 2, TOP_EMPTY_SPACE_PIXEL + j * CELL_PIXEL + CELL_PIXEL // 2),
                                   CIRCLE_RADIUS_PIXEL)
        if self.game.actions:
            x, y = self.game.actions[-1], self.game.cur_depths[self.game.actions[-1]] + 1
            pygame.draw.circle(self.display,
                               BLACK_COLOR,
                               (x * CELL_PIXEL + CELL_PIXEL // 2, TOP_EMPTY_SPACE_PIXEL + y * CELL_PIXEL + CELL_PIXEL // 2),
                               int(CIRCLE_RADIUS_PIXEL * 1.25),
                               CIRCLE_RADIUS_PIXEL // 10)

        texts_to_draw = ("LAST AI ACTION",
                         "  SCORE: {}".format(self.ai.action[0]),
                         "  NODES EXPLORED: {}".format(self.ai.nodes_explored),
                         "  DEPTH: {}".format(self.ai.max_depth - 1),
                         "CURRENT EVALUATION: {}".format(self.ai.evaluate(0)))
        for i, text in enumerate(texts_to_draw):
            text_surface = self.text_font.render(text, True, BLACK_COLOR)
            self.display.blit(text_surface, (SIZE_X_PIXEL + 0.1 * CELL_PIXEL, TOP_EMPTY_SPACE_PIXEL + 0.25 * i * CELL_PIXEL))

        pygame.display.update()

    def draw_winner_line(self, winner):
        pygame.draw.line(self.display,
                         BLACK_COLOR,
                         (winner['winning_line'][0][0] * CELL_PIXEL + CELL_PIXEL // 2, TOP_EMPTY_SPACE_PIXEL + winner['winning_line'][0][1] * CELL_PIXEL + CELL_PIXEL // 2),
                         (winner['winning_line'][3][0] * CELL_PIXEL + CELL_PIXEL // 2, TOP_EMPTY_SPACE_PIXEL + winner['winning_line'][3][1] * CELL_PIXEL + CELL_PIXEL // 2),
                         width=8)
        pygame.display.update()

