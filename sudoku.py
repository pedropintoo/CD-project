class Sudoku:
    def __init__(self, sudoku):
        self.grid = sudoku

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += str(self.grid[i][j])
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def check(self):
        # Check rows
        for row in range(9):
            if sum(self.grid[row]) != 45:
                return False

        # Check columns
        for col in range(9):
            if sum([self.grid[row][col] for row in range(9)]) != 45:
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if sum([self.grid[i*3+k][j*3+l] for k in range(3) for l in range(3)]) != 45:
                    return False

        return True

    def solve(self):
        empty_cell = self.__find_empty_cell()
        if not empty_cell:
            return True  # Puzzle solved

        row, col = empty_cell
        for num in range(1, 10):
            if self.__is_valid_move(row, col, num):
                self.grid[row][col] = num
                if self.solve():
                    return True
                self.grid[row][col] = 0  # Backtrack
        return False

    def __find_empty_cell(self):
        for i in range(9):
            for j in range(9):
                if self.grid[i][j] == 0:
                    return (i, j)
        return None

    def __is_valid_move(self, row, col, num):
        # Check row
        if num in self.grid[row]:
            return False

        # Check column
        if num in [self.grid[i][col] for i in range(9)]:
            return False

        # Check 3x3 square
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(start_row, start_row + 3):
            for j in range(start_col, start_col + 3):
                if self.grid[i][j] == num:
                    return False

        return True


def main():
    solved_sudoku = [
        [8,2,7,1,5,4,3,9,6],
        [9,6,5,3,2,7,1,4,8],
        [3,4,1,6,8,9,7,5,2],
        [5,9,3,4,6,8,2,7,1],
        [4,7,2,5,1,3,6,8,9],
        [6,1,8,9,7,2,4,3,5],
        [7,8,6,2,3,5,9,1,4],
        [1,5,4,7,9,6,8,2,3],
        [2,3,9,8,4,1,5,6,7]
    ]

    sudoku = Sudoku([
        [0,0,0,1,0,0,0,0,0],
        [0,0,0,3,2,0,0,0,0],
        [0,0,0,0,0,9,0,0,0],
        [0,0,0,0,0,0,0,7,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,9,0,0,0,0,0],
        [0,0,0,0,0,0,9,0,0],
        [0,0,0,0,0,0,0,0,3],
        [0,0,0,0,0,0,0,0,0]
    ])

    print(sudoku)

    sudoku.solve()

    if sudoku.check():
        print("Sudoku is correct!")
        print(sudoku)

if __name__ == "__main__":
    main()
