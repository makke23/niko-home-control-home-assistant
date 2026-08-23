# Contributing

Thank you for helping improve Niko Home Control II for Home Assistant.

## Before opening an issue

- Search existing issues first.
- Confirm the problem still occurs on the latest released version.
- Never include passwords, API tokens, private IP addresses, diagnostic files,
  or unredacted Home Assistant logs.
- Describe the Niko device type, the expected result, and the observed result.

## Development

1. Create a Python virtual environment.
2. Install `requirements-dev.txt`.
3. Run `python -m pytest`.
4. Run `python -m compileall -q custom_components tests`.

Keep changes focused and add tests for protocol parsing or behaviour changes.
