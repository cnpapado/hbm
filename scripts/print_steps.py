import os, json

def load_steps(path):
    if not os.path.exists(path):
        return None
    # try:
    with open(path) as f:
        data = json.load(f)
    steps = data.get("steps")
    if steps == "timeout":
        return None
    return len(steps)
    # except:
        # return None

print(load_steps("nohbm.out"))
print(load_steps("hbmA.out"))
