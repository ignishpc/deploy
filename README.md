![IgnisHPC logo](https://gitlab.com/ignis-hpc/wiki/-/raw/main/logo/svg/ignis-hpc.svg)

# IgnisHPC Deploy
Module for the creation and management of an IgnisHPC cluster.

Tutorial and documentation: [IgnisHPC wiki](https://gitlab.com/ignis-hpc/wiki/-/wikis)

## Install

You can install IgnisHPC from its source distribution using pip:
`pip install ignishpc`

### External requirements
* Docker: IgnisHPC is run inside containers, so docker must be installed.
* Git (optional): The git binary is required for building IgnisHPC images from repositories.

## Usage

List services status:
`ignis-deploy status`

List available services:
`ignis-deploy -h`

List available service actions:
`ignis-deploy <service> -h`