import click

from darkworld.persistence import pickle_atomic, load_pickle


@click.group()
def cli():
    pass


@cli.command()
@click.argument('username')
@click.argument('capability')
def grant(username, capability):
    pickfile = f'{username}-caps.pck'
    caps = load_pickle(pickfile)
    if not caps:
        click.echo(f'No such user {username}', err=True)
        return

    caps.add(capability)
    pickle_atomic(pickfile, caps)


@cli.command()
@click.argument('username')
@click.argument('capability')
def revoke(username, capability):
    pickfile = f'{username}-caps.pck'
    caps = load_pickle(pickfile)
    if not caps:
        click.echo(f'No such user {username}', err=True)
        return

    caps.discard(capability)
    pickle_atomic(pickfile, caps)


@cli.command()
@click.argument('username')
def show(username):
    pickfile = f'{username}-caps.pck'
    caps = load_pickle(pickfile)
    if not caps:
        click.echo(f'No such user {username}', err=True)
        return

    for c in sorted(caps):
        print(c)


if __name__ == '__main__':
    cli()
