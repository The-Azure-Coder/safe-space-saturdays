# PixelLab Together asset pack

Starter pixel-art exports for the `Together` cooperative platformer. The files
are suitable for a Roblox 2D/GUI recreation or a sprite-based prototype.

## Contents

- `robot/rotations/`: original four 92×92 side-view robot rotations.
- `robot/variants/`: five block-like 64×64 robot variants, one per player seat
  (purple, coral, blue, green, yellow).
- `robot/animations/`: exported 4-frame idle and walk loops for the directions
  PixelLab completed.
- `tiles/meadow/`: sixteen 32×32 Wang tiles for the meadow world.
- `tiles/crystal/`: sixteen 32×32 Wang tiles for the crystal world.
- `manifest.json`: PixelLab IDs, prompts, job IDs, and import notes.

Use `pattern_4x4` and `connections` in the PixelLab response when building an
autotiler. For Roblox, import the PNGs as transparent `ImageLabel` or
`ImageButton` textures, keep nearest-neighbour sampling, and map the four robot
rotations to the avatar's horizontal facing state.

The manifest retains PixelLab job IDs and the exact direction coverage returned
by the service. Missing directions can be queued later into the same animation
group.
