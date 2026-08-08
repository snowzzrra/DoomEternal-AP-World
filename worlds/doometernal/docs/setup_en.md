# DOOM Eternal Randomizer Setup Guide

## Required software

- A legally obtained, player-supplied installation of DOOM Eternal. Game files are not distributed by this project.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases/latest) with `doometernal.apworld` installed.
- The matching DOOM Eternal Archipelago beta client and mod ZIP.
- On Windows, [EternalModManager](https://github.com/brunoanc/EternalModManager).
- On Linux, [EternalModInjectorShell](https://github.com/leveste/EternalBasher).

The launcher asks before acquiring pinned external tools. Downloads are verified before installation. You may select an
existing local copy instead. Meathook, mod managers, injectors, and third-party scripts are not bundled in this release.

## Install the APWorld and connect

1. Open `doometernal.apworld` with Archipelago Launcher, then restart the launcher.
2. Open **DOOM Eternal Client** and select the extracted beta `client` directory when requested.
3. Enter the room address, slot name, and password if required.
4. Wait for the client to receive the room snapshot, compile the slot-specific mod, and prepare installation.

Only one client may use a profile. The launcher never starts DOOM Eternal and does not provide a game-launch button.
Open the game yourself through Steam whenever you are ready. Close the DOOM Eternal Client to stop its supervised
bridge; close DOOM Eternal normally through the game or Steam.

## Windows installation

1. Select the DOOM Eternal directory containing `DOOMEternalx64vk.exe`.
2. Consent to installing pinned EternalModManager, or select a verified local copy.
3. Let the launcher place the generated mod ZIP in the game's `Mods` directory and open EternalModManager.
4. Select the mod and press **Run Injector** in EternalModManager.
5. Return to the launcher only after the manager has completed successfully, then start DOOM Eternal through Steam.

EternalModManager 4.2.3 does not expose a stable public command-line injector. The launcher therefore reports
`manual_action_required` and never claims that injection succeeded based only on opening the manager.

## Linux and Steam/Proton installation

1. Select the Steam library containing DOOM Eternal (Steam App ID `782330`) if discovery is ambiguous.
2. Consent to installing pinned EternalModInjectorShell, or select a verified local copy.
3. Let the launcher place the generated mod ZIP in `DOOMEternal/Mods` and run EternalModInjectorShell.
4. Keep DOOM Eternal configured to use its existing Steam compatibility tool. Do not start
   `DOOMEternalx64vk.exe` directly with Wine.

DOOM Eternal needs this Steam launch-option entry for Meathook under Proton:

```text
WINEDLLOVERRIDES="XINPUT1_3=n,b" %command%
```

The launcher preserves existing arguments, merges an existing `WINEDLLOVERRIDES`, keeps `%command%` and arguments after
it, shows the proposed diff, and asks permission before writing. It backs up the previous value and offers restoration.
If Steam is open or safe VDF editing is unavailable, use **Copy instruction** and paste the shown value into
**DOOM Eternal → Properties → Launch Options**. Start the game through Steam so its configured Proton prefix and version
remain in effect.

## Troubleshooting

- **Client files not found:** point `doom_eternal_options.client_directory` to the extracted matching `client` folder.
- **Dependency verification failed:** do not run the file; retry or select an official local artifact with the expected
  version and SHA-256.
- **Steam option not changed:** close Steam completely, retry, or use **Copy instruction**.
- **Bridge does not connect to the game:** confirm one bridge is running, the mod was injected, and the Steam launch
  option contains the required `XINPUT1_3` override.
