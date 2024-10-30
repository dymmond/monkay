import textwrap

import click


@click.command
def licenses():
    from monkay import Monkay

    text = ""
    for module, monkay in Monkay.monkays.items():
        ltext = (
            "\n".join(textwrap.wrap(monkay.license, replace_whitespace=False))
            if monkay.license
            else "-"
        )
        text = f'{text}\n\nModule "{module}":\n{ltext}'
    click.echo(text.strip())
