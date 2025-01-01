import tkinter as tk
import json
import uuid
import pyautogui
import pyperclip
import time
from pynput import keyboard

root = tk.Tk()
root.title("MindMap App")

##############################################################################
# Data helpers
##############################################################################

def load_data(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"nodes":[],"edges":[]}

def save_data(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

def build_children_map(d):
    node_ids = {n["id"] for n in d["nodes"]}
    m = {}
    for n in d["nodes"]:
        m[n["id"]] = []
    for e in d["edges"]:
        fr = e["fromNode"]
        to = e["toNode"]
        if fr in node_ids and to in node_ids:
            m[fr].append(to)
    return m

def build_parents_map(d):
    node_ids = {n["id"] for n in d["nodes"]}
    m = {}
    for n in d["nodes"]:
        m[n["id"]] = []
    for e in d["edges"]:
        fr = e["fromNode"]
        to = e["toNode"]
        if fr in node_ids and to in node_ids:
            m[to].append(fr)
    return m

def find_roots(d):
    pm = build_parents_map(d)
    r = []
    for node_id, parents in pm.items():
        if not parents:
            r.append(node_id)
    if not r and d["nodes"]:
        r = [d["nodes"][0]["id"]]
    return r

def node_dict(d):
    nd = {}
    for n in d["nodes"]:
        nd[n["id"]] = n
    return nd

##############################################################################
# Layout logic
##############################################################################

def subtree_width(n, ch, nd, cache):
    """
    Compute total width of a subtree.
    - If it's a normal invisible tag: force 800×800.
    - If it's the NO-RESIZE tag: do NOT force 800×800. Use whatever width/height is set.
    """
    if n in cache:
        return cache[n]

    c = ch[n]
    txt = nd[n]["text"]
    is_no_resize = "<mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>" in txt

    base_width = 800
    base_height = 800

    # If no children, just handle width/height based on the tag
    if not c:
        if is_no_resize:
            w = nd[n].get("width", 300)  # default smaller if missing
            h = nd[n].get("height", 300)
            nd[n]["width"] = w
            nd[n]["height"] = h
            cache[n] = w
            return w
        else:
            nd[n]["width"] = base_width
            nd[n]["height"] = base_height
            cache[n] = base_width
            return base_width

    # If there are children
    gap = 200
    total = 0
    for x in c:
        total += subtree_width(x, ch, nd, cache)
    total += gap * (len(c) - 1)

    if is_no_resize:
        w = nd[n].get("width", 300)
        h = nd[n].get("height", 300)
        nd[n]["width"] = w
        nd[n]["height"] = h
        # If the sum of children widths is smaller than this node's width, make total = that width
        if total < w:
            total = w
    else:
        # forced to 800 if it's the regular invisible tag
        nd[n]["width"] = base_width
        nd[n]["height"] = base_height
        if total < base_width:
            total = base_width

    cache[n] = total
    return total

def layout_subtree(n, x, y, ch, nd, cache):
    """
    Recursively position each node.
    - Normal invisible tag => forced 800×800
    - NO-RESIZE tag => keep existing width/height
    """
    txt = nd[n]["text"]
    is_no_resize = "<mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>" in txt

    if is_no_resize:
        w = nd[n].get("width", 300)
        h = nd[n].get("height", 300)
        nd[n]["width"] = w
        nd[n]["height"] = h
    else:
        w = 800
        h = 800
        nd[n]["width"] = w
        nd[n]["height"] = h

    nd[n]["x"] = x
    nd[n]["y"] = y

    c = ch[n]
    if not c:
        return

    c_sorted = sorted(c, key=lambda cid: nd[cid]["x"])

    gap_x = 200
    gap_y = 200
    ny = y + h + gap_y

    # total width among children
    tw = sum(subtree_width(child_id, ch, nd, cache) for child_id in c_sorted) \
         + (len(c_sorted) - 1) * gap_x

    left = x - tw / 2
    for child_id in c_sorted:
        w_c = subtree_width(child_id, ch, nd, cache)
        nx = left + w_c / 2
        layout_subtree(child_id, nx, ny, ch, nd, cache)
        left += w_c + gap_x

##############################################################################
# Filtering logic
##############################################################################

def filter_invisible(d):
    """
    Filter only nodes containing EITHER:
      <mind-map-node-invisible></mind-map-node-invisible>
    OR
      <mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>
    """
    invisible_nodes = set()
    for n in d["nodes"]:
        txt = n.get("text","")
        if "<mind-map-node-invisible></mind-map-node-invisible>" in txt \
           or "<mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>" in txt:
            invisible_nodes.add(n["id"])
    nd = []
    ed = []
    for n in d["nodes"]:
        if n["id"] in invisible_nodes:
            nd.append(n)
    for e in d["edges"]:
        if e["fromNode"] in invisible_nodes and e["toNode"] in invisible_nodes:
            ed.append(e)
    return {"nodes": nd, "edges": ed}

##############################################################################
# Add node logic
##############################################################################

def add_node():
    """
    Create a new node that ends with <mind-map-node-invisible></mind-map-node-invisible>,
    forced default size 800x800.
    """
    p = e_path.get().strip()
    if not p:
        return
    d = load_data(p)

    q = e_q.get("1.0", "end").strip().replace("\n", "")
    a = e_a.get("1.0", "end")
    i = str(uuid.uuid4())[:16].replace("-", "")

    final_text = f'''<div style="color: white; font-weight: bold; background-color: black; padding: 10px;">
    {q}
</div>

---
{a}<mind-map-node-invisible></mind-map-node-invisible>'''

    d["nodes"].append({
        "id": i,
        "type": "text",
        "text": final_text,
        "x": 0,
        "y": 0,
        "width": 800,
        "height": 800
    })

    save_data(p, d)
    e_q.delete("1.0", "end")
    e_a.delete("1.0", "end")

def add_node_no_resize():
    """
    Create a new node that ends with <mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>,
    do NOT force 800x800 (use smaller default, or let user override later).
    """
    p = e_path.get().strip()
    if not p:
        return
    d = load_data(p)

    q = e_q.get("1.0", "end").strip().replace("\n", "")
    a = e_a.get("1.0", "end")
    i = str(uuid.uuid4())[:16].replace("-", "")

    final_text = f'''<div style="color: white; font-weight: bold; background-color: black; padding: 10px;">
    {q}
</div>

---
{a}<mind-map-node-invisible-no-resize></mind-map-node-invisible-no-resize>'''

    d["nodes"].append({
        "id": i,
        "type": "text",
        "text": final_text,
        "x": 0,
        "y": 0,
        # Let’s start with something smaller like 300x300, user can resize later.
        "width": 300,
        "height": 300
    })

    save_data(p, d)
    e_q.delete("1.0", "end")
    e_a.delete("1.0", "end")

def align():
    """
    Layout only nodes containing the invisible or no-resize tags.
    - Normal <mind-map-node-invisible> => forced 800x800
    - <mind-map-node-invisible-no-resize> => keep custom size
    """
    p = e_path.get().strip()
    if not p:
        return
    d = load_data(p)

    dd = filter_invisible(d)
    ch = build_children_map(dd)
    r = find_roots(dd)
    if not r:
        save_data(p, d)
        return

    nds = node_dict(dd)
    cache = {}

    # Layout from the first root (if multiple, you can loop)
    layout_subtree(r[0], 0, 0, ch, nds, cache)

    # Copy updated positions + updated sizes back to the main data
    for nm in dd["nodes"]:
        for o in d["nodes"]:
            if nm["id"] == o["id"]:
                o["x"] = nm["x"]
                o["y"] = nm["y"]
                o["width"] = nm["width"]
                o["height"] = nm["height"]
                break

    save_data(p, d)

##############################################################################
# UI
##############################################################################

tk.Label(root, text="Question").grid(row=0, column=0, sticky="w")
tk.Label(root, text="Answer").grid(row=1, column=0, sticky="w")
tk.Label(root, text="Canvas Path").grid(row=2, column=0, sticky="w")

e_q = tk.Text(root, width=50, height=5)
e_q.grid(row=0, column=1)
e_a = tk.Text(root, width=50, height=5)
e_a.grid(row=1, column=1)
e_path = tk.Entry(root, width=50)
e_path.grid(row=2, column=1)

tk.Button(root, text="Add", command=add_node).grid(row=3, column=0)
tk.Button(root, text="Align", command=align).grid(row=3, column=1)
# New button for adding the no-resize tag
tk.Button(root, text="Add No Resize", command=add_node_no_resize).grid(row=3, column=2)

##############################################################################
# Global hotkey logic with pynput
##############################################################################

pressed_keys = set()

def on_press(key):
    try:
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            pressed_keys.add('alt')
        elif key == keyboard.Key.f1:
            pressed_keys.add('f1')
        elif key == keyboard.Key.f2:
            pressed_keys.add('f2')
    except:
        pass
    check_hotkeys()

def on_release(key):
    try:
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            pressed_keys.discard('alt')
        elif key == keyboard.Key.f1:
            pressed_keys.discard('f1')
        elif key == keyboard.Key.f2:
            pressed_keys.discard('f2')
    except:
        pass

def check_hotkeys():
    if 'alt' in pressed_keys and 'f1' in pressed_keys:
        alt_f1_action()
    if 'alt' in pressed_keys and 'f2' in pressed_keys:
        alt_f2_action()

def alt_f1_action():
    pressed_keys.discard('f1')
    pressed_keys.discard('alt')

    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'c')
    pyautogui.hotkey('ctrl', 'c')
    pyautogui.hotkey('ctrl', 'c')

    time.sleep(0.3)
    text_copied = pyperclip.paste()
    root.after(0, lambda: e_q.insert("1.0", text_copied))

def alt_f2_action():
    pressed_keys.discard('f2')
    pressed_keys.discard('alt')

    pyautogui.click()
    time.sleep(0.3)
    text_copied = pyperclip.paste()
    root.after(0, lambda: e_a.insert("1.0", text_copied))

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

root.mainloop()
