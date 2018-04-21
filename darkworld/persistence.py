import pickle
import tempfile
from pathlib import Path


savedir = Path.cwd() / 'savedata'


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
