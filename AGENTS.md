# AI Harness Agent Instructions

## Privileged commands

When a command needs `sudo` or another privileged authentication prompt, run it in a visible terminal window so the user can enter their password directly. Do not leave a hidden background process waiting for a password.

On graphical Linux sessions, use this pattern:

```bash
gnome-terminal -- bash -lc 'sudo <command>; printf "\nFinished. Press Enter to close.\n"; read'
```

Replace `<command>` with the complete command, for example:

```bash
gnome-terminal -- bash -lc 'sudo snap install android-studio --classic; printf "\nFinished. Press Enter to close.\n"; read'
```

Never request, record, print, or store the user’s password. If a graphical terminal is unavailable, stop and tell the user to run the privileged command in their own terminal.

After launching the visible terminal, tell the user where the prompt is and wait for confirmation before continuing with steps that depend on the privileged command.

## Change tracking

Run `graphify update .` after every code or documentation change, then run the relevant validation checks before committing. Push requested repository changes to the correct remote branch.
