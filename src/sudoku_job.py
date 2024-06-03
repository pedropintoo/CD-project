from src.sudoku_algorithm import SudokuAlgorithm

class Found(Exception): pass # Exception to stop the loop

class SudokuJob:
    def __init__(self, sudoku, start, end, solverConfig):
        self.solverConfig = solverConfig

        self.grid = sudoku
        self.start = start
        self.end = end
        self.solution = None

    def run(self):
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

    






        