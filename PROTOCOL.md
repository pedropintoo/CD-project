| Command | Destination | Description |
| --- | --- | --- |
| `FLOODING_RESULT` | Any node | ```{'command': 'FLOODING_RESULT', 'replyAddress': 'host:port', 'args': {'nodesList': ['host:port']}, 'baseValue': baseValue, 'incrementedValue': incrementedValue}``` |
| `FLOODING_CONFIRMATION` | Any node | ```{'command': 'FLOODING_CONFIRMATION', 'replyAddress': 'host:port', 'baseValue': baseValue}``` |
| `JOIN_REQUEST` | Anchor node | ```{'command': 'JOIN_REQUEST', 'replyAddress': 'host:port'}``` |
| `JOIN_REPLY` | Joining node | ```{'command': 'JOIN_REPLY', 'args': {'nodesList': ['host:port']}}``` |
| `SOLVE_REQUEST` | Any node | ```{'command': 'SOLVE_REQUEST', 'replyAddress': 'host:port', 'args': {'task_id': task_id , 'sudoku': sudoku} }``` |
| `SOLVE_REPLY` | Node that made the request | ```{'command': 'SOLVE_REPLY', 'replyAddress': 'host:port', 'args': {'task_id': task_id, 'solution': solution} }``` |
| `FLOODING_RESULT` | Any node | ```{'command': 'FLOODING_RESULT', 'replyAddress': 'host:port', 'baseValue': baseValue, 'incrementedValue': incrementedValue, 'args': {'nodesList': ['host:port']}}}``` |
| `FLOODING_CONFIRMATION` | Any node | ```{'command': 'FLOODING_CONFIRMATION', 'replyAddress': 'host:port', 'args': { 'all' : {'solved': X, 'invalid': X} , 'nodes': [ { 'address': 'host:port', 'validations': x }, ... ] }}``` |


# nodesList são os que estão vivos

{'command': 'FLOODING_CONFIRMATION', 'args': { 'all' : {'solved': X, 'invalid': X} , 'nodes': [ { 'address': 'host:port', 'validations': x }, ... ] }}
