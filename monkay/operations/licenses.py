import textwrap
from importlib.metadata import (
    Distribution,
    distribution,
    packages_distributions,
)

import click


@click.command
def licenses():
    text = ""
    for distname, package_names in packages_distributions().items():
        if distname == "__pycache__" or len(package_names) == 0:
            continue
        dist_data: Distribution = distribution(package_names[0])
        ltext = "-"
        if "License-Expression" in dist_data.metadata:
            ltext = " " + "\n ".join(
                dist_data.metadata.get_all("License-Expression", [])
            )
        elif "License" in dist_data.metadata:
            ltext = " " + "\n ".join(dist_data.metadata.get_all("License", []))
        else:
            ltext = " " + "\n ".join(
                header.rsplit("::", 1)[-1].strip()
                for header in dist_data.metadata.get_all("Classifier", [])
                if "License" in header
            )
        if dist_data.metadata.get("Author-email", ""):
            ltext = f"{ltext}\nAuthors:\n " + "\n".join(
                dist_data.metadata.get("Author-email", "").split(",")
            )

        if dist_data.metadata["License-File"]:
            read_text = dist_data.read_text(dist_data.metadata["License-File"])
            if read_text:
                ltext += "\nText:\n" + "\n".join(
                    textwrap.wrap(
                        read_text,
                        replace_whitespace=False,
                    )
                )
        text = f'{text}\n\nModule "{distname}":\n{ltext}'
    click.echo(text.strip())
