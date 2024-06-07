import time
from collections import deque
from src.utils.logger import Logger

class SudokuAlgorithm:
    def __init__(self, sudoku = None, logger: Logger = None, handicap = 1):
        self.grid = sudoku
        self.logger = logger

        self.recent_requests = deque()
        # self.handicap = handicap       # total handicap

        # calculated in runtime
        self.base_delay = 0.01*handicap     # delay applied when the number of requests exceeds the threshold
        self.interval = 10                  # interval to check if the number of requests exceeds the threshold
        self.threshold = 500                  # maximum number of requests allowed in the interval

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += (
                    str(self.grid[i][j])
                    if self.grid[i][j] != 0
                    else f"\033[93m{self.grid[i][j]}\033[0m"
                )
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def checkWithParams(self, sudoku: str):
        self.grid = sudoku
        return self.check()

    def _limit_calls(self):
        """Limit the number of requests made to the Sudoku object."""
        current_time = time.time()
        self.recent_requests.append(current_time)

        num_requests = len(self.recent_requests)

        if num_requests > self.threshold:
            delay = self.base_delay * (num_requests - self.threshold)
            time.sleep(delay)

            self.recent_requests.clear()

    def check_row(self, row):
        """Check if the given row is correct."""
        self._limit_calls()

        # Check row
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False

        return True

    def check_column(self, col):
        """Check if the given row is correct."""
        self._limit_calls()

        # Check col
        if (
            sum([self.grid[row][col] for row in range(9)]) != 45
            or len(set([self.grid[row][col] for row in range(9)])) != 9
        ):
            return False

        return True

    def check_square(self, row, col):
        """Check if the given 3x3 square is correct."""
        self._limit_calls()

        # Check square
        if (
            sum([self.grid[row + i][col + j] for i in range(3) for j in range(3)]) != 45
            or len(
                set([self.grid[row + i][col + j] for i in range(3) for j in range(3)])
            )
            != 9
        ):
            return False

        return True


    def check(self):
        """Check if the given Sudoku solution is correct.
        You MUST incorporate this method without modifications into your final solution.
        """

        for row in range(9):
            if not self.check_row(row):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i * 3, j * 3):
                    return False

        return True

