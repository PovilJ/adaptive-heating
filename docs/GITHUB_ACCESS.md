# GitHub access for the worker

Repository: https://github.com/PovilJ/adaptive-heating

Home Assistant's GitHub integration and the coding worker's GitHub credentials
are separate connections. Adding the former does not authenticate shell Git or
give the worker repository write access.

At initial build time this worker:

- had no callable GitHub connector;
- had no GitHub CLI, GitHub token environment variable, or SSH-agent connection;
- could not resolve `github.com` from shell Git;
- could not inspect or clone the remote repository.

The local project is therefore prepared independently. Fetch and inspect the
remote before publishing; it may already contain a README, license or commits.
Do not force-push over that history.

## Connect a coding GitHub plugin

If the worker supports the GitHub plugin/connector, connect it in the coding
application and grant access to `PovilJ/adaptive-heating`. A new worker session may
be necessary before its tools become visible. Connector access does not
automatically guarantee authenticated shell Git or permission to publish files;
the available capabilities must be checked.

## Shell Git alternative

For this single repository, a write-enabled SSH deploy key is a narrower option
than granting broad account access. Create/store its private half through the
worker's secure persistent credential mechanism; add only its public half under
the repository's Settings → Deploy keys and allow write access. GitHub documents
the setup at https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys.

Do not put a password, access token or private key in chat, the public project, or
a Git remote URL. The worker also needs working DNS/outbound access to GitHub;
authentication cannot fix the current DNS failure.

## Publish from an already-authenticated computer

The build can be handed off as a Git bundle without any credentials. Clone the
actual GitHub repository on that computer first, import the build bundle into a
temporary branch, and cherry-pick the build commit onto a branch based on the
remote history. Review conflicts if the repository already contains files, then
push normally. If the remote is empty, the build commit can become its first
branch. No force push is needed in either case.

Once repository access exists, the next worker can fetch the remote, reconcile
its history, push a review branch, and run validation with the real HA runtime.
