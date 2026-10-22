with open("tests/test_p2p_scatter.py", "r") as f:
    data = f.read()

data = data.replace(
    """        for _ in range(5):
            scatter = governor.update()""",
    """        for _ in range(20):
            scatter = governor.update()""",
)

with open("tests/test_p2p_scatter.py", "w") as f:
    f.write(data)
