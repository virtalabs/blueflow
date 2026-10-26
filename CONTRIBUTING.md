# Contributing to Blueflow

Blueflow is a community driven asset discovery tool. As it keeps growing, we always need more people to help others.
You can contribute in many ways, either on the app itself or in the wider ecosystem.

For contributing to fingerprinting and the open source fingerprinting database see [tapirxl](https://github.com/virtalabs/tapirxl)

# Communication channels

We’re passionate about helping Blueflow users make the jump to contributing members of the community. Communication is key - working on Blueflow is being part of a conversation.
Join it, to become familiar with what we’re doing and how we talk about it.

Feel free to open an issue, email the core dev team, or otherwise contact [Virtalabs](https://virtalabs.com) for help.


# Getting started

Blueflow encourages and welcomes new contributors, and confident contributors to Open Source Software (OSS).

If you would like to help and don't know where to begin, checkout the [issues page](https://github.com/virtalabs/blueflow/issues).

# Contributing code

You can make a pull request and see your code in the next version of Blueflow.

## Git strategy
Blueflow follows a trunk based strategy. In effect this means that all feature and bug fix branches will need to be based on the current HEAD.
Once a PR is approved these changes will be merged into the main branch for the project where the feature branch is then deleted.

## Builds
If your PR is approved it will automatically be included in the `latest` build for Blueflow.

## Versioning
Currently, Blueflow is pre-1.0 and should be treated as in an unstable beta build that is not fit for production and is not guranteed to be secure or stable.

When a new version is published a [git tag](https://github.com/virtalabs/blueflow/tags) will be created. The tag will follow (semver 2.0)[https://semver.org/spec/v2.0.0.html].
Once tagged, a docker build will be published with a matching version tag.

Any changes that result in breaking external contracts will release on a major version bump.
Django migrations may change on minor releases and are only guaranteed to remain backwards compatible between major versions.

Reference the [release page](https://github.com/virtalabs/blueflow/releases) for any details related to a specific release.

## Etiquette

PRs must target the default branch and be based on its latest changes. They must require no merges or rebase.
Any PR that fails automatic testing, fails to provide appropriate test coverage, or otherwise degrades the quality of the code is subject to rejection.

Your code should be easily understandable, with a reasonably sized PR for the given issue.

All PRs _must_ have a linked issue. Some issues the core team fixes may be private, while some may be public.
Once your PR is created it may be subject to automated reviews from agentic tooling as well as approval from a core team member.

## Environment

Every development environment will require the following:

1. a valid `.env` file
2. a python virtualenv
3. all dependencies installed from the [pyproject.toml]()
4. a running PSQL server

An exmaple .env can be found in the repo [here](https://github.com/virtalabs/blueflow/blob/develop/.env.example). Managing the virtualenv can be done with any tool of your choice but the contributors recomend using the latest version of [uv](https://docs.astral.sh/uv/) along with a context system like [direnv](https://direnv.net).
It is recommended to install all dependencies for development, however dependencies are grouped if you wish fine-grained control.
Finally, ensure the `.env` file you have points to the Postgres service as in the `.env.example`.

A simple test to ensure you are setup correctly is to execute the following with no errors:
1. `./project/manage.py migrate`
2. `./project/manage.py runserver_plus`
3. curl or visit `http://127.0.0.1:8000/api/`

# Reporting bugs and requesting features

All bug reports and feature requests should be associated with a GitHub issue, except security vulnerabilities, which should be emailed to security at virtalabs [dot] com.

# Responsible Use of AI-Generated Content

It's essential to use generative AI technologies thoughtfully.

When using generative AI to contribute to the community:

Take ownership of your contributions. You are responsible for the content you share.
Review and revise AI-generated responses before posting. Ensure they reflect your own understanding and voice.
Apply your expertise to validate that the information is accurate, relevant, and helpful.
These practices support a community built on trust, collaboration, and mutual respect

# Contributors

A thank you to everyone who has contributed:

- t-a-y-l-o-r, for their work on Blueflow's core systems and managing everything django.
- xnorkl, for his networking and information security knowledge that helps lead Blueflow's development.

# License
This document is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/)
