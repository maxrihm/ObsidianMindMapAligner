import tkinter as tk
import json
import uuid
import pyautogui
import pyperclip
import time
from pynput import keyboard

root = tk.Tk()
root.title("MindMap App")

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

def subtree_width(n, ch, nd, cache):
    if n in cache:
        return cache[n]
    c = ch[n]
    if not c:
        w = nd[n].get("width", 600)
        cache[n] = w
        return w
    gap = 200
    total = 0
    for x in c:
        total += subtree_width(x, ch, nd, cache)
    total += gap * (len(c) - 1)
    w = nd[n].get("width", 600)
    if total < w:
        total = w
    cache[n] = total
    return total

def layout_subtree(n, x, y, ch, nd, cache):
    nd[n]["x"] = x
    nd[n]["y"] = y
    c = ch[n]
    if not c:
        return
    gap_x = 200
    gap_y = 200
    nh = nd[n].get("height", 600)
    ny = y + nh + gap_y
    tw = sum(subtree_width(i, ch, nd, cache) for i in c) + (len(c)-1)*gap_x
    left = x - tw/2
    for i in c:
        w = subtree_width(i, ch, nd, cache)
        nx = left + w/2
        layout_subtree(i, nx, ny, ch, nd, cache)
        left += w + gap_x

def filter_invisible(d):
    """
    Instead of checking for 'MMN', we check for 
    <mind-map-node-invisible></mind-map-node-invisible>
    """
    invisible_nodes = set()
    for n in d["nodes"]:
        if "<mind-map-node-invisible></mind-map-node-invisible>" in n.get("text",""):
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

def add_node():
    p = e_path.get().strip()
    if not p:
        return
    d = load_data(p)

    # Remove line breaks in the question
    q = e_q.get("1.0", "end").strip().replace("\n", "")
    a = e_a.get("1.0", "end")
    i = str(uuid.uuid4())[:16].replace("-", "")

    # Instead of adding 'MMN', we now add <mind-map-node-invisible></mind-map-node-invisible>
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
        "width": 600,
        "height": 600
    })

    save_data(p, d)
    e_q.delete("1.0", "end")
    e_a.delete("1.0", "end")

def align():
    """
    Re-layout only the nodes containing <mind-map-node-invisible></mind-map-node-invisible>.
    """
    p = e_path.get().strip()
    if not p:
        return
    d = load_data(p)

    dd = filter_invisible(d)
    ch = build_children_map(dd)
    r = find_roots(dd)
    if not r:
        # If no root found, just save and return
        save_data(p, d)
        return

    nds = node_dict(dd)
    cache = {}
    layout_subtree(r[0], 0, 0, ch, nds, cache)

    # Copy updated positions back into the main data
    for nm in dd["nodes"]:
        for o in d["nodes"]:
            if nm["id"] == o["id"]:
                o["x"] = nm["x"]
                o["y"] = nm["y"]
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
    pyautogui.keyDown('ctrl')
    pyautogui.press('c')
    pyautogui.keyUp('ctrl')

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

from pynput import keyboard
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

root.mainloop()
