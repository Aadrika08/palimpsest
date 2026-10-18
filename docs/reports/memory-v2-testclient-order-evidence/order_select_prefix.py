from pathlib import Path

def pytest_collection_modifyitems(config, items):
    keep, drop = [], []
    for item in items:
        if item.path.name < 'test_lab.py' or (item.path.name == 'test_lab.py' and '::ApiGuards::' in item.nodeid):
            keep.append(item)
        else:
            drop.append(item)
    config.hook.pytest_deselected(items=drop)
    items[:] = keep
