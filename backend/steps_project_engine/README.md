# Steps Project Engine

## Essential Docker commands

```sh
docker-compose build  # Build the image before creating a container
docker ps
docker exec project-1-1 python -c "print('Hello from container')"
docker exec project-1-1 cursor-agent -p "Create Python code to print Fibonacci sequence"
```

```sh
docker exec -i project-1-1 python -m pdb main.py
```
