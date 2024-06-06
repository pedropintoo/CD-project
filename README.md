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
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku": [[0, 7, 9, 4, 3, 2, 8, 1, 5], [3, 5, 8, 9, 1, 7, 2, 6, 4], [4, 2, 1, 5, 8, 6, 7, 9, 3], [9, 4, 3, 6, 7, 1, 5, 2, 8], [5, 1, 2, 8, 9, 0, 3, 7, 6], [8, 6, 7, 2, 5, 3, 1, 4, 9], [7, 9, 6, 3, 2, 5, 4, 8, 0], [2, 8, 5, 1, 4, 9, 6, 3, 7], [1, 3, 4, 7, 6, 8, 9, 5, 0]] }'

# Sudoku mais simples
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku": [[6, 7, 9, 4, 3, 2, 8, 1, 5], [3, 5, 8, 9, 1, 7, 2, 6, 4], [4, 2, 1, 5, 8, 6, 7, 9, 3], [9, 4, 3, 6, 7, 1, 5, 2, 8], [5, 1, 2, 8, 9, 0, 3, 7, 6], [8, 6, 7, 2, 5, 3, 1, 4, 9], [7, 9, 6, 3, 2, 5, 4, 8, 0], [2, 8, 5, 1, 4, 9, 6, 3, 7], [1, 3, 4, 7, 6, 8, 9, 5, 2]] }'


self.base_delay = 0.01  # delay applied when the number of requests exceeds the threshold
self.interval = 10      # interval to check if the number of requests exceeds the threshold
self.threshold = 20     # maximum number of requests allowed in the interval

threshold não devia ser um parâmetro fixo mas sim um valor que reflita o número médio de requests que o servidor consegue processar por segundo

interval não devia ser um parâmetro fixo mas sim um valor que reflita o tempo médio que o servidor demora a processar um request

o node pode ser inicializado com um handicap. O handicap serve para atrasar o nó, ou seja, se o handicap for o dobro, deverá demorar o dobro do tempo a processar um request

quero que alteres a minha função _limit_calls para que tenha em conta estes requisitos.

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
        num_requests = len([t for t in self.recent_requests if current_time - t < interval])
        self.logger.critical(f"Number of requests: {num_requests}")
        
        # If the number of requests exceeds the threshold, the delay increases linearly
        if num_requests > threshold:
            self.logger.info(f"Threshold exceeded: {threshold}")
            
            # delay = base_delay * (num_requests - threshold + 1)
            delay = self.handicap
            # self.logger.info(f"Delay applied: {delay}")
            time.sleep(delay)


1min20 com handicap = 1e-10
min com handicap = 2e-10

