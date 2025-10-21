from ipycanvas import Canvas, hold_canvas
import ipywidgets as W
from google.colab import output
import random
from IPython.display import display


# -----------------------------
# Config
# -----------------------------
N = 8
CELL = 64
WIDTH = HEIGHT = N * CELL

# Numero massimo di mosse laterali (h uguale). Metti 0 per hill climbing puro.
SIDEWAYS_MAX = 3

# -----------------------------
# Stato
# -----------------------------
state  = [0, 5, 1, 3, 2, 4, 7, 6]  # iniziale (clic per cambiarlo)
state0 = state.copy()

moves = 0
last_move = None      # (col, from, to)
improved  = None      # True/False
stuck     = False     # minimo locale
sideways_left = SIDEWAYS_MAX

# -----------------------------
# Euristica: coppie in conflitto
# -----------------------------
def conflicts(st):
    h = 0
    for c1 in range(N):
        r1 = st[c1]
        for c2 in range(c1+1, N):
            r2 = st[c2]
            if r1 == r2:
                h += 1
            elif abs(r1 - r2) == abs(c1 - c2):
                h += 1
    return h

# -----------------------------
# Tutti i vicini (sposta una sola regina)
# -----------------------------
def all_neighbors(st):
    neigh = []
    for c in range(N):
        r0 = st[c]
        for r in range(N):
            if r == r0:
                continue
            ns = st.copy()
            ns[c] = r
            neigh.append((ns, (c, r0, r), conflicts(ns)))
    return neigh

# -----------------------------
# Un passo di Hill Climbing con mosse laterali
#   Ritorna True se ha mosso; False se bloccato.
# -----------------------------
def hill_step():
    global state, moves, last_move, improved, sideways_left
    cur_h = conflicts(state)
    neigh = all_neighbors(state)
    best_h = min(h for _,_,h in neigh)

    if best_h < cur_h:
        best = [(ns, mv, h) for (ns, mv, h) in neigh if h == best_h]
        ns, mv, _ = random.choice(best)
        state = ns
        last_move = mv
        improved = True
        moves += 1
        sideways_left = SIDEWAYS_MAX
        return True
    else:
        same = [(ns, mv, h) for (ns, mv, h) in neigh if h == cur_h]
        if SIDEWAYS_MAX > 0 and sideways_left > 0 and same:
            ns, mv, _ = random.choice(same)
            state = ns
            last_move = mv
            improved = True
            moves += 1
            sideways_left -= 1
            return True
        improved = False
        last_move = None
        return False

# -----------------------------
# Rendering
# -----------------------------
canvas = Canvas(width=WIDTH, height=HEIGHT)

def draw_board():
    with hold_canvas(canvas):
        canvas.clear()
        # scacchiera
        for x in range(N):
            for y in range(N):
                light = ((x + y) % 2 == 0)
                canvas.fill_style = "#f0f2f5" if light else "#9aa6b2"
                canvas.fill_rect(x*CELL, (N-1-y)*CELL, CELL, CELL)

        # ultime mosse
        if last_move is not None:
            c, r_from, r_to = last_move
            canvas.fill_style = "rgba(255, 193, 7, 0.35)"   # partenza
            canvas.fill_rect(c*CELL, (N-1-r_from)*CELL, CELL, CELL)
            canvas.fill_style = "rgba(25, 135, 84, 0.35)"   # arrivo
            canvas.fill_rect(c*CELL, (N-1-r_to)*CELL, CELL, CELL)

        # regine
        for c, r in enumerate(state):
            cx = c*CELL + CELL/2
            cy = (N-1-r)*CELL + CELL/2
            canvas.fill_style = "#1f2937"
            canvas.fill_circle(cx, cy, CELL*0.26)
            canvas.fill_style = "#111827"
            canvas.fill_polygon([
                (cx - CELL*0.18, cy + CELL*0.05),
                (cx + CELL*0.18, cy + CELL*0.05),
                (cx,             cy + CELL*0.22),
            ])

        # info
        h = conflicts(state)
        msg = f"h = {h}   mosse = {moves}   sideways_left = {sideways_left}"
        if h == 0:
            msg += "   ✅ soluzione!"
        elif stuck:
            msg += "   ⛔ minimo locale"
        elif improved is False:
            msg += "   —"
        canvas.fill_style = "#111827"
        canvas.fill_text(msg, 8, 16)

def reset():
    global state, state0, moves, last_move, improved, stuck, sideways_left
    state = state0.copy()
    moves = 0
    last_move = None
    improved = None
    stuck = False
    sideways_left = SIDEWAYS_MAX
    draw_board()

# -----------------------------
# Click: imposta la regina nella colonna cliccata
# -----------------------------
def on_click(x, y):
    global state, state0, stuck, improved, last_move, sideways_left
    c = int(x // CELL)
    r = N - 1 - int(y // CELL)
    if 0 <= c < N and 0 <= r < N:
        state[c] = r
        state0 = state.copy()
        stuck = False
        improved = None
        last_move = None
        sideways_left = SIDEWAYS_MAX
        draw_board()
canvas.on_mouse_down(on_click)

# -----------------------------
# Pulsanti e slider
# -----------------------------
btn_start = W.Button(description="Start", button_style="success")
btn_stop  = W.Button(description="Stop",  button_style="warning")
btn_step  = W.Button(description="Step",  button_style="primary")
btn_reset = W.Button(description="Reset", button_style="info")
speed     = W.IntSlider(description="ms/step", min=20, max=800, step=20, value=200)

# -----------------------------
# Callback Python per il timer JS
#   Ritorna '1' per fermare il timer, '0' per continuare.
# -----------------------------
def py_tick():
    global stuck
    if conflicts(state) == 0:
        draw_board()
        return '1'
    moved = hill_step()
    if not moved:
        stuck = True
        draw_board()
        return '1'
    draw_board()
    return '0'

output.register_callback('hc_tick', lambda: py_tick())

# -----------------------------
# Start/Stop/Step/Reset handlers
# -----------------------------
def on_start(_):
    # ferma un eventuale timer precedente
    output.eval_js("""
      if (window._hcTimer) { clearInterval(window._hcTimer); window._hcTimer = null; }
    """)
    # avvia nuovo timer con l'intervallo corrente
    ms = int(speed.value)
    output.eval_js(f"""
      (function() {{
        async function _hcDoTick() {{
          const r = await google.colab.kernel.invokeFunction('hc_tick', [], {{}});
          const txt = String(r.data['text/plain'] || '');
          if (txt.includes('1')) {{
            if (window._hcTimer) {{ clearInterval(window._hcTimer); window._hcTimer = null; }}
          }}
        }}
        window._hcTimer = setInterval(_hcDoTick, {ms});
        // fai anche un primo tick immediato per "vedere partire"
        _hcDoTick();
      }})();
    """)

def on_stop(_):
    output.eval_js("""
      if (window._hcTimer) { clearInterval(window._hcTimer); window._hcTimer = null; }
    """)

def on_step(_):
    # un singolo passo senza timer
    _ = py_tick()

def on_reset(_):
    on_stop(None)
    reset()

btn_start.on_click(on_start)
btn_stop.on_click(on_stop)
btn_step.on_click(on_step)
btn_reset.on_click(on_reset)

# -----------------------------
# Layout
# -----------------------------
ui = W.HBox([btn_start, btn_stop, btn_step, btn_reset, speed])
display(ui, canvas)
draw_board()
