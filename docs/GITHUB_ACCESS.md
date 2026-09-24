# GitHub access for development

Repository: https://github.com/PovilJ/adaptive-heating

Home Assistant's GitHub integration and a development worker's Git credentials
are separate connections. Adding the former does not authenticate shell Git.
Adaptive Heating's public release checks do not need a personal GitHub token.

## HTTPS access to this repository

For command-line development, use an authenticated Git credential manager or a
fine-grained personal access token restricted to `PovilJ/adaptive-heating`:

1. Open [GitHub's token creation page](https://github.com/settings/personal-access-tokens/new).
2. Select the repository owner and a suitable expiration.
3. Choose **Only select repositories**, then **adaptive-heating**.
4. Grant **Contents: Read and write**. Metadata read access is automatic.
5. Store the token through a credential manager or a restricted local credential
   file outside the project, and provide it to Git over its credential-helper
   interface. A file containing a token should have owner-only permissions.

Pull-request API operations additionally need **Pull requests: Read and write**;
ordinary Git pushes do not. See [GitHub's token documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

Do not put a password, token or private key in chat, source files, release
archives, command-line arguments or a Git remote URL. Keep credentials out of
Home Assistant entity mappings and out of the integration's runtime settings.

## Other connection options

If the worker supports the GitHub plugin/connector, connect it in the coding
application and grant access to `PovilJ/adaptive-heating`. A new worker session may
be necessary before its tools become visible. Connector access does not
automatically guarantee authenticated shell Git or permission to publish files;
the available capabilities must be checked.

With an SSH client available, a repository-specific deploy key is another option.
Store its private half in the development machine's credential storage; add only
the public half under the repository's Settings → Deploy keys and allow write
access. See [GitHub's deploy-key instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).

The development worker also needs working DNS and outbound access to GitHub.
Credentials do not override sandbox network restrictions. Configure the worker's
network policy separately through its host application.

## Publish from an already-authenticated computer

The build can be handed off as a Git bundle without any credentials. Clone the
actual GitHub repository on that computer first, import the build bundle into a
temporary branch, and cherry-pick the build commit onto a branch based on the
remote history. Review conflicts if the repository already contains files, then
push normally. If the remote is empty, the build commit can become its first
branch. No force push is needed in either case.

Before publishing, fetch and inspect the remote, reconcile any existing history,
run the documented validation, and push normally. Do not force-push over another
installation's or contributor's work. Push only this project, never the live
Home Assistant configuration directory.
