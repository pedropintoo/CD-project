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
                    if SudokuAlgorithm.checkWith(sudoku, self.solverConfig):
                        self.solution = sudoku
                        raise Found
        except Found: pass

        # 3. If solution is found, return True
        return self.solution


# if __name__ == "__main__":
    
#     sudoku = [  [8, 2, 7, 1, 5, 4, 3, 9, 6], 
#                 [9, 6, 5, 0, 2, 7, 1, 4, 8], 
#                 [3, 4, 1, 6, 8, 9, 7, 5, 2], 
#                 [5, 9, 3, 4, 6, 8, 2, 0, 1], 
#                 [4, 7, 2, 5, 1, 3, 6, 8, 9], 
#                 [6, 1, 8, 9, 7, 2, 4, 3, 5], 
#                 [7, 8, 6, 2, 3, 5, 9, 1, 0], 
#                 [1, 5, 4, 7, 9, 6, 8, 2, 3], 
#                 [2, 3, 9, 8, 4, 1, 5, 6, 7]]
        
#     solverConfig = SudokuAlgorithm(base_delay=0.01, interval=20, threshold=10)

#     solver = SudokuJob(sudoku, 111, 999, solverConfig)

#     response = solver.run()

#     if (response == True):
#         print("Solution found: ", solver.grid)
    


    






        