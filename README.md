# Projecto CD 2023/24
João Pinto - 104384
Pedro Pinto - 115304

## Overview
This project is a distributed Sudoku solver that uses a network of nodes to solve Sudoku puzzles. Each node can be initialized locally or anchored to another node, and nodes can be given a handicap to affect their processing speed.

## Initializing Nodes

Initialize a node locally:
`python3 node.py -l`

Initialize a node anchored to another node:
`python3 node.py -p 8001 -s 7001 -a "localhost:7000" -l`

Initialize a node with a handicap, affects the velocity of the node:
`python3 node.py -p 8001 -s 7001 -a "localhost:7000" -l -d 2`

## Requesting Sudoku Solutions - XML AND JSON

Exemple of a `JSON request`:
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/json' -d '{"sudoku": [[6, 7, 9, 4, 3, 0, 8, 1, 5], [3, 5, 8, 9, 1, 7, 2, 6, 4], [4, 2, 1, 5, 8, 6, 7, 9, 3], [9, 4, 3, 6, 0, 1, 5, 2, 8], [5, 1, 2, 8, 9, 0, 3, 7, 6], [8, 6, 7, 2, 5, 3, 1, 4, 9], [7, 9, 6, 3, 2, 5, 4, 8, 0], [2, 8, 5, 0, 4, 9, 6, 3, 7], [1, 3, 4, 7, 6, 8, 9, 5, 2]] }'

Example of a `XML request`:
curl http://localhost:8000/solve -X POST -H 'Content-Type: application/xml' -d '<request><sudoku><row><cell>6</cell><cell>7</cell><cell>9</cell><cell>4</cell><cell>3</cell><cell>0</cell><cell>8</cell><cell>1</cell><cell>5</cell></row><row><cell>3</cell><cell>5</cell><cell>8</cell><cell>9</cell><cell>1</cell><cell>7</cell><cell>2</cell><cell>6</cell><cell>4</cell></row><row><cell>4</cell><cell>2</cell><cell>1</cell><cell>5</cell><cell>8</cell><cell>6</cell><cell>7</cell><cell>9</cell><cell>3</cell></row><row><cell>9</cell><cell>4</cell><cell>3</cell><cell>6</cell><cell>0</cell><cell>1</cell><cell>5</cell><cell>2</cell><cell>8</cell></row><row><cell>5</cell><cell>1</cell><cell>2</cell><cell>8</cell><cell>9</cell><cell>0</cell><cell>3</cell><cell>7</cell><cell>6</cell></row><row><cell>8</cell><cell>6</cell><cell>7</cell><cell>2</cell><cell>5</cell><cell>3</cell><cell>1</cell><cell>4</cell><cell>9</cell></row><row><cell>7</cell><cell>9</cell><cell>6</cell><cell>3</cell><cell>2</cell><cell>5</cell><cell>4</cell><cell>8</cell><cell>0</cell></row><row><cell>2</cell><cell>8</cell><cell>5</cell><cell>0</cell><cell>4</cell><cell>9</cell><cell>6</cell><cell>3</cell><cell>7</cell></row><row><cell>1</cell><cell>3</cell><cell>4</cell><cell>7</cell><cell>6</cell><cell>8</cell><cell>9</cell><cell>5</cell><cell>2</cell></row></sudoku></request>'

## Requesting Statistics and Network Information (default is JSON)

curl http://localhost:8000/stats -X GET -H "Content-Type: application/json"
curl http://localhost:8000/stats -X GET -H "Content-Type: application/xml"
curl http://localhost:8000/stats -X GET

curl http://localhost:8000/network -X GET -H "Content-Type: application/json"
curl http://localhost:8000/network -X GET -H "Content-Type: application/xml"
curl http://localhost:8000/network -X GET