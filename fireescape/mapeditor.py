# -*- coding: utf-8 -*-
import sys, pygame
import json
import os
from datetime import datetime

# ===== 설정 =====
CELL = 22
ROWS = 35
COLS = 70
MARGIN = 1
FPS = 60

# 색상 설정
BG = (245, 246, 248)
GRID = (220, 223, 230)
WALL = (60, 72, 88)
START_COLOR = (52, 152, 219)
FIRE_COLOR = (231, 100, 20)
TEXT_COLOR = (33, 33, 33)

# 목표 지점 및 탈출구 색상
GOAL_COLORS = [
    (0, 141, 98),   # 초록색
    (241, 196, 15), # 노란색
    (250, 153, 204),# 분홍색
    (119, 109, 97), # 회색
    (153, 134, 179),# 보라색
]
# 탈출구 색상은 목표와 별도로 지정
ESCAPE_COLOR = (25, 25, 25)

# D* Lite 데모에서 가져온 프리셋 벽 정보
PRESET_WALLS = [
    {'kind': 'rect', 'r0': 4, 'c0': 20, 'r1': 24, 'c1': 21},
    {'kind': 'rect', 'r0': 4, 'c0': 35, 'r1': 24, 'c1': 36},
    {'kind': 'hline', 'r': 25, 'c0': 20, 'c1': 35},
    {'kind': 'vline', 'c': 15, 'r0': 5, 'r1': 30},
    {'kind': 'vline', 'c': 40, 'r0': 5, 'r1': 30},
    {'kind': 'rect', 'r0': 27, 'c0': 15, 'r1': 28, 'c1': 40},
    {'kind': 'rect', 'r0': 4, 'c0': 45, 'r1': 24, 'c1': 46},
    {'kind': 'rect', 'r0': 4, 'c0': 60, 'r1': 24, 'c1': 61},
    {'kind': 'hline', 'r': 25, 'c0': 45, 'c1': 60},
    {'kind': 'hline', 'r': 26, 'c0': 50, 'c1': 55},
]


# ----- 함수 (function.py에서 가져옴) -----
def build_blocked_with_presets(ROWS, COLS, presets):
    """
    미리 설정된 값으로 벽을 생성합니다.
    """
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
    return blocked


def draw_all(screen, blocked, start, goals, fire_cells, escapes):
    """
    모든 요소 (그리드, 벽, 목표, 시작점 등)를 화면에 그립니다.
    """
    screen.fill(BG)

    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(
                c * (CELL + MARGIN) + MARGIN,
                r * (CELL + MARGIN) + MARGIN,
                CELL, CELL
            )
            color = GRID
            if blocked[r][c]:
                color = WALL
            pygame.draw.rect(screen, color, rect, border_radius=5)

    if start:
        r, c = start
        rect = pygame.Rect(c * (CELL + MARGIN) + MARGIN, r * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, START_COLOR, rect, border_radius=5)

    for i, g in enumerate(goals):
        r, c = g
        rect = pygame.Rect(c * (CELL + MARGIN) + MARGIN, r * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, GOAL_COLORS[i % len(GOAL_COLORS)], rect, border_radius=5)

    for f in fire_cells:
        r, c = f
        rect = pygame.Rect(c * (CELL + MARGIN) + MARGIN, r * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, FIRE_COLOR, rect, border_radius=5)

    for e in escapes:
        r, c = e
        rect = pygame.Rect(c * (CELL + MARGIN) + MARGIN, r * (CELL + MARGIN) + MARGIN, CELL, CELL)
        pygame.draw.rect(screen, ESCAPE_COLOR, rect, border_radius=5)

    pygame.display.flip()

# ----- 메인 루프 -----
def main():
    pygame.init()
    W = COLS * (CELL + MARGIN) + MARGIN
    H = ROWS * (CELL + MARGIN) + MARGIN
    screen = pygame.display.set_mode((W, H + 80))
    pygame.display.set_caption("Map Editor")
    
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    # 빈 맵으로 시작합니다.
    blocked = [[False] * COLS for _ in range(ROWS)]
    
    start = None
    goals = []
    fire_cells = set()
    escapes = []

    drawing_wall = False
    erasing_wall = False
    
    # 맵 상태 히스토리 (Undo/Redo용)
    history = []
    history_idx = -1
    def save_state():
        nonlocal history_idx, history
        if history_idx < len(history) - 1:
            history = history[:history_idx + 1]
        history.append({
            'blocked': [row[:] for row in blocked],
            'start': start,
            'goals': goals[:],
            'fire_cells': fire_cells.copy(),
            'escapes': escapes[:]
        })
        history_idx = len(history) - 1

    def undo():
        nonlocal history_idx, blocked, start, goals, fire_cells, escapes
        if history_idx > 0:
            history_idx -= 1
            state = history[history_idx]
            blocked = [row[:] for row in state['blocked']]
            start = state['start']
            goals = state['goals'][:]
            fire_cells = state['fire_cells'].copy()
            escapes = state['escapes'][:]

    def redo():
        nonlocal history_idx, blocked, start, goals, fire_cells, escapes
        if history_idx < len(history) - 1:
            history_idx += 1
            state = history[history_idx]
            blocked = [row[:] for row in state['blocked']]
            start = state['start']
            goals = state['goals'][:]
            fire_cells = state['fire_cells'].copy()
            escapes = state['escapes'][:]

    save_state()

    # 파일 입출력 변수
    input_mode = None
    input_text = ''
    
    running = True
    while running:
        clock.tick(FPS)
        
        mx, my = pygame.mouse.get_pos()
        col = mx // (CELL + MARGIN)
        row = my // (CELL + MARGIN)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and my < H:
                if event.button == 1:
                    if not blocked[row][col]:
                        drawing_wall = True
                        blocked[row][col] = True
                        save_state()
                elif event.button == 3:
                    if blocked[row][col]:
                        erasing_wall = True
                        blocked[row][col] = False
                        save_state()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    drawing_wall = False
                elif event.button == 3:
                    erasing_wall = False
            elif event.type == pygame.MOUSEMOTION and my < H:
                if drawing_wall and not blocked[row][col]:
                    blocked[row][col] = True
                elif erasing_wall and blocked[row][col]:
                    blocked[row][col] = False
            elif event.type == pygame.KEYDOWN:
                if input_mode:
                    if event.key == pygame.K_RETURN:
                        if input_mode == 'save':
                            save_map(blocked, start, goals, fire_cells, escapes, input_text)
                        elif input_mode == 'load':
                            blocked, start, goals, fire_cells, escapes = load_map(input_text)
                        input_mode = None
                        input_text = ''
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        input_text += event.unicode
                else:
                    # 키를 숫자로 변경했습니다.
                    if event.key == pygame.K_1:
                        if start == (row, col):
                            start = None
                        else:
                            start = (row, col)
                        save_state()
                    elif event.key == pygame.K_2:
                        if (row, col) in goals:
                            goals.remove((row, col))
                        else:
                            goals.append((row, col))
                        save_state()
                    elif event.key == pygame.K_3:
                        fire_cells.add((row, col))
                        save_state()
                    elif event.key == pygame.K_4:
                        if (row, col) in escapes:
                            escapes.remove((row, col))
                        else:
                            escapes.append((row, col))
                        save_state()
                    elif event.key == pygame.K_d:
                        if (row, col) in fire_cells:
                            fire_cells.remove((row, col))
                        save_state()
                    elif event.key == pygame.K_x:
                        blocked = [[False] * COLS for _ in range(ROWS)]
                        start = None
                        goals = []
                        fire_cells.clear()
                        escapes = []
                        history_idx = -1
                        save_state()
                    elif event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        undo()
                    elif event.key == pygame.K_y and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        redo()
                    elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        input_mode = 'save'
                    elif event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        input_mode = 'load'
                    elif event.key == pygame.K_p: # P 키를 눌러 프리셋 벽을 로드
                        blocked = build_blocked_with_presets(ROWS, COLS, PRESET_WALLS)
                        save_state()
                        
        draw_all(screen, blocked, start, goals, fire_cells, escapes)
        
        # 파일 입출력 오버레이
        if input_mode:
            overlay = pygame.Surface((W, H + 80), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            
            prompt = "파일 이름을 입력하세요 (저장)" if input_mode == 'save' else "파일 이름을 입력하세요 (불러오기)"
            prompt_text = font.render(prompt, True, (255, 255, 255))
            screen.blit(prompt_text, (W//2 - prompt_text.get_width()//2, H//2 - 60))
            
            input_box = pygame.Rect(W//2 - 150, H//2 - 20, 300, 30)
            pygame.draw.rect(screen, (255, 255, 255), input_box, border_radius=5)
            pygame.draw.rect(screen, (0, 0, 0), input_box, 2, border_radius=5)
            
            input_surface = font.render(input_text, True, (0, 0, 0))
            text_rect = input_surface.get_rect(center=input_box.center)
            screen.blit(input_surface, text_rect)
            
            pygame.display.flip()

# 파일 저장 및 불러오기 함수
def save_map(blocked, start, goals, fire_cells, escapes, filename):
    data = {
        'blocked': blocked,
        'start': start,
        'goals': goals,
        'fire_cells': list(fire_cells),
        'escapes': escapes
    }
    with open(f'{filename}.json', 'w') as f:
        json.dump(data, f)
    print(f'Map saved to {filename}.json')

def load_map(filename):
    try:
        with open(f'{filename}.json', 'r') as f:
            data = json.load(f)
            return (
                data.get('blocked', [[False] * COLS for _ in range(ROWS)]),
                data.get('start'),
                data.get('goals', []),
                set(data.get('fire_cells', [])),
                data.get('escapes', [])
            )
    except FileNotFoundError:
        print(f'File {filename}.json not found.')
        return ([[False] * COLS for _ in range(ROWS)], None, [], set(), [])

if __name__ == '__main__':
    main()
