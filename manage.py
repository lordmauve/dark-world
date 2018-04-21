import click

from darkworld.persistence import pickle_atomic, load_pickle


@click.group()
def cli():
    pass


@cli.command()
@click.argument('username')
@click.argument('capability')
def grant(username, capability):
    pickfile = f'{username}-user.pck'
    data = load_pickle(pickfile)
    if not data:
        click.echo(f'No such user {username}', err=True)
        return

    data.setdefault('caps', set()).add(capability)
    pickle_atomic(pickfile, data)


@cli.command()
@click.argument('username')
@click.argument('capability')
def revoke(username, capability):
    pickfile = f'{username}-user.pck'
    data = load_pickle(pickfile)
    if not data:
        click.echo(f'No such user {username}', err=True)
        return

    data.setdefault('caps', set()).discard(capability)
    pickle_atomic(pickfile, data)


@cli.command()
@click.argument('username')
def show(username):
    pickfile = f'{username}-user.pck'
    data = load_pickle(pickfile)
    if not data:
        click.echo(f'No such user {username}', err=True)
        return

    for c in sorted(data.get('caps', ())):
        print(c)


if __name__ == '__main__':
    cli()
