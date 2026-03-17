d = {"a": [1]}
vals = d.values()
d["a"].append(2)
d["b"] = 3
for v in vals:
    print(v)
