# cd_sudoku
Projecto CD 2023/24

python3 node.py -p 8001 -s 7001 -a "localhost:7000" -l
python3 node.py -l
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"tasks":10}'