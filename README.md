# Skybound Steps

A small 3D platformer built with Python and Ursina. Explore a chain of floating islands, gather shards, light checkpoints, dodge red flares, ride moving platforms, and reach the summit beacon.

The game includes generated image assets in `assets/`: a photorealistic sky panorama, grass/rock/wood/bark textures, an explorer character sprite set, and animated flare hazard sprites.

Music in `music/` crossfades from `track1.mp3` to `track2.mp3` when the player reaches Sunspoke Garden.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Controls

- Mouse: look around
- `WASD`: move
- `Space`: jump
- `Shift`: sprint
- `R`: restart
- `Esc`: pause

Collect every shard if you want the cleanest finish, or just explore and make it to the beacon.

## iPhone Safari prototype

The Godot 4 mobile port lives in `mobile/` and uses the existing art and music.
It targets the Compatibility renderer, landscape play, and a single-threaded web
export for iPhone Safari.

```powershell
godot --editor project.godot
godot --headless --export-release Web dist/index.html
```

Touch controls use a virtual stick on the left, drag-to-look on the right, and a
large jump button. Push the stick fully to sprint. The opening tap unlocks audio
on Safari.
