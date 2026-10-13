# GDScript that drops into a Godot project, on a local model

**Source thread:** https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/
**Works with:** Godot 4.x, Hermes with a local model through Ollama or llama.cpp
**Status:** Draft, untested. The Godot check commands below have not been run against a real Godot 4 project yet and may be wrong. In particular, checking a single script outside the project can report false "not declared" errors for autoloads and classes defined in other files. Don't rely on this loop until this note is removed.

## Request

Produce usable GDScript that plugs straight into an existing project, without going back and forth detail by detail in a chat window. Runs locally on a 16GB-VRAM GPU.

## Approach

Two changes matter more than prompt wording:

1. **Let Hermes check its own work.** Godot can parse scripts headlessly. Hermes writes the file, runs the check, reads the errors, and fixes them before it reports back.
2. **Make the model fit the GPU.** If a model spills from VRAM into system RAM, agent loops become very slow, because every tool call rereads a large context. On 16GB, a mixture-of-experts model that fits entirely in VRAM (for example Gemma 4 26B A4B at Q4, about 14-15GB) is usually much faster than a larger dense model that doesn't fit, at a modest quality cost.

## Setup

1. Put the Godot binary on `PATH` as `godot`. On macOS that's `/Applications/Godot.app/Contents/MacOS/Godot`.
2. Confirm the headless check works from the project root:

   ```bash
   godot --headless --path . --check-only --script res://scripts/player.gd
   ```

   Exit code 0 means the script parsed. Add `--debug` to also print GDScript warnings.
3. Write `AGENTS.md` (or a short Hermes skill) in the project with:
   - Godot version and whether the project uses static typing
   - Autoloads and what they own
   - Folder layout, node naming, and signal style
   - "Never edit `.tscn` or `project.godot` unless asked"
4. Check model fit: run `ollama ps` while the model is loaded. `100% GPU` means it fits; any CPU share means it's spilling. Lower the context length or pick a smaller quant or model until it fits.

## Steps

1. Give one small task at a time, for example:

   > Read AGENTS.md. In res://scripts/ship.gd, add screen-edge wrap-around using the viewport size. After editing, run `godot --headless --path . --check-only --script res://scripts/ship.gd` and fix any errors until it exits 0. Show me the diff and the final check output.

2. For changes that touch several scripts, have Hermes check each changed file, then load the whole project once:

   ```bash
   godot --headless --path . --quit
   ```

   This catches errors that only show up when scripts reference each other.
3. Run the game yourself and test the behavior.
4. When something fails in play, paste the runtime error or describe the behavior, and ask for a fix with the same check loop.

## Human Gates

- You are the playtester. A script that parses can still behave wrong.
- Commit before each task (`git commit -am "before: <task>"`) so a bad change is one `git checkout` away.
- Review diffs that touch scenes, autoloads, or input maps before keeping them.

## Verification

- The check command exits 0 for every changed script, and Hermes shows the output, not just "done".
- `godot --headless --path . --quit` loads the project without errors.
- The feature works when you play it.

## Common Pitfalls

- **Whole-game prompts.** "Build Asteroids" yields long, inconsistent code. "Add wrap-around to the ship" yields a script that fits.
- **Godot 3 syntax.** Local models often mix in Godot 3 APIs (`yield`, `KinematicBody2D`, `export var`). State the Godot version in AGENTS.md and let the check loop catch the rest.
- **Context too large for VRAM.** A long context window can push a model that otherwise fits onto the CPU. Start around 16-32K and raise it only if needed.
- **Trusting "fixed" without output.** Require the check command output in every reply.

## Follow-up

_None yet._
