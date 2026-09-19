"""Trivial internal APT repository environment."""

from pathlib import Path

from control_tower.environments.docker_environment import (
    make_environment_config_from_path,
)

root = Path(__file__).parent

trivial_apt_repository_config = make_environment_config_from_path(
    root,
    custom_display_name="Trivial APT Repository",
    short_description="A tiny internal Debian package publisher with approval and quarantine paths.",
    tech_stack=["Bash", "NGINX", "APT", "dpkg"],
    services=["NGINX package repository", "APT client"],
)
