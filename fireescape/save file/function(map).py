import heapq, pygame, json

NEI4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
INF = 10**9

def inb(r, c, ROWS, COLS): 
    return 0 <= r < ROWS and 0 <= c < COLS

def manhattan(a, b): 
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# ---------- 빠른 목표 선택용 A* (길이만) ----------
# 불 위치도 장애물로 간주하도록 fire_cells 인자 추가
def astar_len(blocked, start, goal, ROWS, COLS, fire_cells=None):
    if not inb(goal[0], goal[1], ROWS, COLS) or blocked[goal[0]][goal[1]]: 
        return INF
    if fire_cells and (goal[0], goal[1]) in fire_cells: 
        return INF

    g = [[INF] * COLS for _ in range(ROWS)]
    g[start[0]][start[1]] = 0
    pq = [(manhattan(start, goal), 0, start)]
    while pq:
        _, cost, (r, c) = heapq.heappop(pq)
        if (r, c) == goal: 
            return cost
        if cost != g[r][c]: 
            continue
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, ROWS, COLS) and not blocked[nr][nc]:
                if fire_cells and (nr, nc) in fire_cells:
                    continue
                ncst = cost + 1
                if ncst < g[nr][nc]:
                    g[nr][nc] = ncst
                    heapq.heappush(pq, (ncst + manhattan((nr, nc), goal), ncst, (nr, nc)))
    return INF

# ---------- D* Lite ----------
class DStarLite:
    def __init__(self, blocked, start, goal, ROWS, COLS):
        # 2차원 배열 깊은 복사 (원본과 독립)
        self.blocked = [row[:] for row in blocked]
        self.start = start
        self.goal = goal
        self.ROWS = ROWS
        self.COLS = COLS

        self.g = [[INF] * COLS for _ in range(ROWS)]
        self.rhs = [[INF] * COLS for _ in range(ROWS)]
        self.rhs[goal[0]][goal[1]] = 0

        self.U = []
        self.km = 0
        self.last = start
        self._insert(goal, self._key(goal))

    def _key(self, s):
        r, c = s
        val = min(self.g[r][c], self.rhs[r][c])
        return (val + manhattan(self.start, s) + self.km, val)

    def _insert(self, s, k): 
        heapq.heappush(self.U, (k, s))

    def _top_key(self): 
        return self.U[0][0] if self.U else (INF, INF)

    def _update_vertex(self, s):
        r, c = s
        if s != self.goal:
            m = INF
            for dr, dc in NEI4:
                nr, nc = r + dr, c + dc
                if inb(nr, nc, self.ROWS, self.COLS) and not self.blocked[nr][nc]:
                    m = min(m, self.g[nr][nc] + 1)
            self.rhs[r][c] = m
        if self.g[r][c] != self.rhs[r][c]:
            self._insert(s, self._key(s))

    def _neighbors(self, s):
        r, c = s
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, self.ROWS, self.COLS) and not self.blocked[nr][nc]:
                yield (nr, nc)

    # 제너레이터: 한 스텝씩 실행해서 GUI 프리즈 방지 (빈 큐 보호 추가)
    def compute_generator(self):
        while True:
            # (보호) 큐가 비었는데 start 상태가 불일치하면 start를 큐에 넣어 진행 보장
            if not self.U and self.rhs[self.start[0]][self.start[1]] != self.g[self.start[0]][self.start[1]]:
                self._insert(self.start, self._key(self.start))

            # 종료 조건: 우선순위 조건/값 일치가 모두 만족되면 탈출
            if not (self._top_key() < self._key(self.start) or
                    self.rhs[self.start[0]][self.start[1]] != self.g[self.start[0]][self.start[1]]):
                break

            # 혹시라도 큐가 비어있으면 한 틱 양보
            if not self.U:
                yield
                continue

            (k_old, s) = heapq.heappop(self.U)
            if k_old > self._key(s):
                self._insert(s, self._key(s))
            elif self.g[s[0]][s[1]] > self.rhs[s[0]][s[1]]:
                self.g[s[0]][s[1]] = self.rhs[s[0]][s[1]]
                for n in self._neighbors(s):
                    self._update_vertex(n)
            else:
                old_g = self.g[s[0]][s[1]]
                self.g[s[0]][s[1]] = INF
                self._update_vertex(s)
                for n in self._neighbors(s):
                    if self.rhs[n[0]][n[1]] == old_g + 1:
                        self._update_vertex(n)
            yield
        yield

    def update_start(self, new_start):
        self.km += manhattan(self.last, new_start)
        self.last = new_start
        self.start = new_start

    # 지도 변경 반영 (이웃 4방향 강제 갱신으로 불변식 보장)
    def update_map_change(self, s, is_blocked):
        r, c = s
        was = self.blocked[r][c]
        self.blocked[r][c] = is_blocked
        if was == is_blocked:
            return

        # 바뀐 셀 자체 갱신
        self._update_vertex(s)

        # 네 방향 이웃 모두 갱신 (막힘 여부와 무관)
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, self.ROWS, self.COLS):
                self._update_vertex((nr, nc))

    def get_path(self):
        path = []
        cur = self.start
        visited = set()
        while cur != self.goal:
            path.append(cur)
            visited.add(cur)
            r, c = cur
            best, bestv = None, INF
            for dr, dc in NEI4:
                nr, nc = r + dr, c + dc
                if inb(nr, nc, self.ROWS, self.COLS) and not self.blocked[nr][nc] and self.g[nr][nc] < bestv:
                    bestv = self.g[nr][nc]
                    best = (nr, nc)
            if best is None or best in visited:
                return []
            cur = best
        path.append(self.goal)
        return path

# ---------- 불 확산 ----------
def spread_fire(fire_cells, blocked, ROWS, COLS):
    """
    기존 불의 모든 위치에서 인접한 곳으로 불을 퍼뜨린다.
    새로운 불 좌표 목록을 반환한다.
    """
    newly = set()
    cur = set(fire_cells)
    for r, c in fire_cells:
        for dr, dc in NEI4:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, ROWS, COLS) and not blocked[nr][nc] and (nr, nc) not in cur:
                newly.add((nr, nc))
    return list(newly)

# ---------- 시각화 ----------
def rc_to_cellrect(r, c, CELL, MARGIN):
    x = c * (CELL + MARGIN) + MARGIN
    y = r * (CELL + MARGIN) + MARGIN
    return x, y, CELL, CELL

def rc_center(r, c, CELL, MARGIN):
    x = c * (CELL + MARGIN) + MARGIN + CELL // 2
    y = r * (CELL + MARGIN) + MARGIN + CELL // 2
    return x, y

def draw_all(screen, blocked, path, goals, escapes, start, agent_pos, active_goal_idx, selected_goal_idx, fire_cells,
             mode, auto_planning, ROWS, COLS, CELL, MARGIN, BG, GRID, WALL,
             GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
             W, H, font):
    screen.fill(BG)
    # 격자/장애물
    for r in range(ROWS):
        for c in range(COLS):
            pygame.draw.rect(screen, GRID, rc_to_cellrect(r, c, CELL, MARGIN))
            if blocked[r][c]:
                pygame.draw.rect(screen, WALL, rc_to_cellrect(r, c, CELL, MARGIN))
    # 경로
    for r, c in path:
        x, y, _, _ = rc_to_cellrect(r, c, CELL, MARGIN)
        pygame.draw.rect(screen, PATH_COLOR, (x + 4, y + 4, CELL - 8, CELL - 8), border_radius=4)
    # 목표들
    for i, g in enumerate(goals):
        color = GOAL_COLORS[i % len(GOAL_COLORS)]
        x, y, _, _ = rc_to_cellrect(*g, CELL, MARGIN)
        pygame.draw.rect(screen, color, (x + 2, y + 2, CELL - 4, CELL - 4), border_radius=4)
        if active_goal_idx == i:
            pygame.draw.rect(screen, (0, 0, 0), (x + 1, y + 1, CELL - 2, CELL - 2), width=2, border_radius=5)
    
    # 탈출구 (새로운 부분)
    for e in escapes:
        x, y, _, _ = rc_to_cellrect(*e, CELL, MARGIN)
        pygame.draw.rect(screen, ESCAPE_COLOR, (x + 2, y + 2, CELL - 4, CELL - 4), border_radius=4)

    # 시작점
    x, y, _, _ = rc_to_cellrect(*start, CELL, MARGIN)
    pygame.draw.rect(screen, START_COLOR, (x + 2, y + 2, CELL - 4, CELL - 4), border_radius=4)
    # 불
    for r, c in fire_cells:
        cx, cy = rc_center(r, c, CELL, MARGIN)
        pygame.draw.circle(screen, FIRE_COLOR, (cx, cy), CELL // 2 - 3)
    # 에이전트
    cx, cy = rc_center(*agent_pos, CELL, MARGIN)
    pygame.draw.circle(screen, AGENT_COLOR, (cx, cy), CELL // 2 - 3)

    # 상태바
    bar = pygame.Rect(0, H, W, 40)
    pygame.draw.rect(screen, (250, 250, 250), bar)
    auto_status = "ON" if auto_planning else "OFF"
    msg = f"[1]Start [2]Edit Goal (G to cycle) [3]Fire [4]Obstacle | [SPACE] Auto Plan: {auto_status}  [R] Reset  [C] Clear | Active Goal: {(active_goal_idx + 1) if active_goal_idx is not None else '-'} / {len(goals)}"
    screen.blit(font.render(msg, True, TEXT_COLOR), (10, H + 10))
    mode_label = {1: "Place START", 2: "Edit GOAL (press G to select)", 3: "Place FIRE", 4: "Draw Obstacles"}.get(mode, "")
    auto_mode_text = " | Auto Planning: ACTIVE" if auto_planning else ""
    screen.blit(font.render(f"Mode: {mode_label}{auto_mode_text}", True, TEXT_COLOR), (10, H + 22))
    pygame.display.flip()

def cell_at_pos(px, py, H, CELL, MARGIN, ROWS, COLS):
    if py > H: 
        return None
    c = px // (CELL + MARGIN)
    r = py // (CELL + MARGIN)
    if not inb(r, c, ROWS, COLS): 
        return None
    return (r, c)

def choose_best_goal(blocked, start, goals, ROWS, COLS, fire_cells):
    """
    여러 개 goals 중 A* 길이가 가장 짧은 목표를 고른다.
    returns: (best_idx, best_goal_rc, best_len) 또는 (None, None, INF)
    """
    best_idx, best_goal, best_len = None, None, INF
    for i, g in enumerate(goals):
        L = astar_len(blocked, start, g, ROWS, COLS, fire_cells)
        if L < best_len:
            best_len = L
            best_goal = g
            best_idx = i
    return best_idx, best_goal, best_len

# ---------- 프리셋 벽 생성 함수 ----------
def build_blocked_with_presets(ROWS, COLS, presets):
    blocked = [[False] * COLS for _ in range(ROWS)]

    def _inb(r, c): 
        return 0 <= r < ROWS and 0 <= c < COLS

    for w in presets:
        k = w.get('kind')
        if k == 'rect':
            r0, c0, r1, c1 = w['r0'], w['c0'], w['r1'], w['c1']
            if r0 > r1: r0, r1 = r1, r0
            if c0 > c1: c0, c1 = c1, c0
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if _inb(r, c): 
                        blocked[r][c] = True
        elif k == 'hline':
            r, c0, c1 = w['r'], w['c0'], w['c1']
            if c0 > c1: c0, c1 = c1, c0
            for c in range(c0, c1 + 1):
                if _inb(r, c): 
                    blocked[r][c] = True
        elif k == 'vline':
            c, r0, r1 = w['c'], w['r0'], w['r1']
            if r0 > r1: r0, r1 = r1, r0
            for r in range(r0, r1 + 1):
                if _inb(r, c): 
                    blocked[r][c] = True
        else:
            pass
    return blocked

# ---------- JSON 맵 로드 함수 (새로 추가) ----------
def load_map_from_json(filepath):
    """
    JSON 파일에서 맵 데이터를 로드합니다.
    JSON 파일은 'blocked', 'start', 'goals', 'escapes' 키를 포함해야 합니다.
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        blocked = data['blocked']
        # JSON에서 리스트로 읽어온 좌표를 튜플로 변환
        start = tuple(data['start'])
        goals = [tuple(g) for g in data['goals']]
        # escapes 키가 없을 경우를 대비하여 기본값으로 빈 리스트 사용
        escapes = [tuple(e) for e in data.get('escapes', [])]

        # 데이터 유효성 기본 검사
        if not isinstance(blocked, list) or not isinstance(start, tuple) or not isinstance(goals, list):
            raise ValueError("JSON 파일의 맵 형식이 올바르지 않습니다.")
        
        print(f"맵 파일 '{filepath}'을(를) 성공적으로 로드했습니다.")
        return blocked, start, goals, escapes
    except FileNotFoundError:
        print(f"오류: 맵 파일을 찾을 수 없습니다: '{filepath}'")
        return None, None, None, None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"오류: 맵 파일 파싱 중 오류 발생 '{filepath}': {e}")
        return None, None, None, None

