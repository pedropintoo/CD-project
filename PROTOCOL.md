| Command | Destination | Description |
| --- | --- | --- |
| `HELLO` | Any node | ```{'command': 'HELLO', 'replyAddress': 'host:port', 'args': {'nodesList': ['host:port']}}```  |
| `JOIN_REQUEST` | Anchor node | ```{'command': 'JOIN_REQUEST', 'replyAddress': 'host:port'}``` |
| `JOIN_REPLY` | Joining node | ```{'command': 'JOIN_REPLY', 'args': {'nodesList': ['host:port']}}``` |
| `SOLVE_REQUEST` | Any node | ```{'command': 'SOLVE_REQUEST', 'replyAddress': 'host:port', 'args': {'task_id': task_id}``` |
| `SOLVE_REPLY` | Node that made the request | ```{'command': 'SOLVE_REPLY', 'replyAddress': 'host:port', 'args': {'task_id': task_id}``` |
| `FLOODING_RESULT` | Any node | ```{'command': 'FLOODING_RESULT', 'round':round ,'baseValue': baseValue, 'incrementedValue': incrementedValue}``` |
| `FLOODING_CONFIRMATION` | Any node | ```{'command': 'FLOODING_CONFIRMATION', 'round':round ,'baseValue': baseValue}``` |