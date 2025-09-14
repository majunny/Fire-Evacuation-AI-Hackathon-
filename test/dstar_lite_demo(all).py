import sys, pygame
from function_all import *

# ===== 설정 =====
CELL = 22
ROWS = 40 
COLS = 70 
MARGIN = 1
FPS = 60
STEP_INTERVAL = 0.3
PLANNER_STEPS_PER_FRAME = 10000
REPLAN_CHECK_INTERVAL = 0.5
REPLAN_PERIODIC_CHECK = 1.0

BG = (245, 246, 248)
GRID = (220, 223, 230)
WALL = (60, 72, 88)
ESCAPE_COLOR = (26, 188, 156)
START_COLOR = (52, 152, 219)
PATH_COLOR = (155, 89, 182)
AGENT_COLOR = (231, 76, 60)
FIRE_COLOR = (231, 100, 20)
TEXT_COLOR = (33, 33, 33)

GOAL_COLORS = [
    (0, 141, 98),
    (241, 196, 15),
    (250, 153, 204),
    (119, 109, 97),
    (153, 134, 179),
]

W = COLS * CELL + (COLS + 1) * MARGIN
H = ROWS * CELL + (ROWS + 1) * MARGIN

pygame.init()
screen = pygame.display.set_mode((W, H + 40))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 16)

# ---------- auto_replan 함수 (이전과 동일) ----------
def auto_replan(blocked, agent_pos, goals, escapes, fire_cells, planner, ROWS, COLS):
    best_target, best_len = find_best_target(blocked, agent_pos, goals, escapes, ROWS, COLS, fire_cells)
    
    if best_target is not None and best_len < float('inf'):
        if planner and best_target == planner.goal:
            planner.update_start(agent_pos)
            return best_target, planner, planner.compute_generator()
        
        new_planner = DStarLite(blocked, agent_pos, best_target, ROWS, COLS)
        if fire_cells:
            for f_pos in fire_cells:
                new_planner.update_map_change(f_pos, True)
        plan_gen = new_planner.compute_generator()
        return best_target, new_planner, plan_gen
        
    return None, None, None

def reset_all(map_filepath='test/mainmap.json'):
    blocked, start, goals, escapes = load_map_from_json(map_filepath)

    if blocked is None:
        print("맵 로드에 실패하여 프로그램을 종료합니다.")
        pygame.quit()
        sys.exit()

    fire_cells = []
    agent_pos = start
    planner = None
    plan_gen = None
    planning = False
    auto_planning = False
    path = []
    current_target = None
    selected_goal_idx = 0
    mode = 1
    step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer = 0.0, 0.0, 0.0, 0.0
    dragging = False
    just_teleported = False
    
    return (blocked, goals, escapes, fire_cells, start, agent_pos,
            planner, plan_gen, planning, auto_planning, path,
            current_target, selected_goal_idx, mode,
            step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
            dragging, just_teleported)

def main():
    (blocked, goals, escapes, fire_cells, start, agent_pos,
     planner, plan_gen, planning, auto_planning, path,
     current_target, selected_goal_idx, mode,
     step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
     dragging, just_teleported) = reset_all()

    current_rows = len(blocked)
    current_cols = len(blocked[0]) if current_rows > 0 else 0

    FIRE_STEP_INTERVAL = 1.0
    skip_frame = False 

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        skip_frame = False  

        # ===== 이벤트 처리 =====
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                
                # ---------- [수정됨] 모드 변경 기능 복원 ----------
                elif e.key == pygame.K_1: mode = 1
                elif e.key == pygame.K_2: mode = 2
                elif e.key == pygame.K_3: mode = 3
                elif e.key == pygame.K_4: mode = 4
                
                # ---------- [수정됨] G키 목표 선택 기능 복원 ----------
                elif e.key == pygame.K_g:
                    if goals:
                        selected_goal_idx = (selected_goal_idx + 1) % len(goals)

                elif e.key == pygame.K_m:
                    print('역시 마준이야')

                elif e.key == pygame.K_k:
                    print('역시 민성이형이야')

                elif e.key == pygame.K_i:

                    json_string = json.dumps(blocked)
                    print(json_string)

                elif e.key == pygame.K_SPACE:
                    if not auto_planning:
                        auto_planning = True
                        current_target, planner, plan_gen = auto_replan(
                            blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                        )
                        if planner is not None:
                            planning = True; path = []; step_timer = 0.0
                        else:
                            planning = False; plan_gen = None; path = []
                            print("현재 도달 가능한 목표/탈출구가 없습니다. 자동 재탐색 대기...")
                        print("자동 계획 모드: ON")
                    else:
                        auto_planning = False; planning = False; plan_gen = None; path = []; current_target = None
                        print("자동 계획 모드: OFF")

                elif e.key == pygame.K_q:
                    blocked_to_preset(blocked)

                elif e.key == pygame.K_c:
                    (blocked, goals, escapes, fire_cells, start, agent_pos,
                     planner, plan_gen, planning, auto_planning, path,
                     current_target, selected_goal_idx, mode,
                     step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
                     dragging, just_teleported) = reset_all()
                    skip_frame = True
            
            # ---------- [수정됨] 마우스 클릭/드래그 기능 전체 복원 ----------
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                rc = cell_at_pos(*e.pos, H, CELL, MARGIN, current_rows, current_cols)
                if rc:
                    r, c = rc
                    map_changed = False
                    # Mode 1: 에이전트 위치 설정
                    if mode == 1 and not blocked[r][c] and (r, c) not in fire_cells:
                        agent_pos = (r, c); start = (r, c); map_changed = True
                    # Mode 2: 선택된 목표(계단) 위치 설정
                    elif mode == 2 and not blocked[r][c] and goals and (r, c) not in fire_cells:
                        goals[selected_goal_idx] = (r, c); map_changed = True
                    # Mode 3: 불 설정/제거
                    elif mode == 3 and (r, c) != agent_pos and (r, c) not in goals:
                        if (r, c) in fire_cells:
                            fire_cells.remove((r, c))
                            blocked[r][c] = False # 다시 걸을 수 있도록
                            if planner: planner.update_map_change((r, c), False)
                        elif not blocked[r][c]:
                            fire_cells.append((r, c))
                            blocked[r][c] = True # 불은 장애물
                            if planner: planner.update_map_change((r, c), True)
                        map_changed = True
                    # Mode 4: 벽 설치/제거
                    elif mode == 4:
                        if (r, c) not in fire_cells and (r,c) != agent_pos and (r,c) not in goals:
                             blocked[r][c] = not blocked[r][c]
                             if planner: planner.update_map_change((r, c), blocked[r][c])
                             dragging = True; map_changed = True
                    
                    # 자동 계획 중에 맵이 바뀌면 즉시 재탐색
                    if map_changed and auto_planning and planner:
                        path = []; plan_gen = planner.compute_generator(); planning = True; step_timer = 0.0

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging = False

            elif e.type == pygame.MOUSEMOTION and dragging and mode == 4:
                rc = cell_at_pos(*e.pos, H, CELL, MARGIN, current_rows, current_cols)
                if rc:
                    r, c = rc
                    if not blocked[r][c] and (r,c) not in fire_cells and (r,c) != agent_pos and (r,c) not in goals:
                        blocked[r][c] = True
                        if planner: planner.update_map_change((r, c), True)
                        if auto_planning and planner:
                            path = []; plan_gen = planner.compute_generator(); planning = True; step_timer = 0.0

        if skip_frame:
            draw_all(screen, blocked, path, goals, escapes, start, agent_pos, current_target, selected_goal_idx, fire_cells,
                     mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
                     BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR, W, H, font)
            continue
            
        # ===== 불 확산 (이전 코드와 동일) =====
        if fire_cells and auto_planning:
            fire_step_timer += dt
            if fire_step_timer >= FIRE_STEP_INTERVAL:
                fire_step_timer -= FIRE_STEP_INTERVAL
                new_fire_cells = spread_fire(fire_cells, blocked, current_rows, current_cols)
                teleported_fire = set()
                if new_fire_cells and goals:
                    for f_pos in new_fire_cells:
                        if f_pos in goals:
                            try:
                                reached_goal_idx = goals.index(f_pos)
                                num_goal_colors = len(GOAL_COLORS)
                                partner_idx = reached_goal_idx + num_goal_colors if reached_goal_idx < num_goal_colors else reached_goal_idx - num_goal_colors
                                if 0 <= partner_idx < len(goals):
                                    partner_pos = goals[partner_idx]
                                    if partner_pos not in fire_cells and not blocked[partner_pos[0]][partner_pos[1]]:
                                        teleported_fire.add(partner_pos)
                            except ValueError: continue
                if teleported_fire: new_fire_cells.extend(list(teleported_fire))

                if new_fire_cells:
                    changed = False
                    for f_pos in new_fire_cells:
                        if f_pos not in fire_cells and not blocked[f_pos[0]][f_pos[1]]:
                            fire_cells.append(f_pos); blocked[f_pos[0]][f_pos[1]] = True; changed = True
                            if planner: planner.update_map_change(f_pos, True)
                    if changed and planner:
                        plan_gen = planner.compute_generator(); planning = True; path = []

        # ===== 자동 재탐색 / 주기적 최적 경로 재검토 (이전 코드와 동일) =====
        if auto_planning and not planning:
            replan_check_timer += dt
            if replan_check_timer >= REPLAN_CHECK_INTERVAL:
                replan_check_timer = 0.0
                current_target, planner, plan_gen = auto_replan(
                    blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                )
                if planner is not None:
                    planning = True; path = []; step_timer = 0.0
                    print("주기적 탐색 → 경로 발견!")

        if auto_planning and planning:
            periodic_replan_timer += dt
            if periodic_replan_timer >= REPLAN_PERIODIC_CHECK:
                periodic_replan_timer = 0.0
                new_target, new_planner, new_plan_gen = auto_replan(
                    blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                )
                if new_planner is not None and new_target != current_target:
                    current_target = new_target; planner = new_planner; plan_gen = new_plan_gen; path = []
                    target_type = "탈출구" if new_target in escapes else "계단"
                    print(f"더 효율적인 경로 발견 → 목표({target_type}) 변경")

        # ===== 계획 실행 (이전 코드와 동일) =====
        if planning and plan_gen is not None:
            # D* Lite 계산을 프레임당 한 번씩 조금씩 수행
            try:
                for _ in range(PLANNER_STEPS_PER_FRAME):
                    next(plan_gen)
            except StopIteration:
                path = planner.get_path(); plan_gen = None
                if not path and auto_planning:
                    new_target, new_planner, new_plan_gen = auto_replan(
                        blocked, agent_pos, goals, escapes, fire_cells, None, current_rows, current_cols
                    )
                    if new_planner is not None:
                        current_target = new_target; planner = new_planner; plan_gen = new_plan_gen; path = []
                    else:
                        planning = False
                step_timer = 0.0
        
        # ===== 에이전트 이동 (이전 코드와 동일) =====
        if planning and path and auto_planning:
            if agent_pos == path[-1]: # 경로의 끝에 도달
                if agent_pos in goals and not just_teleported:
                    reached_goal_idx = goals.index(agent_pos)
                    num_goal_colors = len(GOAL_COLORS)
                    partner_idx = reached_goal_idx + num_goal_colors if reached_goal_idx < num_goal_colors else reached_goal_idx - num_goal_colors
                    if 0 <= partner_idx < len(goals):
                        agent_pos = goals[partner_idx]; just_teleported = True
                        planner = None
                        current_target, planner, plan_gen = auto_replan(
                            blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                        )
                        if planner is not None: path = []; planning = True; step_timer = 0.0
                        else: planning = False; path = []
                elif agent_pos in escapes:
                    print("탈출 성공!"); auto_planning = False; planning = False; path = []
                else: planning = False; path = []
            else: # 경로 따라 이동
                step_timer += dt
                if step_timer >= STEP_INTERVAL:
                    step_timer -= STEP_INTERVAL
                    try:
                        current_path_idx = path.index(agent_pos)
                        next_pos = path[current_path_idx + 1]
                        if blocked[next_pos[0]][next_pos[1]]:
                            if planner: plan_gen = planner.compute_generator(); path = []
                        else:
                            agent_pos = next_pos
                            if planner: planner.update_start(agent_pos)
                            if agent_pos not in goals: just_teleported = False
                    except (ValueError, IndexError):
                        if planner: plan_gen = planner.compute_generator(); path = []

        # ===== 렌더링 =====
        draw_all(
            screen, blocked, path, goals, escapes, start, agent_pos, current_target, selected_goal_idx, fire_cells,
            mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
            BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
            W, H, font
        )

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()

