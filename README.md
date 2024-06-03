# cd_sudoku
Projecto CD 2023/24

python3 node.py -p 8001 -s 7001 -a "localhost:7000" -l
python3 node.py -l
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"tasks":10}'

# estou a tentar enviar um sudoku também
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"tasks":10, "sudoku":[[0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 3, 2, 0, 0, 0, 0], [0, 0, 0, 0, 0, 9, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 7, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 9, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 9, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 3], [0, 0, 0, 0, 0, 0, 0, 0, 0]]}'

# não preciso de passar as tasks, number_of_tasks são as combinações possíveis
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku":[[0, 0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 3, 2, 0, 0, 0, 0], [0, 0, 0, 0, 0, 9, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 7, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 9, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 9, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 3], [0, 0, 0, 0, 0, 0, 0, 0, 0]]}'


curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku": [[6, 7, 9, 4, 3, 0, 8, 1, 5], [3, 5, 8, 9, 1, 7, 2, 6, 4], [4, 2, 1, 5, 8, 6, 7, 9, 3], [9, 4, 3, 6, 0, 1, 5, 2, 8], [5, 1, 2, 8, 9, 0, 3, 7, 6], [8, 6, 7, 2, 5, 3, 1, 4, 9], [7, 9, 6, 3, 2, 5, 4, 8, 0], [2, 8, 5, 0, 4, 9, 6, 3, 7], [1, 3, 4, 7, 6, 8, 9, 5, 2]] }'

# Sudoku mais simples
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku": [[6, 7, 9, 4, 3, 2, 8, 1, 5], [3, 5, 8, 9, 1, 7, 2, 6, 4], [4, 2, 1, 5, 8, 6, 7, 9, 3], [9, 4, 3, 6, 7, 1, 5, 2, 8], [5, 1, 2, 8, 9, 0, 3, 7, 6], [8, 6, 7, 2, 5, 3, 1, 4, 9], [7, 9, 6, 3, 2, 5, 4, 8, 0], [2, 8, 5, 1, 4, 9, 6, 3, 7], [1, 3, 4, 7, 6, 8, 9, 5, 2]] }'