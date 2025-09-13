import heapq, pygame, json

# 인접 셀 (상, 하, 좌, 우)
NEI4 = [(1, 0), (-1, 0), (0, 1), (0, -1)] 
INF = 10**9

def inb(r, c, ROWS, COLS): 
    """
    주어진 좌표가 맵 경계 내에 있는지 확인합니다.
    """
    return 0 <= r < ROWS and 0 <= c < COLS

def manhattan(a, b): 
    """
    두 좌표 간의 맨해튼 거리를 계산합니다.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar_len(blocked, start, goal, ROWS, COLS, fire_cells=None):
    """
    A* 알고리즘을 사용하여 경로의 길이를 계산합니다.
    """
    if not inb(start[0], start[1], ROWS, COLS) or not inb(goal[0], goal[1], ROWS, COLS):
        return INF
    if blocked[start[0]][start[1]] or blocked[goal[0]][goal[1]]: 
        return INF
    if fire_cells and (start in fire_cells or goal in fire_cells):
        return INF

    g = [[INF] * COLS for _ in range(ROWS)]
    g[start[0]][start[1]] = 0
    pq = [(manhattan(start, goal), 0, start)]
    while pq:
        _, cost, (r, c) = heapq.heappop(pq)
        if (r, c) == goal: 
            return cost
        if cost > g[r][c]: 
            continue
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            is_fire = fire_cells and (nr, nc) in fire_cells
            if inb(nr, nc, ROWS, COLS) and not blocked[nr][nc] and not is_fire:
                new_cost = cost + 1
                if new_cost < g[nr][nc]:
                    g[nr][nc] = new_cost
                    priority = new_cost + manhattan((nr, nc), goal)
                    heapq.heappush(pq, (priority, new_cost, (nr, nc)))
    return INF

class DStarLite:
    """
    D* Lite 알고리즘을 구현하는 클래스.
    """
    def __init__(self, ROWS, COLS, start, goal, blocked):
        self.ROWS = ROWS
        self.COLS = COLS
        self.start = start
        self.goal = goal
        self.blocked = blocked
        self.g = [[INF] * self.COLS for _ in range(self.ROWS)]
        self.rhs = [[INF] * self.COLS for _ in range(self.ROWS)]
        self.key_m = 0
        self.U = []
        
        self.rhs[self.goal[0]][self.goal[1]] = 0
        heapq.heappush(self.U, (self.calculate_key(self.goal), self.goal))

    def calculate_key(self, s):
        k1 = min(self.g[s[0]][s[1]], self.rhs[s[0]][s[1]]) + manhattan(self.start, s) + self.key_m
        k2 = min(self.g[s[0]][s[1]], self.rhs[s[0]][s[1]])
        return (k1, k2)

    def update_vertex(self, u):
        if self.g[u[0]][u[1]] != self.rhs[u[0]][u[1]]:
            if u not in [item[1] for item in self.U]:
                heapq.heappush(self.U, (self.calculate_key(u), u))
            else:
                for i, item in enumerate(self.U):
                    if item[1] == u:
                        self.U[i] = (self.calculate_key(u), u)
                        heapq.heapify(self.U)
                        break
        else:
            if u in [item[1] for item in self.U]:
                self.U = [item for item in self.U if item[1] != u]
                heapq.heapify(self.U)

    def compute(self):
        while self.U and self.U[0][0] < self.calculate_key(self.start) or self.rhs[self.start[0]][self.start[1]] != self.g[self.start[0]][self.start[1]]:
            k_old, u = heapq.heappop(self.U)
            if k_old < self.calculate_key(u):
                heapq.heappush(self.U, (self.calculate_key(u), u))
            elif self.g[u[0]][u[1]] > self.rhs[u[0]][u[1]]:
                self.g[u[0]][u[1]] = self.rhs[u[0]][u[1]]
                for v_dr, v_dc in NEI4:
                    v = (u[0] + v_dr, u[1] + v_dc)
                    if inb(v[0], v[1], self.ROWS, self.COLS) and not self.blocked[v[0]][v[1]]:
                        if v != self.goal:
                            self.rhs[v[0]][v[1]] = min(self.rhs[v[0]][v[1]], self.g[u[0]][u[1]] + 1)
                        self.update_vertex(v)
            else:
                self.g[u[0]][u[1]] = INF
                self.update_vertex(u)
                for v_dr, v_dc in NEI4:
                    v = (u[0] + v_dr, u[1] + v_dc)
                    if inb(v[0], v[1], self.ROWS, self.COLS) and not self.blocked[v[0]][v[1]]:
                        if v != self.goal:
                            self.rhs[v[0]][v[1]] = min(self.rhs[v[0]][v[1]], self.g[u[0]][u[1]] + 1)
                        self.update_vertex(v)
    
    def compute_generator(self):
        self.compute()
        path = []
        if self.g[self.start[0]][self.start[1]] == INF: return path
        
        curr = self.start
        while curr != self.goal:
            path.append(curr)
            min_cost = INF
            next_node = None
            for dr, dc in NEI4:
                neighbor = (curr[0] + dr, curr[1] + dc)
                if inb(neighbor[0], neighbor[1], self.ROWS, self.COLS) and not self.blocked[neighbor[0]][neighbor[1]]:
                    cost = self.g[neighbor[0]][neighbor[1]] + 1
                    if cost < min_cost:
                        min_cost = cost
                        next_node = neighbor
            if not next_node: break
            curr = next_node
        path.append(self.goal)
        return path

    def replan(self):
        self.key_m += manhattan(self.start, self.start)
        self.compute()

    def update_start(self, new_start):
        self.start = new_start
        self.replan()
    
    def update_blocked_state(self, pos, is_blocked):
        if self.blocked[pos[0]][pos[1]] == is_blocked: return
        self.key_m += manhattan(self.start, self.start)
        self.blocked[pos[0]][pos[1]] = is_blocked
        self.update_vertex(pos)
        self.replan()
    
    def update_fire_state(self, pos, is_fire):
        self.key_m += manhattan(self.start, self.start)
        # Assuming `is_fire` is handled as a separate state
        self.replan()

def draw_grid(screen, blocked, path, goals, escapes, fire_cells, ROWS, COLS, CELL, MARGIN,
              GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, PATH_COLOR, FIRE_COLOR):
    """
    모든 그리드 셀을 그립니다.
    """
    for row in range(ROWS):
        for col in range(COLS):
            color = GRID
            cell_pos = (col * (CELL + MARGIN) + MARGIN, row * (CELL + MARGIN) + MARGIN)
            if blocked[row][col]:
                color = WALL
            elif (row, col) in fire_cells:
                color = FIRE_COLOR
            elif (row, col) in path:
                color = PATH_COLOR
            
            goal_idx = -1
            if (row, col) in goals:
                goal_idx = goals.index((row, col))
                color = GOAL_COLORS[goal_idx % len(GOAL_COLORS)]
            elif (row, col) in escapes:
                color = ESCAPE_COLOR

            pygame.draw.rect(screen, color, (*cell_pos, CELL, CELL), border_radius=5)
            
            # Goal 아이콘 추가
            if goal_idx != -1:
                goal_text = str(goal_idx + 1)
                text_surf = pygame.font.Font(None, 20).render(goal_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(cell_pos[0] + CELL // 2, cell_pos[1] + CELL // 2))
                screen.blit(text_surf, text_rect)

def draw_all(screen, blocked, path, goals, escapes, start, agent_pos, current_target, selected_goal_idx, fire_cells,
             mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
             BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
             W, H, font):
    """
    전체 화면을 렌더링하는 함수입니다.
    """
    screen.fill(BG)
    
    # 1. 그리드 그리기
    draw_grid(
        screen, blocked, path, goals, escapes, fire_cells, current_rows, current_cols, CELL, MARGIN,
        GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, PATH_COLOR, FIRE_COLOR
    )

    # 2. 시작점과 에이전트 그리기
    start_pos = (start[1] * (CELL + MARGIN) + MARGIN, start[0] * (CELL + MARGIN) + MARGIN)
    agent_pos_pix = (agent_pos[1] * (CELL + MARGIN) + MARGIN, agent_pos[0] * (CELL + MARGIN) + MARGIN)
    pygame.draw.rect(screen, START_COLOR, (*start_pos, CELL, CELL), border_radius=5)
    
    agent_rect = pygame.Rect(agent_pos_pix[0], agent_pos_pix[1], CELL, CELL)
    pygame.draw.circle(screen, AGENT_COLOR, agent_rect.center, CELL // 2 - 2)

    # 3. 상태 텍스트 표시
    status_text = f"Mode: {['Agent', 'Goal', 'Fire', 'Wall'][mode-1]} | Auto Planning: {'ON' if auto_planning else 'OFF'}"
    if not auto_planning and goals:
        status_text += f" | Selected Goal: {selected_goal_idx + 1}"
    
    if auto_planning:
        target_str = "Searching..."
        if current_target:
            if current_target in goals:
                target_str = f"Stair {goals.index(current_target) + 1}"
            elif current_target in escapes:
                target_str = "Escape"
        elif not any(escapes) and not any(goals):
             target_str = "No Target"
        status_text += f" | Current Target: {target_str}"

    text_surf = font.render(status_text, True, TEXT_COLOR)
    screen.blit(text_surf, (10, H + 10))

    pygame.display.flip()

def load_map_from_json(filepath):
    try:
        with open(filepath, 'r') as f: data = json.load(f)
        blocked = data['blocked']
        start = tuple(data['start'])
        goals = [tuple(g) for g in data['goals']]
        escapes = [tuple(e) for e in data.get('escapes', [])]
        if not isinstance(blocked, list) or not isinstance(start, tuple):
            raise ValueError("Invalid map data format")
        return blocked, start, goals, escapes
    except FileNotFoundError:
        print(f"Error: Map file not found at '{filepath}'. Please check the file path.")
        raise
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{filepath}'. Please check the file content.")
        raise
