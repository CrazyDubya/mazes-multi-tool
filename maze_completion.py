import random
from collections import deque
import heapq
import time
import matplotlib.pyplot as plt
import json
import os


# =======================
# Maze Generation Algorithms
# =======================

def generate_maze(width, height):
    """
    Recursive Backtracking Maze Generation Algorithm.
    """
    maze = [[1 for _ in range(width)] for _ in range(height)]

    def carve_passages(cx, cy, maze, width, height):
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            if 0 < nx < width and 0 < ny < height and maze[ny][nx] == 1:
                maze[ny][nx] = 0
                maze[cy + dy // 2][cx + dx // 2] = 0
                carve_passages(nx, ny, maze, width, height)

    start_x, start_y = 1, 1  # Fixed starting position
    maze[start_y][start_x] = 0
    carve_passages(start_x, start_y, maze, width, height)

    # Ensure entrance and exit are consistent
    maze[1][0] = 0  # Entrance at (0,1)
    maze[height - 2][width - 1] = 0  # Exit at (width-1, height-2)

    return maze


def recursive_division_maze(width, height):
    """
    Recursive Division Maze Generation Algorithm.
    """
    maze = [[1 for _ in range(width)] for _ in range(height)]

    def divide(x, y, w, h, orientation):
        if w < 3 or h < 3:
            return
        horizontal = orientation == 'H'

        if horizontal:
            wx = x
            wy = y + random.randint(1, h - 2)
            px = wx + random.randint(0, w - 1)
            for i in range(w):
                maze[wy][wx + i] = 1
            maze[wy][px] = 0
            # Recursively divide the regions above and below the wall
            divide(x, y, w, wy - y, choose_orientation(w, wy - y))
            divide(x, wy + 1, w, y + h - wy - 1, choose_orientation(w, y + h - wy - 1))
        else:
            wx = x + random.randint(1, w - 2)
            wy = y
            py = wy + random.randint(0, h - 1)
            for i in range(h):
                maze[wy + i][wx] = 1
            maze[py][wx] = 0
            # Recursively divide the regions to the left and right of the wall
            divide(x, y, wx - x, h, choose_orientation(wx - x, h))
            divide(wx + 1, y, x + w - wx - 1, h, choose_orientation(x + w - wx - 1, h))

    def choose_orientation(w, h):
        if w < h:
            return 'H'
        elif h < w:
            return 'V'
        else:
            return 'H' if random.choice([True, False]) else 'V'

    # Initialize the maze with passages
    for i in range(width):
        maze[0][i] = 1
        maze[height - 1][i] = 1
    for i in range(height):
        maze[i][0] = 1
        maze[i][width - 1] = 1

    divide(1, 1, width - 2, height - 2, choose_orientation(width - 2, height - 2))

    # Ensure entrance and exit are consistent
    maze[1][0] = 0  # Entrance at (0,1)
    maze[height - 2][width - 1] = 0  # Exit at (width-1, height-2)

    return maze


def prim_maze(width, height):
    """
    Prim's Algorithm Maze Generation.
    """
    maze = [[1 for _ in range(width)] for _ in range(height)]
    start_x, start_y = 1, 1  # Fixed starting position
    maze[start_y][start_x] = 0
    walls = []

    def add_walls(x, y):
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < width and 0 < ny < height and maze[ny][nx] == 1:
                walls.append((x, y, nx, ny))

    add_walls(start_x, start_y)

    while walls:
        idx = random.randint(0, len(walls) - 1)
        x, y, nx, ny = walls.pop(idx)
        if maze[ny][nx] == 1:
            maze[ny][nx] = 0
            maze[y + (ny - y) // 2][x + (nx - x) // 2] = 0
            add_walls(nx, ny)

    # Ensure entrance and exit are consistent
    maze[1][0] = 0  # Entrance at (0,1)
    maze[height - 2][width - 1] = 0  # Exit at (width-1, height-2)

    return maze


def kruskal_maze(width, height):
    """
    Kruskal's Algorithm Maze Generation.
    """
    maze = [[1 for _ in range(width)] for _ in range(height)]
    parent = {}

    def find(cell):
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    def union(cell1, cell2):
        root1 = find(cell1)
        root2 = find(cell2)
        parent[root2] = root1

    # Initialize cells
    for y in range(1, height, 2):
        for x in range(1, width, 2):
            maze[y][x] = 0
            parent[(x, y)] = (x, y)

    walls = []
    for y in range(1, height, 2):
        for x in range(1, width, 2):
            if x < width - 2:
                walls.append(((x, y), (x + 2, y)))
            if y < height - 2:
                walls.append(((x, y), (x, y + 2)))

    random.shuffle(walls)

    for cell1, cell2 in walls:
        if find(cell1) != find(cell2):
            union(cell1, cell2)
            mx, my = (cell1[0] + cell2[0]) // 2, (cell1[1] + cell2[1]) // 2
            maze[my][mx] = 0

    # Ensure entrance and exit are consistent
    maze[1][0] = 0  # Entrance at (0,1)
    maze[height - 2][width - 1] = 0  # Exit at (width-1, height-2)

    return maze


def ellers_maze(width, height):
    """
    Eller's Algorithm Maze Generation.
    """
    maze = [[1 for _ in range(width)] for _ in range(height)]
    sets = {}
    current_set = 1

    for y in range(1, height, 2):
        # Initialize cells
        for x in range(1, width, 2):
            maze[y][x] = 0
            sets[x] = current_set
            current_set += 1

        # Create horizontal connections
        for x in range(1, width - 2, 2):
            if y == height - 2:
                continue
            if random.choice([True, False]):
                maze[y][x + 1] = 0
                sets[x + 2] = sets[x]

        # Create vertical connections
        next_row_sets = {}
        for x in range(1, width, 2):
            if random.choice([True, False]) or y == height - 2:
                if y < height - 2:
                    maze[y + 1][x] = 0
                    next_row_sets[x] = sets[x]
                else:
                    next_row_sets[x] = sets[x]
            else:
                next_row_sets[x] = None

        # Assign new sets where necessary
        for x in range(1, width, 2):
            if next_row_sets[x] is None:
                sets[x] = current_set
                current_set += 1
            else:
                sets[x] = next_row_sets[x]

    # Ensure entrance and exit are consistent
    maze[1][0] = 0  # Entrance at (0,1)
    maze[height - 2][width - 1] = 0  # Exit at (width-1, height-2)

    return maze


# =======================
# Helper Functions
# =======================

def get_neighbors(position, maze):
    """
    Returns the list of accessible neighboring positions (up, down, left, right).
    """
    x, y = position
    neighbors = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Left, Right, Up, Down
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= ny < len(maze) and 0 <= nx < len(maze[0]):
            if maze[ny][nx] == 0:
                neighbors.append((nx, ny))
    return neighbors


def reconstruct_path(parent, start, goal):
    """
    Reconstructs the path from goal to start using the parent dictionary.
    """
    path = []
    current = goal
    while current != start:
        path.append(current)
        current = parent.get(current)
        if current is None:
            return []  # No path found
    path.append(start)
    path.reverse()
    return path


def heuristic(a, b):
    """
    Manhattan distance heuristic for A*.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def merge_paths(front_visited, back_visited, meeting_point):
    """
    Merges the paths from front and back searches at the meeting point.
    """
    path = []
    current = meeting_point
    while current:
        path.append(current)
        current = front_visited.get(current)
    path = path[::-1]
    current = back_visited.get(meeting_point)
    while current:
        path.append(current)
        current = back_visited.get(current)
    return path


def is_solvable(maze, start, goal):
    """
    Checks if there's a path from start to goal using BFS.
    Returns True if solvable, False otherwise.
    """
    queue = deque([start])
    visited = set()
    visited.add(start)

    while queue:
        current = queue.popleft()
        if current == goal:
            return True
        for neighbor in get_neighbors(current, maze):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


# =======================
# Pathfinding Algorithms with Stats
# =======================

def bfs_with_stats(maze, start, goal):
    """
    Breadth-First Search Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    queue = deque([start])
    visited = set()
    visited.add(start)
    parent = {start: None}
    nodes_explored = 0

    while queue:
        current = queue.popleft()
        nodes_explored += 1
        if current == goal:
            break
        neighbors = get_neighbors(current, maze)
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)

    path = reconstruct_path(parent, start, goal)
    return path, nodes_explored


def dfs_with_stats(maze, start, goal):
    """
    Depth-First Search Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    stack = [start]
    visited = set()
    visited.add(start)
    parent = {start: None}
    nodes_explored = 0

    while stack:
        current = stack.pop()
        nodes_explored += 1
        if current == goal:
            break
        neighbors = get_neighbors(current, maze)
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    path = reconstruct_path(parent, start, goal)
    return path, nodes_explored


def dijkstra_with_stats(maze, start, goal):
    """
    Dijkstra's Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    heap = []
    heapq.heappush(heap, (0, start))
    distances = {start: 0}
    parent = {start: None}
    nodes_explored = 0

    while heap:
        current_distance, current = heapq.heappop(heap)
        nodes_explored += 1
        if current == goal:
            break
        for neighbor in get_neighbors(current, maze):
            distance = current_distance + 1
            if neighbor not in distances or distance < distances[neighbor]:
                distances[neighbor] = distance
                parent[neighbor] = current
                heapq.heappush(heap, (distance, neighbor))

    path = reconstruct_path(parent, start, goal)
    return path, nodes_explored


def a_star_with_stats(maze, start, goal):
    """
    A* Search Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    heap = []
    heapq.heappush(heap, (heuristic(start, goal), 0, start))
    distances = {start: 0}
    parent = {start: None}
    nodes_explored = 0

    while heap:
        _, current_distance, current = heapq.heappop(heap)
        nodes_explored += 1
        if current == goal:
            break
        for neighbor in get_neighbors(current, maze):
            distance = current_distance + 1
            if neighbor not in distances or distance < distances[neighbor]:
                distances[neighbor] = distance
                parent[neighbor] = current
                priority = distance + heuristic(neighbor, goal)
                heapq.heappush(heap, (priority, distance, neighbor))

    path = reconstruct_path(parent, start, goal)
    return path, nodes_explored


def greedy_bfs_with_stats(maze, start, goal):
    """
    Greedy Best-First Search Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    heap = []
    heapq.heappush(heap, (heuristic(start, goal), start))
    visited = set()
    visited.add(start)
    parent = {start: None}
    nodes_explored = 0

    while heap:
        _, current = heapq.heappop(heap)
        nodes_explored += 1
        if current == goal:
            break
        for neighbor in get_neighbors(current, maze):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                heapq.heappush(heap, (heuristic(neighbor, goal), neighbor))

    path = reconstruct_path(parent, start, goal)
    return path, nodes_explored


def bidirectional_bfs_with_stats(maze, start, goal):
    """
    Bidirectional BFS Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """
    if start == goal:
        return [start], 0

    front_queue = deque([start])
    back_queue = deque([goal])
    front_visited = {start: None}
    back_visited = {goal: None}
    nodes_explored = 0

    while front_queue and back_queue:
        # Expand front
        current_front = front_queue.popleft()
        nodes_explored += 1
        for neighbor in get_neighbors(current_front, maze):
            if neighbor not in front_visited:
                front_visited[neighbor] = current_front
                front_queue.append(neighbor)
                if neighbor in back_visited:
                    path = merge_paths(front_visited, back_visited, neighbor)
                    return path, nodes_explored

        # Expand back
        current_back = back_queue.popleft()
        nodes_explored += 1
        for neighbor in get_neighbors(current_back, maze):
            if neighbor not in back_visited:
                back_visited[neighbor] = current_back
                back_queue.append(neighbor)
                if neighbor in front_visited:
                    path = merge_paths(front_visited, back_visited, neighbor)
                    return path, nodes_explored

    return [], nodes_explored


def bidirectional_a_star_with_stats(maze, start, goal):
    """
    Bidirectional A* Search Algorithm with statistics tracking.
    Returns the path and number of nodes explored.
    """

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    front_heap = []
    back_heap = []
    heapq.heappush(front_heap, (heuristic(start, goal), 0, start))
    heapq.heappush(back_heap, (heuristic(goal, start), 0, goal))

    front_dist = {start: 0}
    back_dist = {goal: 0}
    front_parent = {start: None}
    back_parent = {goal: None}
    nodes_explored = 0
    meeting_point = None

    while front_heap and back_heap:
        # Expand front
        if front_heap:
            _, current_distance, current = heapq.heappop(front_heap)
            nodes_explored += 1
            if current in back_dist:
                meeting_point = current
                break
            for neighbor in get_neighbors(current, maze):
                distance = current_distance + 1
                if neighbor not in front_dist or distance < front_dist[neighbor]:
                    front_dist[neighbor] = distance
                    front_parent[neighbor] = current
                    priority = distance + heuristic(neighbor, goal)
                    heapq.heappush(front_heap, (priority, distance, neighbor))

        # Expand back
        if back_heap:
            _, current_distance, current = heapq.heappop(back_heap)
            nodes_explored += 1
            if current in front_dist:
                meeting_point = current
                break
            for neighbor in get_neighbors(current, maze):
                distance = current_distance + 1
                if neighbor not in back_dist or distance < back_dist[neighbor]:
                    back_dist[neighbor] = distance
                    back_parent[neighbor] = current
                    priority = distance + heuristic(neighbor, start)
                    heapq.heappush(back_heap, (priority, distance, neighbor))

    if not meeting_point:
        return [], nodes_explored

    # Reconstruct path
    path = []
    current = meeting_point
    while current:
        path.append(current)
        current = front_parent.get(current)
    path = path[::-1]
    current = back_parent.get(meeting_point)
    while current:
        path.append(current)
        current = back_parent.get(current)
    return path, nodes_explored


# =======================
# Player and Leaderboard Classes
# =======================

class Player:
    """
    Represents a pathfinding algorithm contestant.
    Tracks performance metrics.
    """

    def __init__(self, name, algorithm):
        self.name = name
        self.algorithm = algorithm
        self.total_time = 0.0
        self.total_path_length = 0
        self.total_nodes_explored = 0
        self.run_count = 0

    def update_stats(self, time_taken, path_length, nodes_explored):
        self.total_time += time_taken
        self.total_path_length += path_length
        self.total_nodes_explored += nodes_explored
        self.run_count += 1

    def average_time(self):
        return self.total_time / self.run_count if self.run_count else float('inf')

    def average_path_length(self):
        return self.total_path_length / self.run_count if self.run_count else float('inf')

    def average_nodes_explored(self):
        return self.total_nodes_explored / self.run_count if self.run_count else float('inf')


class Leaderboard:
    """
    Maintains and persists the leaderboard across sessions.
    """

    def __init__(self, filename='leaderboard.json'):
        self.filename = filename
        self.players = {}
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                data = json.load(f)
                for name, stats in data.items():
                    player = Player(name, None)
                    player.total_time = stats['total_time']
                    player.total_path_length = stats['total_path_length']
                    player.total_nodes_explored = stats['total_nodes_explored']
                    player.run_count = stats['run_count']
                    self.players[name] = player

    def add_player(self, player):
        if player.name not in self.players:
            # Create a new player entry
            existing = Player(player.name, player.algorithm)
            existing.total_time = player.total_time
            existing.total_path_length = player.total_path_length
            existing.total_nodes_explored = player.total_nodes_explored
            existing.run_count = player.run_count
            self.players[player.name] = existing
        else:
            # Update existing player stats
            existing = self.players[player.name]
            existing.total_time += player.total_time
            existing.total_path_length += player.total_path_length
            existing.total_nodes_explored += player.total_nodes_explored
            existing.run_count += player.run_count

    def save(self):
        data = {}
        for name, player in self.players.items():
            data[name] = {
                'total_time': player.total_time,
                'total_path_length': player.total_path_length,
                'total_nodes_explored': player.total_nodes_explored,
                'run_count': player.run_count
            }
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

    def display(self):
        print("\nLeaderboard:")
        print(f"{'Algorithm':<30} {'Avg Time (s)':<15} {'Avg Path Len':<15} {'Avg Nodes Exp':<15}")
        sorted_players = sorted(self.players.values(), key=lambda p: p.average_time())
        for player in sorted_players:
            avg_path_len = player.average_path_length()
            # Handle 'inf' path lengths
            avg_path_len_display = f"{avg_path_len:.2f}" if avg_path_len != float('inf') else "inf"
            print(
                f"{player.name:<30} {player.average_time():<15.6f} {avg_path_len_display:<15} {player.average_nodes_explored():<15.2f}")


# =======================
# Players Registration
# =======================

def get_pathfinding_players():
    """
    Registers all pathfinding algorithms as players.
    """
    return [
        Player("Breadth-First Search (BFS)", bfs_with_stats),
        Player("Depth-First Search (DFS)", dfs_with_stats),
        Player("Dijkstra's Algorithm", dijkstra_with_stats),
        Player("A* Search", a_star_with_stats),
        Player("Greedy Best-First Search", greedy_bfs_with_stats),
        Player("Bidirectional BFS", bidirectional_bfs_with_stats),
        Player("Bidirectional A* Search", bidirectional_a_star_with_stats)
    ]


# =======================
# Competition Function
# =======================

def run_competition(num_mazes, width, height, maze_generators, players, leaderboard, image_dir):
    for i in range(1, num_mazes + 1):
        # Attempt to generate a solvable maze
        max_attempts = 10  # Prevent infinite loops
        attempt = 0
        while attempt < max_attempts:
            generator_name, generator_func = random.choice(maze_generators)
            maze = generator_func(width, height)
            start = (0, 1)
            goal = (width - 1, height - 2)

            if is_solvable(maze, start, goal):
                break  # Maze is solvable
            else:
                attempt += 1
                print(f"Maze {i}: Generated maze is unsolvable. Regenerating... (Attempt {attempt})")
        else:
            print(f"Maze {i}: Failed to generate a solvable maze after {max_attempts} attempts. Skipping...")
            continue  # Skip to the next maze if unable to generate a solvable one

        # Process each player
        for player in players:
            start_time = time.time()
            path, nodes_explored = player.algorithm(maze, start, goal)
            end_time = time.time()
            time_taken = end_time - start_time
            path_length = len(path) if path else float('inf')
            player.update_stats(time_taken, path_length, nodes_explored)
            leaderboard.add_player(player)

        # Save the maze visualization
        paths = {}
        for player in players:
            # Re-run algorithm to get paths for visualization
            path, _ = player.algorithm(maze, start, goal)
            paths[player.name] = path

        # Define image filename
        clean_generator_name = generator_name.replace(" ", "_").replace("'", "")
        image_filename = f"maze_{i}_{clean_generator_name}.png"
        image_path = os.path.join(image_dir, image_filename)

        # Save the image
        visualize_maze_with_paths(maze, paths, start, goal, save_path=image_path)

        print(f"Maze {i}/{num_mazes} generated using {generator_name} and saved as {image_filename}")

    # After all mazes are processed, save and display the leaderboard
    leaderboard.save()
    leaderboard.display()


# =======================
# Visualization Function
# =======================

def visualize_maze_with_paths(maze, paths=None, start=(0, 1), goal=None, save_path=None):
    """
    Visualizes the maze and overlays the paths found by different algorithms.
    Saves the visualization to the specified path if provided.
    """
    if goal is None:
        goal = (len(maze[0]) - 1, len(maze) - 2)
    maze_img = [[0 if cell == 1 else 1 for cell in row] for row in maze]

    plt.figure(figsize=(10, 10))
    plt.imshow(maze_img, cmap='binary')

    # Plot start and goal
    plt.scatter(start[0], start[1], marker='o', color='green', s=100, label='Start')
    plt.scatter(goal[0], goal[1], marker='x', color='red', s=100, label='Goal')

    # Define distinct colors for each algorithm
    colors = ['yellow', 'cyan', 'magenta', 'orange', 'lime', 'purple', 'blue', 'brown', 'pink', 'grey']
    for idx, (alg, path) in enumerate(paths.items()):
        if path:
            xs, ys = zip(*path)
            plt.plot(xs, ys, color=colors[idx % len(colors)], label=alg)

    plt.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
    plt.axis('off')  # Hide axes for better visualization

    if save_path:
        plt.tight_layout()
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


# =======================
# Main Execution
# =======================

if __name__ == "__main__":
    # Parameters
    NUM_MAZES = 20
    WIDTH = 31  # Must be odd number
    HEIGHT = 31  # Must be odd number

    # Directory to save maze images
    IMAGE_DIR = "maze_images"

    # Create directory if it doesn't exist
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    # Define Maze Generators
    maze_generators = [
        ("Recursive Backtracking", generate_maze),
        ("Recursive Division", recursive_division_maze),
        ("Prim's Algorithm", prim_maze),
        ("Kruskal's Algorithm", kruskal_maze),
        ("Eller's Algorithm", ellers_maze)
    ]

    # Initialize Players
    players = get_pathfinding_players()

    # Initialize Leaderboard
    leaderboard = Leaderboard()

    # Run Competition
    print("Starting the Pathfinding Algorithms Competition...")
    run_competition(NUM_MAZES, WIDTH, HEIGHT, maze_generators, players, leaderboard, IMAGE_DIR)

    print("\nCompetition completed. Leaderboard and maze images have been saved.")
