import pickle
import tempfile
from pathlib import Path

from . import client
from .world_gen import create_light_world


savedir = Path.cwd() / 'savedata'
world_file = 'light_world.pck'


def pickle_atomic(outfile, data):
    assert outfile.endswith('.pck')
    if not savedir.exists():
        # FIXME: this bit is not atomic
        savedir.mkdir()

    tmpfile = tempfile.NamedTemporaryFile(
        dir=savedir,
        delete=False,
        suffix='.pck'
    )
    try:
        pickle.dump(data, tmpfile, -1)
    except BaseException:
        Path(tmpfile.name).unlink()
        raise
    else:
        Path(tmpfile.name).rename(savedir / outfile)


def load_pickle(name):
    try:
        f = (savedir / name).open('rb')
    except IOError:
        return None
    with f:
        return pickle.load(f)


def init_world():
    client.light_world = load_pickle(world_file)
    if client.light_world:
        print(f'World loaded from {world_file}')
    else:
        client.light_world = create_light_world()


def save_world():
    pickle_atomic(world_file, client.light_world)
    print(f'World state saved to {world_file}')
