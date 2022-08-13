import bisect
import time

from constants import *
from gui import GUI

import pygame

TIMEOUT_TURN = 2
DIRECTIONS = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, -1), (1, 0), (1, 1))
SCORES_FOR_LINES = {
    2: 1,
    3: 4,
}


class Line:
    def __init__(self, points, direction):
        self.pieces = sorted(points)
        self.direction = direction

    def add(self, piece):
        bisect.insort(self.pieces, piece)

    def index(self, piece):
        return bisect.bisect_left(self.pieces, piece)

    @staticmethod
    def normalize_direction(dx, dy):
        if dx < 0:
            dx, dy = -dx, -dy
        elif dx == 0:
            dx, dy = dx, abs(dy)
        return dx, dy


class Branch:
    def __init__(self, action, node):
        self.action = action
        self.node = node

    def __lt__(self, other):
        return self.node.value > other.node.value  # Use '>' to reverse the order and have the highest value at first index


class Node:
    def __init__(self):
        self.value = None
        self.branches = []


class Game:
    def __init__(self):
        self.state = [[EMPTY for _ in range(SIZE_Y)] for _ in range(SIZE_X)]
        self.lines = [[{} for _ in range(SIZE_Y)] for _ in range(SIZE_X)]
        self.turn = YELLOW
        self.cur_depths = [SIZE_Y - 1 for _ in range(SIZE_X)]
        self.actions = []
        self.winner = None

    def apply_action(self, action):
        if self.cur_depths[action] < 0:
            raise ValueError(f"Invalid action ! Action:  {action}")

        x, y = action, self.cur_depths[action]
        self.state[x][y] = self.turn
        self.cur_depths[action] -= 1
        self.actions.append(action)

        # Update the lines state
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy  # The neighbour coordinates
            if 0 <= nx < SIZE_X and 0 <= ny < SIZE_Y and self.state[nx][ny] == self.turn:
                direction = Line.normalize_direction(dx, dy)
                if direction in self.lines[x][y]:
                    if direction in self.lines[nx][ny]:
                        for piece in self.lines[nx][ny][direction].pieces:
                            self.lines[x][y][direction].add(piece)
                            self.lines[piece[0]][piece[1]][direction] = self.lines[x][y][direction]
                    else:
                        self.lines[x][y][direction].add((nx, ny))
                        self.lines[nx][ny][direction] = self.lines[x][y][direction]
                else:
                    if direction in self.lines[nx][ny]:
                        self.lines[nx][ny][direction].add((x, y))
                    else:
                        self.lines[nx][ny][direction] = Line(((x, y), (nx, ny)), direction)
                    self.lines[x][y][direction] = self.lines[nx][ny][direction]

        # Check for win
        for line in self.lines[x][y].values():
            if len(line.pieces) >= 4:
                self.winner = {
                    'color': self.turn,
                    'winning_line': sorted(list(line.pieces)),
                }

        # Check for a draw
        if all(depth < 0 for depth in self.cur_depths):
            self.winner = DRAW

        self.turn = RED if self.turn == YELLOW else YELLOW

    def undo_action(self):
        action = self.actions.pop()
        x, y = action, self.cur_depths[action] + 1
        self.state[x][y] = EMPTY
        self.cur_depths[action] += 1

        # Revert the lines state
        for line in self.lines[x][y].values():
            index = line.index((x, y))
            left_side_pieces = line.pieces[:index]
            right_side_pieces = line.pieces[index + 1:]
            for pieces in (left_side_pieces, right_side_pieces):
                if len(pieces) == 1:
                    px, py = pieces[0]
                    del self.lines[px][py][line.direction]
                elif len(pieces) >= 2:
                    new_line = Line(pieces, line.direction)
                    for px, py in pieces:
                        self.lines[px][py][line.direction] = new_line
        self.lines[x][y] = {}

        self.turn = RED if self.turn == YELLOW else YELLOW
        self.winner = None

    def successors(self):
        return set(i for i in range(SIZE_X) if self.cur_depths[i] >= 0)

    def __hash__(self):
        return hash(tuple(tuple(column) for column in self.state))


class AI:
    def __init__(self, game, color):
        self.game = game
        self.color = color
        self.action = 0, None
        self.nodes_explored = 0
        self.max_depth = 1
        self.turn_start_timestamp = 0
        self.transposition_table = {}
        self.prev_tree = None

    def cutoff(self, depth):
        return depth == self.max_depth or self.game.winner

    def evaluate(self, depth):
        if self.game.winner:
            if self.game.winner == DRAW:
                return 0
            else:
                return 1000 - depth if self.game.winner['color'] == self.color else -1000 + depth
        score = 0
        my_lines = {}
        enemy_lines = {}
        for i in range(SIZE_X):
            for j in range(SIZE_Y):
                if self.game.state[i][j] != EMPTY:
                    if self.game.state[i][j] == self.color:
                        for line in self.game.lines[i][j].values():
                            my_lines[id(line)] = line
                    else:
                        for line in self.game.lines[i][j].values():
                            enemy_lines[id(line)] = line
        for line in my_lines.values():
            score += SCORES_FOR_LINES[len(line.pieces)]
        for line in enemy_lines.values():
            score -= SCORES_FOR_LINES[len(line.pieces)]
        return score

    # Minimax with alpha-beta pruning
    def minimax(self, node, prev_tree_node, alpha, beta, depth):
        if time.time() - self.turn_start_timestamp > TIMEOUT_TURN:
            for _ in range(depth):
                self.game.undo_action()
            raise TimeoutError
        self.nodes_explored += 1
        hashed_board = hash(self.game)
        if hashed_board in self.transposition_table:
            return self.transposition_table[hashed_board]
        if self.cutoff(depth):
            evaluation = self.evaluate(depth)
            return evaluation, None
        best_action = None
        maximizing = depth % 2 == 0
        val = -100000 if maximizing else 100000
        next_actions = self.game.successors()
        if prev_tree_node:
            branches = prev_tree_node.branches
            for branch in branches:
                next_actions.remove(branch.action)
        else:
            branches = []
        branches.extend(Branch(action, None) for action in next_actions)
        for branch in branches:
            action = branch.action
            self.game.apply_action(action)
            new_node = Node()
            v, _ = self.minimax(new_node, branch.node, alpha, beta, depth + 1)
            new_node.value = v
            bisect.insort(node.branches, Branch(action, new_node))
            self.game.undo_action()
            if maximizing:
                if v > val:
                    val = v
                    best_action = action
                    if v >= beta:
                        return v, action
                    alpha = max(alpha, v)
            else:
                if v < val:
                    val = v
                    best_action = action
                    if v <= alpha:
                        return v, action
                    beta = min(beta, v)
        self.transposition_table[hashed_board] = (val, best_action)
        return val, best_action

    def get_action(self):
        self.turn_start_timestamp = time.time()
        self.nodes_explored = 0
        self.max_depth = 1
        self.prev_tree = None
        try:
            while self.max_depth <= sum(self.game.cur_depths) + 7:  # max_depth shouldn't exceed the number of empty cells left
                self.transposition_table = {}
                new_tree = Node()
                self.action = self.minimax(new_tree, self.prev_tree, -100000, 100000, 0)
                self.prev_tree = new_tree
                self.max_depth += 1
        except TimeoutError:
            pass
        return self.action[1]


class Robot:
    def __init__(self):
        self.cur_column = 3

    def move(self, n_cols):
        if (n_cols < 0 and self.cur_column > 0) or (n_cols > 0 and self.cur_column < SIZE_X - 1):
            self.cur_column += n_cols

    def apply_action(self, action):
        n_cols = action - self.cur_column
        if n_cols:
            self.move(n_cols)


def main():
    game = Game()
    ai = AI(game, RED)
    robot = Robot()
    gui = GUI(game, robot, ai)

    gui.draw()
    while True:
        pygame.time.Clock().tick(60)
        if game.winner is None:
            if game.turn == YELLOW:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        exit(0)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_LEFT:
                            robot.move(-1)
                        elif event.key == pygame.K_RIGHT:
                            robot.move(1)
                        elif event.key == pygame.K_DOWN:
                            try:
                                game.apply_action(robot.cur_column)
                            except ValueError:
                                pass
                        elif event.key == pygame.K_UP:
                            print(f"game.state = {game.state}")
                            print(f"game.turn = {game.turn}")
                            print(f"game.actions = {game.actions}")
                            print(f"game.cur_depths = {game.cur_depths}")
                        elif event.key == pygame.K_BACKSPACE:
                            game.undo_action()
                            game.undo_action()
                        gui.draw()
            else:
                ai_action = ai.get_action()
                game.apply_action(ai_action)
                gui.draw()
        else:
            if game.winner == DRAW:
                print("Draw !")
            else:
                print(f"Winner is {'yellow' if game.winner['color'] == YELLOW else 'red'}")
                gui.draw_winner_line(game.winner)
            wait_for_close = True
            while wait_for_close:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        exit(0)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_BACKSPACE:
                            wait_for_close = False
                            game.undo_action()
                            game.undo_action()
                            gui.draw()


if __name__ == '__main__':
    main()
