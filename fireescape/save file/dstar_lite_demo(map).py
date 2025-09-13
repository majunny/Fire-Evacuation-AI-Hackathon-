import sys, pygame
from function import *

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
ESCAPE_COLOR = (26, 188, 156) # 새로 추가 (민트색)
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

def auto_replan(blocked, agent_pos, goals, fire_cells, planner, ROWS, COLS, exclude_goal_idx=None):
    best_idx, best_goal, best_len = choose_best_goal(blocked, agent_pos, goals, ROWS, COLS, fire_cells)
    if best_goal is not None and best_len < float('inf'):
        if planner and best_goal == planner.goal:
            planner.update_start(agent_pos)
            return best_idx, planner, planner.compute_generator()
        new_planner = DStarLite(blocked, agent_pos, best_goal, ROWS, COLS)
        if fire_cells:
            for f_pos in fire_cells:
                new_planner.update_map_change(f_pos, True)
        plan_gen = new_planner.compute_generator()
        return best_idx, new_planner, plan_gen
    return None, None, None

def reset_all(map_filepath='mainmap.json'):
    # JSON 파일에서 맵 데이터 로드
    blocked, start, goals, escapes = load_map_from_json(map_filepath)

    # 맵 로드 실패 시 프로그램 종료
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
    active_goal_idx = None
    selected_goal_idx = 0
    mode = 1
    step_timer = 0.0
    fire_step_timer = 0.0
    replan_check_timer = 0.0
    periodic_replan_timer = 0.0
    dragging = False
    return (blocked, goals, escapes, fire_cells, start, agent_pos,
            planner, plan_gen, planning, auto_planning, path,
            active_goal_idx, selected_goal_idx, mode,
            step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
            dragging)

def main():
    (blocked, goals, escapes, fire_cells, start, agent_pos,
     planner, plan_gen, planning, auto_planning, path,
     active_goal_idx, selected_goal_idx, mode,
     step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
     dragging) = reset_all()

    # JSON에서 로드된 맵의 실제 크기를 반영
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

                elif e.key == pygame.K_1:
                    mode = 1
                elif e.key == pygame.K_2:
                    mode = 2
                elif e.key == pygame.K_3:
                    mode = 3
                elif e.key == pygame.K_4:
                    mode = 4

                elif e.key == pygame.K_g:
                    if goals:
                        selected_goal_idx = (selected_goal_idx + 1) % len(goals)

                elif e.key == pygame.K_SPACE:
                    if not auto_planning:
                        auto_planning = True
                        active_goal_idx, planner, plan_gen = auto_replan(
                            blocked, agent_pos, goals, fire_cells, planner, current_rows, current_cols
                        )
                        if planner is not None:
                            planning = True
                            path = []
                            step_timer = 0.0
                        else:
                            planning = False
                            plan_gen = None
                            path = []
                            print("현재 도달 가능한 목표가 없습니다. 자동 재탐색 대기...")
                        print("자동 계획 모드: ON")
                    else:
                        auto_planning = False
                        planning = False
                        plan_gen = None
                        path = []
                        active_goal_idx = None
                        print("자동 계획 모드: OFF")

                elif e.key == pygame.K_c:
                    print("전체 리셋합니다.")
                    (blocked, goals, escapes, fire_cells, start, agent_pos,
                     planner, plan_gen, planning, auto_planning, path,
                     active_goal_idx, selected_goal_idx, mode,
                     step_timer, fire_step_timer, replan_check_timer, periodic_replan_timer,
                     dragging) = reset_all()
                    skip_frame = True  

                elif e.key == pygame.K_r:
                    print("불을 지우고 에이전트 위치를 초기화합니다.")
                    for f_pos in fire_cells:
                        if inb(f_pos[0], f_pos[1], current_rows, current_cols):
                            blocked[f_pos[0]][f_pos[1]] = False
                    fire_cells = []
                    agent_pos = start
                    if auto_planning:
                        if active_goal_idx is not None:
                            planner = DStarLite(blocked, agent_pos, goals[active_goal_idx], current_rows, current_cols)
                            plan_gen = planner.compute_generator()
                            planning = True
                            path = []
                            step_timer = 0.0
                            print(f"기존 목표 {active_goal_idx + 1}로 재계획합니다.")
                        else:
                            active_goal_idx, planner, plan_gen = auto_replan(
                                blocked, agent_pos, goals, fire_cells, planner, current_rows, current_cols
                            )
                            if planner is not None:
                                planning = True
                                path = []
                                step_timer = 0.0
                            else:
                                planning = False
                                plan_gen = None
                                path = []
                    else:
                        planner = None
                        plan_gen = None
                        planning = False
                        path = []
                        step_timer = 0.0
                        active_goal_idx = None

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                rc = cell_at_pos(*e.pos, H, CELL, MARGIN, current_rows, current_cols)
                if rc:
                    r, c = rc
                    map_changed = False
                    if mode == 1 and not blocked[r][c] and (r, c) not in fire_cells:
                        agent_pos = (r, c); start = (r, c); map_changed = True
                    elif mode == 2 and not blocked[r][c] and goals and (r, c) not in fire_cells:
                        goals[selected_goal_idx] = (r, c); map_changed = True
                    elif mode == 3 and (r, c) != agent_pos and (r, c) not in goals:
                        if (r, c) in fire_cells:
                            fire_cells.remove((r, c))
                            if planner: planner.update_map_change((r, c), False)
                            print("불 제거 → 재평가")
                        elif not blocked[r][c]:
                            fire_cells.append((r, c))
                            if planner: planner.update_map_change((r, c), True)
                            print("불 추가 → 재계획")
                        map_changed = True
                    elif mode == 4:
                        if (r, c) not in fire_cells:
                            blocked[r][c] = not blocked[r][c]
                            if planner: planner.update_map_change((r, c), blocked[r][c])
                            dragging = True; map_changed = True
                    if map_changed and auto_planning and planner:
                        path = []; plan_gen = planner.compute_generator(); planning = True; step_timer = 0.0

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging = False

            elif e.type == pygame.MOUSEMOTION and dragging and mode == 4:
                rc = cell_at_pos(*e.pos, H, CELL, MARGIN, current_rows, current_cols)
                if rc:
                    r, c = rc
                    if not blocked[r][c] and (r, c) not in fire_cells:
                        blocked[r][c] = True
                        if planner: planner.update_map_change((r, c), True)
                        if auto_planning and planner:
                            path = []; plan_gen = planner.compute_generator(); planning = True; step_timer = 0.0

        if skip_frame:
            draw_all(
                screen, blocked, path, goals, escapes, start, agent_pos, active_goal_idx, selected_goal_idx, fire_cells,
                mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
                BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
                W, H, font
            )
            continue  

        # ===== 불 확산 =====
        if fire_cells and auto_planning:
            fire_step_timer += dt
            if fire_step_timer >= FIRE_STEP_INTERVAL:
                fire_step_timer -= FIRE_STEP_INTERVAL
                new_fire_cells = spread_fire(fire_cells, blocked, current_rows, current_cols)
                if new_fire_cells:
                    changed = False
                    path_set = set(path) if path else set()
                    for f_pos in new_fire_cells:
                        r, c = f_pos
                        if f_pos not in fire_cells and not blocked[r][c]:
                            fire_cells.append(f_pos); blocked[r][c] = True; changed = True
                            if planner: planner.update_map_change(f_pos, True)
                    intersects_path = any((f in path_set) for f in new_fire_cells)
                    next_blocked = False
                    if path:
                        try:
                            pi = path.index(agent_pos)
                            if pi + 1 < len(path):
                                nxt = path[pi + 1]; next_blocked = nxt in new_fire_cells
                        except ValueError:
                            pass
                    if changed:
                        if planner:
                            if intersects_path or next_blocked:
                                plan_gen = planner.compute_generator(); planning = True; path = []
                                print("불 확산 영향 → 재계획!")
                        else:
                            active_goal_idx, planner, plan_gen = auto_replan(
                                blocked, agent_pos, goals, fire_cells, None, current_rows, current_cols
                            )
                            if planner is not None:
                                planning = True; path = []; print("불 확산 → 초기 경로 계획!")

        # ===== 자동 재탐색 / 주기적 최적 경로 재검토 =====
        if auto_planning and not planning:
            replan_check_timer += dt
            if replan_check_timer >= REPLAN_CHECK_INTERVAL:
                replan_check_timer = 0.0
                active_goal_idx, planner, plan_gen = auto_replan(
                    blocked, agent_pos, goals, fire_cells, planner, current_rows, current_cols
                )
                if planner is not None:
                    planning = True; path = []; step_timer = 0.0
                    print("주기적 탐색 → 경로 발견!")

        if auto_planning and planning:
            periodic_replan_timer += dt
            if periodic_replan_timer >= REPLAN_PERIODIC_CHECK:
                periodic_replan_timer = 0.0
                new_active_idx, new_planner, new_plan_gen = auto_replan(
                    blocked, agent_pos, goals, fire_cells, planner, current_rows, current_cols
                )
                if new_planner is not None and new_active_idx != active_goal_idx:
                    active_goal_idx = new_active_idx; planner = new_planner; plan_gen = new_plan_gen; path = []
                    print(f"더 가까운 목표 {active_goal_idx + 1}로 전환")

        # ===== 계획 실행 =====
        if planning and plan_gen is not None:
            steps = 0
            try:
                while steps < PLANNER_STEPS_PER_FRAME:
                    next(plan_gen); steps += 1
            except StopIteration:
                path = planner.get_path(); plan_gen = None
                if not path and auto_planning:
                    print(f"목표 {active_goal_idx + 1 if active_goal_idx is not None else '?'} 실패 → 다른 목표")
                    new_active_idx, new_planner, new_plan_gen = auto_replan(
                        blocked, agent_pos, goals, fire_cells, None, current_rows, current_cols
                    )
                    if new_planner is not None:
                        active_goal_idx = new_active_idx; planner = new_planner; plan_gen = new_plan_gen; path = []
                        print(f"새 목표 {new_active_idx + 1}로 전환")
                    else:
                        print("도달 가능한 목표 없음 → 대기"); planning = False
                step_timer = 0.0

        # ===== 에이전트 이동 =====
        if planning and path and auto_planning:
            if agent_pos == path[-1]:
                print("목표 도달 → 정지"); planning = False; path = []
            else:
                step_timer += dt
                if step_timer >= STEP_INTERVAL:
                    step_timer -= STEP_INTERVAL
                    replan_needed = False
                    try:
                        current_path_idx = path.index(agent_pos)
                    except ValueError:
                        print("경로 이탈 → 재계획"); replan_needed = True
                        current_path_idx = -1
                    if not replan_needed and current_path_idx + 1 >= len(path):
                        print("경로 끝 → 재계획"); replan_needed = True
                    if not replan_needed:
                        next_pos = path[current_path_idx + 1]
                        if blocked[next_pos[0]][next_pos[1]]:
                            print("다음 칸 막힘 → 재계획"); replan_needed = True
                    if replan_needed:
                        if planner:
                            planner.update_start(agent_pos); plan_gen = planner.compute_generator(); path = []
                        else:
                            active_goal_idx, planner, plan_gen = auto_replan(
                                blocked, agent_pos, goals, fire_cells, None, current_rows, current_cols
                            )
                        if planner and planner.get_path():
                            path = planner.get_path(); print("우회 경로 찾음")
                        else:
                            print("기존 목표 막힘 → 다른 목표 탐색")
                            active_goal_idx, planner, plan_gen = auto_replan(
                                blocked, agent_pos, goals, fire_cells, None, current_rows, current_cols
                            )
                            if planner:
                                path = planner.get_path(); print(f"새 목표 {active_goal_idx + 1} 전환")
                            else:
                                planning = False; path = []; print("우회/새 경로 실패")
                        step_timer = 0.0
                    else:
                        agent_pos = path[current_path_idx + 1]
                        if planner: planner.update_start(agent_pos)

        # ===== 렌더링 =====
        draw_all(
            screen, blocked, path, goals, escapes, start, agent_pos, active_goal_idx, selected_goal_idx, fire_cells,
            mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
            BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
            W, H, font
        )

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()

