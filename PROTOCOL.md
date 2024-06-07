
## `FLOODING_HELLO` -> Alive nodes  
```json
{
    "command": "FLOODING_HELLO",
    "replyAddress": "host:port",
    "args": { 
        "aliveNodes": ["host:port"],
        "stats": {
            "all" : {
                "solved": 0, "internal_solved": 0,
                "invalid": 0,"internal_invalid": 0,
            },
            "nodes": [ 
                { 
                    "address": "host:port", 
                    "validations": 0, 
                    "internal_validations": 0, 
                }, 
                ... 
            ]
        }
             
    }
}
```


## `FLOODING_CONFIRMATION` -> Consensus nodes 
```json
{
    "command": "FLOODING_CONFIRMATION",
    "replyAddress": "host:port",
    "args": {
        "stats": {
            "all" : {
                "solved": 0,
                "invalid": 0,
            },
            "nodes": [ 
                { 
                    "address": "host:port", 
                    "validations": 0, 
                }, 
                ... 
            ]
        } 
    }
}
``` 


## `JOIN_REQUEST` -> Anchor node
```json
{
    "command": "JOIN_REQUEST",
    "replyAddress": "host:port"
}
```


## `JOIN_REPLY` -> Joining node
```json
{
    "command": "JOIN_REPLY",
    "args": {
        "aliveNodes": ["host:port"]
    }
}
``` 


## `SOLVE_REQUEST` -> Alive nodes
```json
{
    "command": "SOLVE_REQUEST",
    "replyAddress": "host:port",
    "args": {
        "task_id": "sudoku_id[start-end]",
        "sudoku": sudoku
    }
}
``` 


## `SOLVE_REPLY` -> Node that made the request
```json
{
    "command": "SOLVE_REPLY",
    "replyAddress": "host:port",
    "args": {
        "task_id": task_id,
        "solution": solution
    } 
}
```


