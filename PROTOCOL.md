| Command | Destination | Description |
| --- | --- | --- |
| `HELLO` | Any node | ```{'command': 'HELLO', 'args': {'nodesList': []}}```  |
| `JOIN_REQUEST` | Anchor node | ```{'command': 'JOIN_REQUEST'}``` |
| `JOIN_REPLY` | Joining node | ```{'command': 'JOIN_REPLY', 'args': {'nodesList': []}}``` |
| `SOLVE_REQUEST` | Any node | ```{'command': 'SOLVE_REQUEST', 'task': task_id}``` |
| `SOLVE_REPLY` | Node that made the request | ```{'command': 'SOLVE_REPLY'}``` |
