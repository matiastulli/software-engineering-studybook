"""
Graphs & recursion for live coding: runnable templates
======================================================
Run: python3 theory/backend/python_graphs.py  (every demo is an assert, so it fails loudly)

Which traversal? Decide from the question, not the data structure:

    Question asks for...                          Use                     Time        Space
    ---------------------------------------------------------------------------------------
    "is there a path / visit everything /         DFS (recursion/stack)   O(V + E)    O(V)
     connected components / cycle?"
    "fewest steps / shortest path, every edge     BFS (deque)             O(V + E)    O(V)
     costs the same / nodes at distance k"
    "an order that respects dependencies"         Topological sort        O(V + E)    O(V)
     (Airflow DAG, dbt ref() graph, courses)      (Kahn = BFS on in-degree)
    "shortest path, edges have weights >= 0"      Dijkstra (heapq)        O(E log V)  O(V)
    "are x and y connected?" asked many times     Union-Find              ~O(1) each  O(V)
     while edges keep arriving
    "all combinations / permutations / subsets"   Backtracking            exponential O(depth)

Data-engineering bridge: an Airflow DAG or a dbt lineage graph IS a directed acyclic
graph. Topological sort is how the scheduler decides run order, and cycle detection
is why `dbt` refuses a model that refs itself through another model.

Gotchas that cost points:
- Recursive DFS hits Python's default recursion limit (1000) on deep graphs or big grids.
  Say it out loud and offer the iterative stack version.
- Mark nodes visited when you ENQUEUE them in BFS (not when you dequeue),
  or the same node enters the queue many times.
- Nodes that only appear as neighbours aren't dict keys: use graph.get(node, []).
"""

import heapq
from collections import defaultdict, deque
from typing import Optional


# =============================================================================
# 1. GRAPH REPRESENTATIONS
# =============================================================================

# Adjacency list: dict node -> list of neighbours. Default choice: O(V + E) memory.
# (An adjacency matrix is O(V^2); only worth it for small, dense graphs.)
graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}  # undirected, and contains the cycle A-B-E-F-C-A

# Weighted adjacency list: node -> list of (neighbour, weight)
weighted_graph = {
    "A": [("B", 1), ("C", 4)],
    "B": [("A", 1), ("D", 2), ("E", 5)],
    "C": [("A", 4), ("F", 3)],
    "D": [("B", 2)],
    "E": [("B", 5), ("F", 1)],
    "F": [("C", 3), ("E", 1)],
}


def build_graph(edges: list[tuple], directed: bool = False) -> dict:
    """Edge list -> adjacency list, the most common input conversion.
    O(E). For an undirected graph, add both directions."""
    g = defaultdict(list)
    for u, v in edges:
        g[u].append(v)
        if not directed:
            g[v].append(u)
        else:
            g.setdefault(v, [])  # make sinks appear as keys too
    return g


# =============================================================================
# 2. DFS: DEPTH-FIRST SEARCH
# =============================================================================

def dfs_recursive(graph, start) -> list:
    """Go as deep as possible before backtracking. Returns the visit order.

    Use for reachability, connected components, cycle detection, topological sort,
    and 'explore every path'. Does NOT give shortest paths.
    Time O(V + E), since each node and edge is seen once. Space O(V) for visited plus
    the call stack, which can be V deep (recursion limit 1000).
    A set for membership (O(1)) and a list for order; `x in list` would be O(V).
    The inner function avoids the `visited=set()` mutable-default trap.
    """
    visited, order = set(), []

    def dfs(node):
        visited.add(node)
        order.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)

    dfs(start)
    return order


def dfs_iterative(graph, start) -> list:
    """Same traversal with an explicit stack: no recursion limit.
    Check `visited` on POP, because a node can be pushed several times before being visited.
    Neighbours are pushed in reverse so the order matches the recursive version.
    Time O(V + E), space O(V + E) worst case for the stack."""
    visited, order = set(), []
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for neighbor in reversed(graph.get(node, [])):
            if neighbor not in visited:
                stack.append(neighbor)
    return order


# =============================================================================
# 3. BFS: BREADTH-FIRST SEARCH
# =============================================================================

def bfs(graph, start) -> list:
    """Visit level by level (distance 0, then 1, then 2...) using a FIFO deque.

    Use for shortest paths when every edge costs the same, 'minimum steps', and level order.
    Time O(V + E), space O(V).
    deque.popleft() is O(1); list.pop(0) is O(V) and makes BFS quadratic.
    """
    visited = {start}
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)  # mark on enqueue
                queue.append(neighbor)
    return order


def bfs_shortest_path(graph, start, end) -> list:
    """Shortest path (fewest edges) in an unweighted graph, or [] if unreachable.

    Stores one parent per node and rebuilds the path at the end. Copying `path + [n]`
    into every queue entry also works, but costs O(V^2) memory in the worst case.
    Time O(V + E), space O(V).
    """
    parent = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == end:
            path = []
            while node is not None:
                path.append(node)
                node = parent[node]
            return path[::-1]
        for neighbor in graph.get(node, []):
            if neighbor not in parent:  # parent doubles as the visited set
                parent[neighbor] = node
                queue.append(neighbor)
    return []


def dijkstra(weighted_graph, start) -> dict:
    """Shortest distance from start to every reachable node, for weights >= 0.

    BFS with a min-heap instead of a queue: always expand the closest unfinished node.
    Time O(E log V), space O(V). With negative weights it's wrong (use Bellman-Ford).
    Skipping stale heap entries (d > dist[node]) replaces a decrease-key operation.
    """
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist[node]:
            continue  # stale entry, a shorter path was already found
        for neighbor, w in weighted_graph.get(node, []):
            nd = d + w
            if nd < dist.get(neighbor, float("inf")):
                dist[neighbor] = nd
                heapq.heappush(heap, (nd, neighbor))
    return dist


# =============================================================================
# 4. CYCLE DETECTION
# =============================================================================

def detect_cycle_undirected(graph) -> bool:
    """Undirected graph: a cycle exists if DFS reaches an already-visited node
    that isn't the node we just came from (the parent).
    Time O(V + E). Limitation: with parallel edges (A-B listed twice) the parent check
    misses that 2-cycle. Union-Find handles that case (union returns False)."""
    visited = set()

    def dfs(node, parent):
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, node):
                    return True
            elif neighbor != parent:  # back edge -> cycle
                return True
        return False

    return any(dfs(n, None) for n in list(graph) if n not in visited)


def detect_cycle_directed(graph) -> bool:
    """Directed graph: a cycle exists if DFS reaches a node that is still ON the current
    recursion path (grey in white/grey/black colouring). Merely 'visited before'
    is not enough: A->C and B->C is a diamond, not a cycle.
    Time O(V + E), space O(V)."""
    visited, on_path = set(), set()

    def dfs(node):
        visited.add(node)
        on_path.add(node)
        for neighbor in graph.get(node, []):
            if neighbor in on_path:
                return True
            if neighbor not in visited and dfs(neighbor):
                return True
        on_path.remove(node)  # leaving this path
        return False

    return any(dfs(n) for n in list(graph) if n not in visited)


# =============================================================================
# 5. TOPOLOGICAL SORT (directed acyclic graphs only)
# =============================================================================
# Use when the question is about order under dependencies: task scheduling, build
# steps, course prerequisites, dbt model run order. Edge u -> v means "u before v".

def topological_sort_kahn(graph) -> list:
    """Kahn's algorithm, the one to type in an interview: iterative and it detects cycles.

    1. Count in-degree (number of prerequisites) of every node.
    2. Queue every node with in-degree 0 (nothing blocks it).
    3. Pop a node, emit it, decrement its neighbours, and enqueue any that reach 0.
    If fewer nodes were emitted than exist, the remainder is stuck in a cycle.
    Time O(V + E), space O(V).
    """
    nodes = set(graph) | {v for vs in graph.values() for v in vs}
    in_degree = {n: 0 for n in nodes}
    for u in graph:
        for v in graph[u]:
            in_degree[v] += 1

    queue = deque(sorted(n for n in nodes if in_degree[n] == 0))  # sorted = deterministic
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(nodes):
        raise ValueError("Graph has a cycle, so no topological order exists")
    return order


def topological_sort_dfs(graph) -> list:
    """DFS version: append a node AFTER all its descendants finish, then reverse.
    Needs the on-path check too; without it a cyclic graph silently returns a wrong order.
    Time O(V + E), space O(V) including recursion depth."""
    visited, on_path, post_order = set(), set(), []

    def dfs(node):
        on_path.add(node)
        for neighbor in graph.get(node, []):
            if neighbor in on_path:
                raise ValueError("Graph has a cycle, so no topological order exists")
            if neighbor not in visited:
                dfs(neighbor)
        on_path.remove(node)
        visited.add(node)
        post_order.append(node)

    for node in list(graph):
        if node not in visited:
            dfs(node)
    return post_order[::-1]


# =============================================================================
# 6. CONNECTED COMPONENTS
# =============================================================================

def connected_components(graph) -> list[list]:
    """Groups of nodes that reach each other (undirected). Start a DFS from every
    unvisited node; each start is a new component. Time O(V + E).
    Iterative, so a 100k-node component doesn't hit the recursion limit."""
    visited, components = set(), []
    for start in graph:
        if start in visited:
            continue
        component, stack = [], [start]
        visited.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


# =============================================================================
# 7. UNION-FIND (disjoint set union)
# =============================================================================

class UnionFind:
    """Answers 'are x and y connected?' while edges keep arriving, without re-running DFS.
    With path compression plus union by rank, each operation is ~O(1) amortised
    (inverse Ackermann). Also detects a cycle in an undirected edge list: union() returns
    False when both ends are already connected."""

    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank = {n: 0 for n in nodes}

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, x, y) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False  # already connected
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx  # attach the shorter tree under the taller one
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def connected(self, x, y) -> bool:
        return self.find(x) == self.find(y)


# =============================================================================
# 8. BINARY TREE RECURSION
# =============================================================================
# A tree is a graph with no cycles, so there's no visited set. The template is:
#   1) base case (None)  2) recurse left  3) recurse right  4) combine.
# Every function below is O(n) time and O(h) stack space, where h is the height.

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def tree_height(root: Optional[TreeNode]) -> int:
    """Number of nodes on the longest root-to-leaf path (empty tree = 0)."""
    if root is None:
        return 0
    return 1 + max(tree_height(root.left), tree_height(root.right))


def tree_diameter(root: Optional[TreeNode]) -> int:
    """Longest path between any two nodes, counted in EDGES. The helper returns height,
    and a closure variable tracks the best left+right seen at any node."""
    best = 0

    def height(node):
        nonlocal best
        if not node:
            return 0
        left, right = height(node.left), height(node.right)
        best = max(best, left + right)
        return 1 + max(left, right)

    height(root)
    return best


def lowest_common_ancestor(root, p, q):
    """LCA of nodes p and q (both assumed present). If p and q come back from different
    sides, this node is the split point."""
    if not root or root is p or root is q:
        return root
    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)
    if left and right:
        return root
    return left or right


def paths_to_target_sum(root, target) -> list[list]:
    """All root-to-leaf paths summing to target. Backtracking on a tree:
    append, recurse, pop. Copy the path (list(path)) when saving it."""
    results = []

    def dfs(node, remaining, path):
        if not node:
            return
        path.append(node.val)
        if not node.left and not node.right and remaining == node.val:
            results.append(list(path))
        else:
            dfs(node.left, remaining - node.val, path)
            dfs(node.right, remaining - node.val, path)
        path.pop()  # undo the choice

    dfs(root, target, [])
    return results


# =============================================================================
# 9. GRIDS ARE GRAPHS (cell = node, 4 neighbours = edges)
# =============================================================================

DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]


def num_islands(grid: list[list[str]]) -> int:
    """Count groups of connected "1" cells (connected components on a grid).
    Time O(rows * cols). Marks visited by overwriting cells, so it MUTATES the input;
    say so, or copy first. Iterative stack: a 1000x1000 all-land grid would blow the
    recursion limit with recursive DFS."""
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != "1":
                continue
            count += 1
            grid[r][c] = "#"
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                for dr, dc in DIRS:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "1":
                        grid[nr][nc] = "#"
                        stack.append((nr, nc))
    return count


def shortest_path_grid(grid: list[list[int]], start, end) -> int:
    """Fewest moves from start to end, where 0 = open and 1 = wall. Returns -1 if unreachable.
    This is BFS because every move costs 1. Time and space O(rows * cols)."""
    rows, cols = len(grid), len(grid[0])
    (sr, sc), (er, ec) = start, end
    if grid[sr][sc] == 1 or grid[er][ec] == 1:
        return -1
    visited = {(sr, sc)}
    queue = deque([(sr, sc, 0)])  # (row, col, distance)
    while queue:
        r, c, dist = queue.popleft()
        if (r, c) == (er, ec):
            return dist
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))
    return -1


# =============================================================================
# 10. BACKTRACKING: choose, recurse, un-choose
# =============================================================================
# Use it for "generate all": permutations, combinations, subsets, N-Queens, Sudoku.
# The output itself is exponential, so no trick makes it polynomial; pruning helps constants.

def permutations(nums) -> list[list]:
    """All orderings. O(n * n!) time. A `used` flag avoids slicing new lists each call."""
    result, current, used = [], [], [False] * len(nums)

    def backtrack():
        if len(current) == len(nums):
            result.append(list(current))  # copy, since current keeps changing
            return
        for i, num in enumerate(nums):
            if used[i]:
                continue
            used[i] = True
            current.append(num)
            backtrack()
            current.pop()  # undo the choice
            used[i] = False

    backtrack()
    return result


def subsets(nums) -> list[list]:
    """All 2^n subsets. O(n * 2^n). `start` prevents re-using earlier elements,
    so [1,2] and [2,1] aren't both produced."""
    result, current = [], []

    def backtrack(start):
        result.append(list(current))
        for i in range(start, len(nums)):
            current.append(nums[i])
            backtrack(i + 1)
            current.pop()

    backtrack(0)
    return result


# =============================================================================
# DEMO: asserts, so a broken edit fails loudly
# =============================================================================

if __name__ == "__main__":
    print("DFS recursive :", dfs_recursive(graph, "A"))
    assert dfs_recursive(graph, "A") == dfs_iterative(graph, "A") == ["A", "B", "D", "E", "F", "C"]

    print("BFS           :", bfs(graph, "A"))
    assert bfs(graph, "A") == ["A", "B", "C", "D", "E", "F"]

    print("Shortest A->F :", bfs_shortest_path(graph, "A", "F"))
    assert bfs_shortest_path(graph, "A", "F") == ["A", "C", "F"]
    assert bfs_shortest_path(graph, "A", "A") == ["A"]
    assert bfs_shortest_path({"A": [], "B": []}, "A", "B") == []

    print("Dijkstra from A:", dijkstra(weighted_graph, "A"))
    assert dijkstra(weighted_graph, "A") == {"A": 0, "B": 1, "C": 4, "D": 3, "E": 6, "F": 7}

    print("Cycle (undirected):", detect_cycle_undirected(graph))  # True: A-B-E-F-C-A
    assert detect_cycle_undirected(graph) is True
    assert detect_cycle_undirected(build_graph([("A", "B"), ("B", "C")])) is False

    dag = {"extract": ["stage"], "stage": ["dim_carrier", "fct_loads"],
           "dim_carrier": ["fct_loads"], "fct_loads": []}  # a dbt-style lineage graph
    cyclic = {"A": ["B"], "B": ["C"], "C": ["A"]}
    diamond = {"A": ["B", "C"], "B": ["D"], "C": ["D"]}
    assert detect_cycle_directed(cyclic) is True
    assert detect_cycle_directed(diamond) is False  # visited twice is not a cycle

    print("Topo (Kahn)   :", topological_sort_kahn(dag))
    print("Topo (DFS)    :", topological_sort_dfs(dag))
    for order in (topological_sort_kahn(dag), topological_sort_dfs(dag)):
        pos = {n: i for i, n in enumerate(order)}
        assert all(pos[u] < pos[v] for u in dag for v in dag[u])
    for fn in (topological_sort_kahn, topological_sort_dfs):
        try:
            fn(cyclic)
            raise AssertionError("cycle not detected")
        except ValueError:
            pass

    print("Components    :", connected_components(build_graph([(1, 2), (2, 3), (4, 5)])))
    assert connected_components(build_graph([(1, 2), (2, 3), (4, 5)])) == [[1, 2, 3], [4, 5]]

    uf = UnionFind("ABCD")
    uf.union("A", "B"); uf.union("C", "D")
    assert uf.connected("A", "B") and not uf.connected("A", "C")
    assert uf.union("B", "A") is False  # edge inside a component -> would form a cycle

    #        3
    #      /   \
    #     5     1
    #    / \
    #   6   2
    six, two = TreeNode(6), TreeNode(2)
    five = TreeNode(5, six, two)
    one = TreeNode(1)
    root = TreeNode(3, five, one)
    assert tree_height(root) == 3
    assert tree_diameter(root) == 3  # 6-5-3-1
    assert lowest_common_ancestor(root, six, two) is five
    assert lowest_common_ancestor(root, six, one) is root
    assert paths_to_target_sum(root, 14) == [[3, 5, 6]]

    islands = [
        ["1", "1", "0", "0", "0"],
        ["1", "1", "0", "0", "0"],
        ["0", "0", "1", "0", "0"],
        ["0", "0", "0", "1", "1"],
    ]
    print("Num islands   :", num_islands([row[:] for row in islands]))  # pass a copy
    assert num_islands([row[:] for row in islands]) == 3
    num_islands(islands)
    assert islands[0][0] == "#"  # without a copy the caller's grid is overwritten: the gotcha

    maze = [[0, 0, 0],
            [1, 1, 0],
            [0, 0, 0]]
    print("Grid BFS      :", shortest_path_grid(maze, (0, 0), (2, 0)))
    assert shortest_path_grid(maze, (0, 0), (2, 0)) == 6

    print("Permutations  :", permutations([1, 2, 3]))
    assert len(permutations([1, 2, 3])) == 6
    print("Subsets       :", subsets([1, 2, 3]))
    assert len(subsets([1, 2, 3])) == 8

    print("All asserts passed.")
