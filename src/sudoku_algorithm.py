import time
from collections import deque
from src.utils.logger import Logger

class SudokuAlgorithm:
    def __init__(self, sudoku = None, logger = Logger, handicap = 0):
        self.grid = sudoku
        self.logger = logger

        self.recent_requests = deque()
        self.handicap = handicap       # total handicap

        # calculated in runtime
        self.base_delay = 0  # delay applied when the number of requests exceeds the threshold
        self.interval = 0      # interval to check if the number of requests exceeds the threshold
        self.threshold = 0      # maximum number of requests allowed in the interval

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
        # if self.handicap > 0:
        #     self.calculate_delay_params()
        #     self.logger.critical(f"Handicap: {self.handicap}, Base delay: {self.base_delay}, Interval: {self.interval}, Threshold: {self.threshold}")
        self.grid = sudoku
        # self.logger.warning(f"Parameters: {self.base_delay}, {self.interval}, {self.threshold}")
        # self.logger.warning("Len requests: " + str(len(self.recent_requests)))
        self.recent_requests = deque()
        return self.check()

    def calculate_delay_params(self):
        # Define arbitrary proportions for interval and threshold

        # Convert handicap from milliseconds to seconds
        handicap_seconds = self.handicap / 1000.0

        # Calculate base_delay: total handicap divided by the number of calls exceeding the threshold
        # Ensure we only apply base_delay if num_requests exceeds threshold
        
        current_time = time.time()
        self.recent_requests.append(current_time)
        
        # number of requests made in the last interval
        num_requests = len(
            [t for t in self.recent_requests if current_time - t < self.interval]
        )
        
        # If the number of requests exceeds the threshold, the delay increases
        if num_requests > self.threshold:
            self.base_delay = handicap_seconds / (num_requests - self.threshold) # the delay is applied proportionally based on the excess number of requests.
    

    
    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        """Limit the number of requests made to the Sudoku object."""
        if base_delay is None:
            base_delay = self.base_delay
        if interval is None:
            interval = self.interval
        if threshold is None:
            threshold = self.threshold

        current_time = time.time()
        self.recent_requests.append(current_time)
        
        # number of requests made in the last interval
        num_requests = len(
            [t for t in self.recent_requests if current_time - t < interval]
        )

        # If the number of requests exceeds the threshold, the delay increases linearly
        if num_requests > threshold:
            delay = base_delay * (num_requests - threshold + 1)
            # self.logger.warning(f"Delay: {delay}")
            time.sleep(delay)

    def check_row(self, row, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False

        return True

    def check_column(self, col, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check col
        if (
            sum([self.grid[row][col] for row in range(9)]) != 45
            or len(set([self.grid[row][col] for row in range(9)])) != 9
        ):
            return False

        return True

    def check_square(self, row, col, base_delay=None, interval=None, threshold=None):
        """Check if the given 3x3 square is correct."""
        self._limit_calls(base_delay, interval, threshold)

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


    def check(self, base_delay=None, interval=None, threshold=None):
        """Check if the given Sudoku solution is correct.
        You MUST incorporate this method without modifications into your final solution.
        """

        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i * 3, j * 3, base_delay, interval, threshold):
                    return False

        return True

