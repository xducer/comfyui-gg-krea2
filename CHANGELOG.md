# Changelog

## Unreleased (0.3.1)

- New `image_use` and `image_b_use` (default **grounding + source**, as before): send an image to the grounding only (objects, outfits, scenes by meaning, layout free, no source tokens) or the source only (pixels, e.g. a face). See Grounding and source in the README.
- Fixed: streaks along the right or bottom edge at output sizes that aren't a multiple of 16. The engine now pads like ComfyUI's native Krea 2 model ([krea2edit#35](https://github.com/lbouaraba/comfyui-krea2edit/issues/35)).
- The node moved from **krea2edit → gg** to **krea2 → gg** in the node menu. Saved workflows are unaffected.
- A quick reference in the node's help panel (select the node, click the info button): common setups, one line per control, V1.2 vs V2 edit LoRAs.

## 0.3.0 (2026-10-29)

- comfyui-krea2edit is no longer needed: its edit engine is included in this pack.
- Node ID, inputs, outputs and defaults are unchanged, so saved workflows keep working. Output was pixel-identical to 0.2.1 in regression tests with the V1.2 and V2 edit LoRAs.
- License changed from Apache-2.0 to GPL-3.0.

## 0.2.1 (2026-10-27)

- The README and tooltips name the Identity Edit V1.2 LoRA.

## 0.2.0 (2026-10-26)

- Built-in Rebalance option (`rebalance`, `rebalance_multiplier`).

## 0.1.1 (2026-10-26)

- Clear errors when comfyui-krea2edit is missing or older than 2.0.0.

## 0.1.0 (2026-10-26)

- First release: zero, one or two reference images, with per-image boosts, masks and positions.
