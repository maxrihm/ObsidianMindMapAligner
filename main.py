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
    """
    Compute total width of a subtree. We use 800 as the base width now.
    """
    if n in cache:
        return cache[n]
    c = ch[n]
    if not c:
        # If no children, width = 800
        nd[n]["width"] = 800
        nd[n]["height"] = 800
        cache[n] = 800
        return 800

    gap = 200
    total = 0
    for x in c:
        total += subtree_width(x, ch, nd, cache)
    total += gap * (len(c) - 1)

    # A node’s own width is forced to 800
    nd[n]["width"] = 800
    nd[n]["height"] = 800

    # If the sum of children widths is smaller than 800, we use 800 anyway
    if total < 800:
        total = 800

    cache[n] = total
    return total

def layout_subtree(n, x, y, ch, nd, cache):
    """
    Recursively set x,y for each node, forcing 800x800 for each node.
    Preserves the left-to-right order based on the child's existing x value.
    """
    nd[n]["x"] = x
    nd[n]["y"] = y
    nd[n]["width"] = 800
    nd[n]["height"] = 800

    c = ch[n]
    if not c:
        return

    # Sort children by their current X so we preserve any manual ordering
    c_sorted = sorted(c, key=lambda cid: nd[cid]["x"])

    gap_x = 200
    gap_y = 200
    nh = 800  # forced height
    ny = y + nh + gap_y

    # total width among children
    tw = sum(subtree_width(child_id, ch, nd, cache) for child_id in c_sorted) \
         + (len(c_sorted) - 1) * gap_x

    left = x - tw / 2
    for child_id in c_sorted:
        w = subtree_width(child_id, ch, nd, cache)
        nx = left + w / 2
        layout_subtree(child_id, nx, ny, ch, nd, cache)
        left += w + gap_x

def filter_invisible(d):
    """
    Filter only nodes containing <mind-map-node-invisible></mind-map-node-invisible>.
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
    """
    Create a new node that ends with <mind-map-node-invisible></mind-map-node-invisible>,
    and set default size to 800x800.
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
        "width": 800,  # force new node to be 800x800
        "height": 800
    })

    save_data(p, d)
    e_q.delete("1.0", "end")
    e_a.delete("1.0", "end")

def align():
    """
    Layout only nodes containing <mind-map-node-invisible></mind-map-node-invisible>.
    Force them all to be 800x800 in the process,
    but preserve left-to-right order based on current x-values.
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

    # We layout only the first root (if multiple, you can loop).
    layout_subtree(r[0], 0, 0, ch, nds, cache)

    # Copy updated positions + forced size back to the main data
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
