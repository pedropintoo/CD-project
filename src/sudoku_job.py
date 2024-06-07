from src.sudoku_algorithm import SudokuAlgorithm
from threading import Thread

class Found(Exception): pass # Exception to stop the loop

class SudokuJob:
    def __init__(self, sudoku, start, end, solverConfig):
        self.solverConfig = solverConfig

        self.grid = sudoku
        self.start = start
        self.end = end
        self.solution = None

    def run(self, locker, queue, task_id, host_port):
        
        thread = Thread(target=self.solve_locking, args=(locker, queue, task_id, host_port))
        thread.daemon = True
        thread.start()

    def solve_locking(self, locker=None, queue=None, task_id=None, host_port=None):
        with locker:
            # 1. Fill the sudoku with the combinations from start to end
            try:
                for comb in range(self.start, self.end):
                    sudoku = self.grid.copy()
                    fill_comb = comb
                    for i in reversed(range(0, 9)):
                        sudoku[i] = self.grid[i].copy() # copy() is a shallow copy!
                        for j in reversed(range(0, 9)):
                            if sudoku[i][j] == 0:
                                sudoku[i][j] = fill_comb % (10)
                                fill_comb = fill_comb // 10

                        # 2. Check if the sudoku is valid. If yes, raise Found             
                        if self.solverConfig.checkWithParams(sudoku):
                            self.solution = sudoku
                            raise Found
            except Found: pass
            # 3. If solution is found, put it in the queue

            solution = self.solution if self.solution is not None else "INVALID"
            queue.put({"solution": solution, "task_id": task_id, "replyAddress": host_port})

    def solve(self):
        # 1. Fill the sudoku with the combinations from start to end
        try:
            for comb in range(self.start, self.end):
                sudoku = self.grid.copy()
                fill_comb = comb
                for i in reversed(range(0, 9)):
                    sudoku[i] = self.grid[i].copy() # copy() is a shallow copy!
                    for j in reversed(range(0, 9)):
                        if sudoku[i][j] == 0:
                            sudoku[i][j] = fill_comb % (10)
                            fill_comb = fill_comb // 10

                    # 2. Check if the sudoku is valid. If yes, raise Found             
                    if self.solverConfig.checkWithParams(sudoku):
                        self.solution = sudoku
                        raise Found
        except Found: pass
        # 3. If solution is found, return True

        return self.solution        





        