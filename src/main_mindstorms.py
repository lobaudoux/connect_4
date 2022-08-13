from mindstorms import ColorSensor, MSHub, Motor
from mindstorms.control import Timer, wait_for_seconds


EMPTY = 0
YELLOW = 1
RED = 2
DRAW = 3
SIZE_X = 7
SIZE_Y = 6
LEFT = -1
RIGHT = 1

TIMEOUT_TURN = 1
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (-1, 1))
SCORES_FOR_LINES = {
    2: 1,
    3: 4,
}

MOVEMENT_SPEED = 20
RELEASE_SPEED = 100
COLUMN_ROTATION = 105


def insort(a, x, lo=0, hi=None):
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x < a[mid]:
            hi = mid
        else:
            lo = mid + 1
    a.insert(lo, x)


class TimeoutError(Exception):
    pass


class Branch:
    def __init__(self, action, node):
        self.action = action
        self.node = node

    def __lt__(self, other):
        return self.node.value > other.node.value  # use '>' to reverse the order and have the highest value at first index


class Node:
    def __init__(self):
        self.value = None
        self.branches = []


class Game:
    def __init__(self):
        self.state = [[EMPTY for _ in range(SIZE_Y)] for _ in range(SIZE_X)]
        self.turn = YELLOW
        self.cur_depths = [SIZE_Y - 1 for _ in range(SIZE_X)]
        self.actions = []
        self.winner = None

    def check_for_win(self):
        for i in range(SIZE_X):
            for j in range(SIZE_Y):
                if self.state[i][j] != EMPTY:
                    for dx, dy in DIRECTIONS:
                        if 0 <= i + 3 * dx < SIZE_X and j + 3 * dy < SIZE_Y and all(self.state[i][j] == self.state[i + k * dx][j + k * dy] for k in range(1, 4)):
                            self.winner = {
                                'color': self.state[i][j],
                                'winning_line': [(i + k * dx, j + k * dy) for k in range(4)]
                            }
                            return
        if all(depth < 0 for depth in self.cur_depths):
            self.winner = DRAW

    def apply_action(self, action):
        if self.cur_depths[action] >= 0:
            self.state[action][self.cur_depths[action]] = self.turn
            self.cur_depths[action] -= 1
            self.check_for_win()
            self.turn = RED if self.turn == YELLOW else YELLOW
            self.actions.append(action)
        else:
            raise ValueError("Invalid action ! Action: {}".format(action))

    def undo_action(self):
        action = self.actions.pop()
        self.state[action][self.cur_depths[action] + 1] = EMPTY
        self.cur_depths[action] += 1
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
        for i in range(SIZE_X):
            for j in range(SIZE_Y):
                if self.game.state[i][j] != EMPTY:
                    for dx, dy in DIRECTIONS:
                        for line_length in (2, 3):
                            if 0 <= i + (line_length - 1) * dx < SIZE_X and j + (line_length - 1) * dy < SIZE_Y and \
                                    all(self.game.state[i][j] == self.game.state[i + k * dx][j + k * dy] for k in range(1, line_length)):
                                max_length = line_length
                                # Search the additional length that could be added in the reverse direction
                                n = -1
                                while 0 <= i + n * dx < SIZE_X and 0 <= j + n * dy < SIZE_Y and self.game.state[i + n * dx][j + n * dy] == EMPTY:
                                    n -= 1
                                    max_length += 1
                                # Now search the additional length that could be added in the original direction
                                n = line_length
                                while 0 <= i + n * dx < SIZE_X and 0 <= j + n * dy < SIZE_Y and self.game.state[i + n * dx][j + n * dy] == EMPTY:
                                    n += 1
                                    max_length += 1
                                if max_length >= 4:
                                    score_for_line = SCORES_FOR_LINES[line_length]
                                    if self.game.state[i][j] == self.color:
                                        score += score_for_line
                                    else:
                                        score -= score_for_line
        return score

    # Minimax with alpha-beta pruning
    def minimax(self, node, prev_tree_node, alpha, beta, depth):
        if timer.now() > TIMEOUT_TURN:
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
            insort(node.branches, Branch(action, new_node))
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
        timer.reset()
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
        self.release_motor = Motor('A')
        self.movement_motor = Motor('C')
        self.left_color = ColorSensor('F')
        self.mid_color = ColorSensor('D')
        self.right_color = ColorSensor('B')
        self.cur_column = 3

    def move(self, n_cols):
        if (n_cols < 0 and self.cur_column > 0) or (n_cols > 0 and self.cur_column < SIZE_X - 1):
            self.cur_column += n_cols
            self.movement_motor.run_for_degrees(n_cols * COLUMN_ROTATION, MOVEMENT_SPEED)

    def apply_action(self, action):
        n_cols = action - self.cur_column
        if n_cols:
            self.move(n_cols)
        self.drop_piece()

    def drop_piece(self):
        self.release_motor.run_to_position(330, speed=RELEASE_SPEED)
        self.release_motor.run_to_position(0, speed=RELEASE_SPEED)


hub = MSHub()
timer = Timer()

game = Game()
ai = AI(game, RED)
robot = Robot()

while game.winner is None:
    hub.light_matrix.write(robot.cur_column)
    if game.turn == YELLOW:
        hub.status_light.on('yellow')
        has_played = False
        while not has_played:
            wait_for_seconds(0.1)
            if robot.left_color.get_color() == 'red':
                robot.move(-1)
            elif robot.right_color.get_color() == 'red':
                robot.move(-1)
            elif robot.mid_color.get_color() == 'red':
                robot.apply_action(robot.cur_column)
                game.apply_action(robot.cur_column)
                has_played = True
    else:
        hub.status_light.on('red')
        ai_action = ai.get_action()
        robot.apply_action(ai_action)
        game.apply_action(ai_action)

if game.winner == DRAW:
    print("Draw !")
else:
    print("Winner is {}".format('yellow' if game.winner['color'] == YELLOW else 'red'))
