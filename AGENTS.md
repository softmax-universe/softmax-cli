# Softmax CLI

Owns the `softmax` command, interactive Python login, browser callback and terminal output in the `softmax` namespace.
Read [package contracts](.contracts/index.md) and ancestor guidance. Change contracts only when explicitly requested.
Portable operations belong to the bundled `src/softmax_client` modules, documented in [CLIENT.md](CLIENT.md). Follow the
root E2E/system-only test policy and the shared
[client operation arguments](../../.contracts/003-client-operation-arguments/CONTRACT.md) contract.

Run from the repository root in the pinned Nix environment:

```sh
uv run --package softmax-cli ruff check workspaces/softmax/cli
uv run --package softmax-cli ty check workspaces/softmax/cli/src
bazel test //workspaces/softmax/cli/...
uv run lint-imports
```

Exercise real local authentication with isolated saved credentials before publishing changes to login or player
selection. Build the wheel and run its commands outside the checkout on Python 3.11 and 3.12. The
[publishing guide](../../../packages/metta-dev/src/metta/setup/tools/PUBLISHING.md) owns release setup and order.

Publish the command and shared client together with `metta publish softmax`. Keep one `softmax-cli` distribution,
`softmax-v*` tag stream and existing PyPI publisher. Check installed public client imports before running CLI commands,
so the verification catches client imports that accidentally initialize commands or callback-server frameworks.
