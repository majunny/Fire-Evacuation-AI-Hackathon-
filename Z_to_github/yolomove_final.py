import sys, pygame, cv2
from ultralytics import YOLO
from function_all_of_all import *
import time

#NEW!
# For macOS, change "COM4" to the appropriate device name, e.g., "/dev/tty.usbmodemXXXX"
PICO_PORTS = ["/dev/cu.usbmodem13201"]

# ===== Settings =====
CELL = 22
ROWS = 40 
COLS = 70 
MARGIN = 1
FPS = 60
PLANNER_STEPS_PER_FRAME = 10000
REPLAN_CHECK_INTERVAL = 0.5
REPLAN_PERIODIC_CHECK = 1.0
FIRE_STEP_INTERVAL = 1.0

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

# ---------- auto_replan function (same as before) ----------

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

def reset_all(map_filepath='mainmap.json'):
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
    fire_step_timer, replan_check_timer, periodic_replan_timer = 0.0, 0.0, 0.0
    dragging = False
    just_teleported = False
    
    return (blocked, goals, escapes, fire_cells, start, agent_pos,
            planner, plan_gen, planning, auto_planning, path,
            current_target, selected_goal_idx, mode,
            fire_step_timer, replan_check_timer, periodic_replan_timer,
            dragging, just_teleported)

def main():
    # ===== YOLO and webcam initialization =====
    try:
        yolo_model = YOLO("last.pt")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise IOError("웹캠을 열 수 없습니다.")
        print("YOLO 모델 및 웹캠 초기화 완료.")
    except Exception as e:
        print(f"YOLO 또는 웹캠 초기화 중 오류 발생: {e}")
        pygame.quit()
        sys.exit(0)

    (blocked, goals, escapes, fire_cells, start, agent_pos,
     planner, plan_gen, planning, auto_planning, path,
     current_target, selected_goal_idx, mode,
     fire_step_timer, replan_check_timer, periodic_replan_timer,
     dragging, just_teleported) = reset_all()

    # Start WebSocket Server for Kotlin communication
    ws_handler = WebSocketServer()
    ws_handler.start()

    current_rows = len(blocked)
    current_cols = len(blocked[0]) if current_rows > 0 else 0
    
    # Store the previous position of the recognized object
    prev_bald_pos = None

    picos = connect_picos(PICO_PORTS)
    time.sleep(0.5)  # 연결 안정화

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ===== Event handling =====
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_1: mode = 1
                elif e.key == pygame.K_2: mode = 2
                elif e.key == pygame.K_3: mode = 3
                elif e.key == pygame.K_4: mode = 4
                elif e.key == pygame.K_g:
                    if goals: selected_goal_idx = (selected_goal_idx + 1) % len(goals)
                elif e.key == pygame.K_SPACE:
                    auto_planning = not auto_planning
                    if auto_planning:
                        print("자동 계획 모드: ON")
                    else:
                        planning = False; plan_gen = None; path = []; current_target = None
                        print("자동 계획 모드: OFF")
                elif e.key == pygame.K_c:
                    (blocked, goals, escapes, fire_cells, start, agent_pos,
                     planner, plan_gen, planning, auto_planning, path,
                     current_target, selected_goal_idx, mode,
                     fire_step_timer, replan_check_timer, periodic_replan_timer,
                     dragging, just_teleported) = reset_all()
                    prev_bald_pos = None

                elif e.key == pygame.K_m:
                    print('역시 마준이야')

                elif e.key == pygame.K_k:
                    print('역시 민성이형이야')

                elif e.key == pygame.K_n:
                    print('노가다는...내가 할게 \n노가다는 익숙하니까...')

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
                            blocked[r][c] = False
                            if planner: planner.update_map_change((r, c), False)
                        elif not blocked[r][c]:
                            fire_cells.append((r, c))
                            blocked[r][c] = True
                            if planner: planner.update_map_change((r, c), True)
                        map_changed = True
                    elif mode == 4:
                        if (r, c) not in fire_cells and (r,c) != agent_pos and (r,c) not in goals:
                             blocked[r][c] = not blocked[r][c]
                             if planner: planner.update_map_change((r, c), blocked[r][c])
                             dragging = True; map_changed = True
                    
                    if map_changed and auto_planning:
                        path = []; plan_gen = None
                        if planner:
                            planner.update_map_change(rc, blocked[r][c])
                        current_target, planner, plan_gen = auto_replan(
                            blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                        )
                        if planner is not None: planning = True

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1: dragging = False
            elif e.type == pygame.MOUSEMOTION and dragging and mode == 4:
                rc = cell_at_pos(*e.pos, H, CELL, MARGIN, current_rows, current_cols)
                if rc:
                    r, c = rc
                    if not blocked[r][c] and (r,c) not in fire_cells and (r,c) != agent_pos and (r,c) not in goals:
                        blocked[r][c] = True
                        if planner: planner.update_map_change((r, c), True)
                        if auto_planning:
                            path = []; plan_gen = None
                            current_target, planner, plan_gen = auto_replan(
                                blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                            )
                            if planner is not None: planning = True
        
        # ===== YOLO-based incremental agent movement and teleportation =====
        if auto_planning:
            ret, frame = cap.read()
            if ret:
                results = yolo_model.predict(frame, verbose=False)
                current_bald_pos = None
                
                # Draw bounding boxes and labels on the frame for display
                for result in results:
                    for box in result.boxes:
                        if yolo_model.names[int(box.cls[0])] == 'bald':
                            x1, y1, x2, y2 = [int(x) for x in box.xyxy[0]]
                            center_x = (x1 + x2) // 2
                            center_y = (y1 + y2) // 2
                            
                            # Draw bounding box and label
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, 'bald', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                            # Map YOLO coords to grid coords
                            frame_h, frame_w, _ = frame.shape
                            mapped_r = int((center_y / frame_h) * current_rows)
                            mapped_c = int((center_x / frame_w) * current_cols)
                            
                            current_bald_pos = (mapped_r, mapped_c)
                            break
                    if current_bald_pos: break

                # Only move one step based on the direction of the object's movement
                direction = "NONE"
                if current_bald_pos and prev_bald_pos:
                    dr = current_bald_pos[0] - prev_bald_pos[0]
                    dc = current_bald_pos[1] - prev_bald_pos[1]
                    
                    next_agent_pos = agent_pos
                    
                    if abs(dr) > abs(dc):  # Dominant vertical movement
                        if dr > 0:
                            next_agent_pos = (agent_pos[0] + 1, agent_pos[1])
                            direction = "DOWN"
                        elif dr < 0:
                            next_agent_pos = (agent_pos[0] - 1, agent_pos[1])
                            direction = "UP"
                    else:  # Dominant horizontal movement or no movement
                        if dc > 0:
                            next_agent_pos = (agent_pos[0], agent_pos[1] + 1)
                            direction = "RIGHT"
                        elif dc < 0:
                            next_agent_pos = (agent_pos[0], agent_pos[1] - 1)
                            direction = "LEFT"
                    
                    # Check if the calculated move is valid
                    r, c = next_agent_pos
                    if inb(r, c, current_rows, current_cols) and not blocked[r][c]:
                        agent_pos = next_agent_pos
                        
                        # ===== 탈출 성공 및 텔레포트 기능 추가 =====
                        if agent_pos in escapes:
                            print("탈출 성공!")
                            auto_planning = False
                            planning = False
                            path = []
                        elif agent_pos in goals and not just_teleported:
                            try:
                                reached_goal_idx = goals.index(agent_pos)
                                num_goal_colors = len(GOAL_COLORS)
                                partner_idx = reached_goal_idx + num_goal_colors if reached_goal_idx < num_goal_colors else reached_goal_idx - num_goal_colors
                                if 0 <= partner_idx < len(goals):
                                    partner_pos = goals[partner_idx]
                                    if not blocked[partner_pos[0]][partner_pos[1]]:
                                        agent_pos = partner_pos
                                        just_teleported = True
                                        print("텔레포트: 목표에 도달, 파트너 위치로 이동.")
                            except ValueError:
                                pass
                        
                        if agent_pos not in goals:
                            just_teleported = False

                        if planner: planner.update_start(agent_pos)
                        current_target, planner, plan_gen = auto_replan(
                            blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                        )
                        if planner is not None: planning = True
                
                ws_handler.set_direction(direction)

                if current_bald_pos:
                    prev_bald_pos = current_bald_pos
                
                # Display the camera feed in a separate window
                cv2.imshow('YOLO Feed', frame)
                cv2.waitKey(1)

            # Check if the OpenCV window was closed by the user
            if cv2.getWindowProperty('YOLO Feed', cv2.WND_PROP_VISIBLE) < 1:
                running = False


        # ===== Fire spreading (same as before) =====
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

        # ===== Auto-replan / Periodic re-evaluation (same as before) =====
        if auto_planning and not planning:
            replan_check_timer += dt
            if replan_check_timer >= REPLAN_CHECK_INTERVAL:
                replan_check_timer = 0.0
                current_target, planner, plan_gen = auto_replan(
                    blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                )
                if planner is not None:
                    planning = True; path = []
                    print("주기적 탐색 → 경로 발견!")
        if auto_planning and not planning and path and planner.g[agent_pos[0]][agent_pos[1]] != planner.g[path[-1][0]][path[-1][1]] + len(path) - 1:
            periodic_replan_timer += dt
            if periodic_replan_timer >= REPLAN_PERIODIC_CHECK:
                periodic_replan_timer = 0.0
                new_target, new_planner, new_plan_gen = auto_replan(
                    blocked, agent_pos, goals, escapes, fire_cells, planner, current_rows, current_cols
                )
                if new_planner is not None and new_target != current_target:
                    current_target = new_target; planner = new_planner; plan_gen = new_plan_gen; path = []
                    target_type = "탈출구" if new_target in escapes else "계단"
                    print(f"더 효율적인 경로 발견 → 목표({target_type}) 변경)")

        # ===== Plan execution (same as before) =====
        if planning and plan_gen is not None:
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
                    else: planning = False



# ==================================================New!===============================================================================

        # 1층부터 갑니다
        if (11, 12) in path:
            send_command(picos, "0,0_ON")
        else:
            send_command(picos, "0,0_OFF")

        if (17, 12) in path:
            send_command(picos, "0,1_ON")
        else:
            send_command(picos, "0,1_OFF")

        if (19, 16) in path:
            send_command(picos, "0,2_ON")
        else:
            send_command(picos, "0,2_OFF")

        if (19, 21) in path:
            send_command(picos, "0,3_ON")
        else:
            send_command(picos, "0,3_OFF")

        if (20, 12) in path:
            send_command(picos, "0,4_ON")
        else:
            send_command(picos, "0,4_OFF")

        if (20, 24) in path:
            send_command(picos, "1,0_ON")
        else:
            send_command(picos, "1,0_OFF")

        if (26, 12) in path:
            send_command(picos, "1,1_ON")
        else:
            send_command(picos, "1,1_OFF")

        if (26, 18) in path:
            send_command(picos, "1,2_ON")
        else:
            send_command(picos, "1,2_OFF")

        if (26, 24) in path:
            send_command(picos, "1,3_ON")
        else:
            send_command(picos, "1,3_OFF")

        if (10, 47) in path:
            send_command(picos, "2,0_ON")
        else:
            send_command(picos, "2,0_OFF")

        if (17, 47) in path:
            send_command(picos, "2,1_ON")
        else:
            send_command(picos, "2,1_OFF")

        if (17, 59) in path:
            send_command(picos, "2,2_ON")
        else:
            send_command(picos, "2,2_OFF")

        if (19, 45) in path:
            send_command(picos, "2,3_ON")
        else:
            send_command(picos, "2,3_OFF")

        if (19, 47) in path:
            send_command(picos, "2,4_ON")
        else:
            send_command(picos, "2,4_OFF")

        if (19, 51) in path:
            send_command(picos, "3,0_ON")
        else:
            send_command(picos, "3,0_OFF")

        if (19, 56) in path:
            send_command(picos, "3,1_ON")
        else:
            send_command(picos, "3,1_OFF")

        if (19, 59) in path:
            send_command(picos, "3,2_ON")
        else:
            send_command(picos, "3,2_OFF")

        if (26, 47) in path:
            send_command(picos, "3,3_ON")
        else:
            send_command(picos, "3,3_OFF")

        if (26, 53) in path:
            send_command(picos, "3,4_ON")
        else:
            send_command(picos, "3,4_OFF")

        if (26, 59) in path:
            send_command(picos, "3,5_ON")
        else:
            send_command(picos, "3,5_OFF")

# ============================================================표독게이지 올라온다================================================
        
        # ===== Rendering =====
        draw_all(
            screen, blocked, path, goals, escapes, start, agent_pos, current_target, selected_goal_idx, fire_cells,
            mode, auto_planning, current_rows, current_cols, CELL, MARGIN,
            BG, GRID, WALL, GOAL_COLORS, ESCAPE_COLOR, START_COLOR, PATH_COLOR, AGENT_COLOR, FIRE_COLOR, TEXT_COLOR,
            W, H, font
        )

    ws_handler.stop()
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()
