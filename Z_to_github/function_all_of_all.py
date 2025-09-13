import heapq, pygame, json, serial, asyncio, threading, socket, contextlib, websockets
NEI4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
INF = 10**9

def inb(r, c, ROWS, COLS): 
    return 0 <= r < ROWS and 0 <= c < COLS

def manhattan(a, b): 
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar_len(blocked, start, goal, ROWS, COLS, fire_cells=None):
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
                    heapq.heappush(pq, (new_cost + manhattan((nr, nc), goal), new_cost, (nr, nc)))
    return INF

class DStarLite:
    def __init__(self, blocked, start, goal, ROWS, COLS):
        self.blocked = blocked
        self.start = start
        self.goal = goal
        self.ROWS = ROWS
        self.COLS = COLS
        self.g = [[INF] * COLS for _ in range(ROWS)]
        self.rhs = [[INF] * COLS for _ in range(ROWS)]
        self.km = 0
        self.U = []
        self.rhs[goal[0]][goal[1]] = 0
        heapq.heappush(self.U, (self.calculate_key(goal), goal))
    def calculate_key(self, s):
        val = min(self.g[s[0]][s[1]], self.rhs[s[0]][s[1]])
        return (val + manhattan(s, self.start) + self.km, val)
    def update_vertex(self, u):
        if u != self.goal:
            min_rhs = INF
            for dr, dc in NEI4:
                v = (u[0] + dr, u[1] + dc)
                if inb(v[0], v[1], self.ROWS, self.COLS) and not self.blocked[v[0]][v[1]]:
                    min_rhs = min(min_rhs, self.g[v[0]][v[1]] + 1)
            self.rhs[u[0]][u[1]] = min_rhs
        u_in_U = any(u == item[1] for item in self.U)
        if u_in_U:
            self.U = [item for item in self.U if item[1] != u]
            heapq.heapify(self.U)
        if self.g[u[0]][u[1]] != self.rhs[u[0]][u[1]]:
            heapq.heappush(self.U, (self.calculate_key(u), u))
    def compute_shortest_path(self):
        while self.U and (self.U[0][0] < self.calculate_key(self.start) or self.g[self.start[0]][self.start[1]] != self.rhs[self.start[0]][self.start[1]]):
            k_old, u = heapq.heappop(self.U)
            k_new = self.calculate_key(u)
            if k_old < k_new: heapq.heappush(self.U, (k_new, u))
            elif self.g[u[0]][u[1]] > self.rhs[u[0]][u[1]]:
                self.g[u[0]][u[1]] = self.rhs[u[0]][u[1]]
                for dr, dc in NEI4:
                    s = (u[0] + dr, u[1] + dc)
                    if inb(s[0], s[1], self.ROWS, self.COLS) and not self.blocked[s[0]][s[1]]: self.update_vertex(s)
            else:
                self.g[u[0]][u[1]] = INF
                self.update_vertex(u)
                for dr, dc in NEI4:
                    s = (u[0] + dr, u[1] + dc)
                    if inb(s[0], s[1], self.ROWS, self.COLS) and not self.blocked[s[0]][s[1]]: self.update_vertex(s)
    def compute_generator(self):
        yield from iter([None] * 1) 
        self.compute_shortest_path()
    def get_path(self):
        if self.g[self.start[0]][self.start[1]] == INF: return []
        path = [self.start]
        curr = self.start
        while curr != self.goal:
            min_cost, next_node = INF, None
            for dr, dc in NEI4:
                n = (curr[0] + dr, curr[1] + dc)
                if inb(n[0], n[1], self.ROWS, self.COLS):
                    cost = self.g[n[0]][n[1]] + 1
                    if cost < min_cost: min_cost, next_node = cost, n
            if next_node is None or next_node in path: return []
            path.append(next_node); curr = next_node
        return path
    def update_start(self, new_start): self.start = new_start
    def update_map_change(self, pos, is_blocked):
        self.blocked[pos[0]][pos[1]] = is_blocked; self.km += manhattan(self.start, pos); self.update_vertex(pos)


def find_best_target(blocked, start_pos, goals, escapes, ROWS, COLS, fire_cells=None):
    min_path_len = INF; best_immediate_target = None
    for escape_pos in escapes:
        path_len = astar_len(blocked, start_pos, escape_pos, ROWS, COLS, fire_cells)
        if path_len < min_path_len: min_path_len, best_immediate_target = path_len, escape_pos
    num_goal_colors = 5
    for i, goal_pos in enumerate(goals):
        partner_idx = i + num_goal_colors if i < num_goal_colors else i - num_goal_colors
        if not (0 <= partner_idx < len(goals)): continue
        partner_pos = goals[partner_idx]
        len_to_goal = astar_len(blocked, start_pos, goal_pos, ROWS, COLS, fire_cells)
        if len_to_goal == INF: continue
        for escape_pos in escapes:
            len_from_partner = astar_len(blocked, partner_pos, escape_pos, ROWS, COLS, fire_cells)
            if len_from_partner == INF: continue
            total_len = len_to_goal + len_from_partner
            if total_len < min_path_len: min_path_len, best_immediate_target = total_len, goal_pos
    if best_immediate_target is None:
        for goal_pos in goals:
            path_len = astar_len(blocked, start_pos, goal_pos, ROWS, COLS, fire_cells)
            if path_len < min_path_len: min_path_len, best_immediate_target = path_len, goal_pos
    return best_immediate_target, min_path_len

def spread_fire(fire_cells, blocked, ROWS, COLS):
    newly_burnt = []
    for r, c in fire_cells:
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, ROWS, COLS) and not blocked[nr][nc] and (nr, nc) not in fire_cells:
                newly_burnt.append((nr, nc))
    return list(set(newly_burnt))

def cell_at_pos(x, y, H, CELL, MARGIN, ROWS, COLS):
    if y > H: return None
    c = int(x / (CELL + MARGIN)); r = int(y / (CELL + MARGIN))
    if 0 <= r < ROWS and 0 <= c < COLS: return (r, c)
    return None
    
# ---------- [수정됨] draw_all 함수 (오브젝트 모양 변경) ----------
def draw_all(screen, blocked, path, goals, escapes, start, agent, current_target, selected_goal_idx, fire_cells, 
             mode, auto_planning, ROWS, COLS, CELL, MARGIN,
             BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
             W, H, font):

    screen.fill(BG)
    # 1. 배경 (그리드, 벽) 그리기
    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(c * (CELL + MARGIN) + MARGIN, r * (CELL + MARGIN) + MARGIN, CELL, CELL)
            color = GRID
            # 불은 나중에 그리므로 여기서는 벽만 그림
            if blocked[r][c] and (r,c) not in fire_cells : color = WALL
            pygame.draw.rect(screen, color, rect)

    # 2. 경로 그리기 (작은 원)
    if path:
        for p in path:
            center_x = p[1] * (CELL + MARGIN) + MARGIN + CELL // 2
            center_y = p[0] * (CELL + MARGIN) + MARGIN + CELL // 2
            pygame.draw.circle(screen, PATH_COLOR, (center_x, center_y), CELL // 5)

    # 3. 시작 지점 그리기 (다이아몬드)
    start_rect = pygame.Rect(start[1] * (CELL + MARGIN) + MARGIN, start[0] * (CELL + MARGIN) + MARGIN, CELL, CELL)
    pygame.draw.polygon(screen, START_COLOR, [
        start_rect.midtop, start_rect.midright, start_rect.midbottom, start_rect.midleft
    ])

    # 4. 목표(계단) 그리기
    for i, g in enumerate(goals):
        color_idx = i % len(GOAL_COLORS)
        rect = pygame.Rect(g[1] * (CELL + MARGIN) + MARGIN, g[0] * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, GOAL_COLORS[color_idx], rect)
        # 계단 모양 아이콘 추가
        for j in range(1, 4):
            y = rect.top + j * (CELL // 4)
            pygame.draw.line(screen, (255,255,255), (rect.left + 4, y), (rect.right - 4, y), 2)
        
        if auto_planning and g == current_target:
             pygame.draw.rect(screen, (255, 255, 255), rect, 3)
        elif not auto_planning and i == selected_goal_idx:
             pygame.draw.rect(screen, (231, 76, 60), rect, 3)

    # 5. 탈출구 그리기
    for e in escapes:
        rect = pygame.Rect(e[1] * (CELL + MARGIN) + MARGIN, e[0] * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, ESCAPE_COLOR, rect)
        # 탈출구 모양 아이콘 (삼각형) 추가
        pygame.draw.polygon(screen, (255,255,255), [
            (rect.centerx, rect.top + 5),
            (rect.left + 5, rect.bottom - 5),
            (rect.right - 5, rect.bottom - 5)
        ])
        if auto_planning and e == current_target:
             pygame.draw.rect(screen, (255, 255, 255), rect, 3)

    # 6. 불 그리기 (원)
    for r,c in fire_cells:
        center_x = c * (CELL + MARGIN) + MARGIN + CELL // 2
        center_y = r * (CELL + MARGIN) + MARGIN + CELL // 2
        pygame.draw.circle(screen, FIRE_COLOR, (center_x, center_y), CELL // 2)

    # 7. 에이전트 그리기 (원)
    agent_rect = pygame.Rect(agent[1] * (CELL + MARGIN) + MARGIN, agent[0] * (CELL + MARGIN) + MARGIN, CELL, CELL)
    pygame.draw.circle(screen, AGENT_COLOR, agent_rect.center, CELL // 2 - 2)
    
    # 8. 상태 텍스트 표시
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
        if not isinstance(blocked, list) or not isinstance(start, tuple) or not isinstance(goals, list):
            raise ValueError("JSON 파일의 맵 형식이 올바르지 않습니다.")
        return blocked, start, goals, escapes
    except FileNotFoundError: return None, None, None, None
    except (json.JSONDecodeError, KeyError, ValueError) as e: return None, None, None, None

def blocked_to_preset(blocked):


    ROWS = len(blocked)
    COLS = len(blocked[0])
    presets = []

    # 가로줄(hline) 스캔
    for r in range(ROWS):
        c = 0
        while c < COLS:
            if blocked[r][c]:
                c0 = c
                while c+1 < COLS and blocked[r][c+1]:
                    c += 1
                c1 = c
                presets.append({'kind': 'hline', 'r': r , 'c0': c0, 'c1': c1})
            c += 1

    # 세로줄(vline) 스캔
    for c in range(COLS):
        r = 0
        while r < ROWS:
            if blocked[r][c]:
                r0 = r
                while r+1 < ROWS and blocked[r+1][c]:
                    r += 1
                r1 = r
                if r1 > r0:  # 길이가 2 이상일 때만 추가
                    presets.append({'kind': 'vline', 'c': c, 'r0': r0, 'r1': r1})
            r += 1

    print(presets)

    return presets

#==========================================================New!================================================================================

# 피코 연결 함수
def connect_picos(ports):
    return [serial.Serial(port, 115200, timeout=1) for port in ports]

# 명령어 전송 함수 (2개 피코에 동시에 전송)
def send_command(picos, command: str):
    for pico in picos:
        pico.write((command + "\n").encode())

def _get_lan_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8765, interval=0.2):
        self.host, self.port, self.interval = host, port, interval
        self._direction = "NONE"
        self._clients = set()
        self._stop_flag = threading.Event()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop_flag.set()

    def set_direction(self, direction: str):
        self._direction = direction

    async def _handler(self, ws):
        self._clients.add(ws)
        try:
            async for _ in ws: pass
        finally:
            self._clients.discard(ws)

    async def _broadcast_task(self):
        while not self._stop_flag.is_set():
            for ws in list(self._clients):
                try:
                    await ws.send(self._direction)
                except:
                    self._clients.discard(ws)
            await asyncio.sleep(self.interval)

    async def _amain(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(f"📡 ws://{_get_lan_ip()}:{self.port}")
            broadcaster = asyncio.create_task(self._broadcast_task())
            try:
                while not self._stop_flag.is_set():
                    await asyncio.sleep(0.2)
            finally:
                broadcaster.cancel()
                with contextlib.suppress(Exception): await broadcaster

    def _run(self):
        asyncio.run(self._amain())