# Krea2 Edit Prep (gg)

Turns zero, one or two images into `model`, `positive` and `negative` for a KSampler. Connect the same `latent` to the KSampler. Apply the edit LoRAs before this node.

## Quick setups

| Goal | image | image_b | Settings |
| --- | --- | --- | --- |
| Text-to-image | – | – | defaults |
| Edit one picture | the picture | – | describe the edit |
| Put a person into a scene | scene | person (a body shot, not a tight headshot) | defaults |
| Keep the scene, take outfit and face from two photos | scene | outfit and face photos stitched side by side | defaults; crop the outfit photo below the chin; more reliable with V1.2 |
| Restage: scene design, outfit and face | outfit and scene photos stitched, **grounding only** | face, **pixels only** | V2 LoRAs; outfit photo cropped, plain background |
| Keep a design or style, restage freely | the image, **grounding only** | – | |

## Controls

- **boost**: 1.0 neutral, above 1 copies that image more closely, below 1 more loosely, 0 leaves it out.
- **mask**: limits the boost to the painted area; not an inpainting mask. Only the mask of the last image whose pixels are used applies (with defaults and two images: `image_b_mask`).
- **position**: `aligned` keeps the image's layout (scenes); `beside` keeps a likeness but restages it (people); `bag of features` is experimental and tends to paste face photos in.
- **use**: *grounding* lets the text encoder read the image (objects, outfits, scenes; layout free, faster); *pixels* puts the image itself in the model (faces; the layout when aligned). *Pixels only* works best with the V2 LoRAs; with V1.2 it is usually weaker. "First/second image" in the prompt count only grounded images. A boost of 0 leaves an image out of both.
- **grounding_px**: lower follows the prompt more, higher keeps identity; 1024 suits people.
- **negative**: *zero* at CFG 1 (Turbo); *grounded* at CFG above 1 (Raw). Raw at CFG ~3 follows the prompt more closely when a reference's pose competes with it.
- **rebalance**: per-layer weights; multiplier about 0.7–0.8 with the V2 LoRAs, 1.0 with V1.2 or no edit LoRA.
- **fit_mode**: keep `fit`.

## Edit LoRAs

- **Identity Edit V2 + General Edit V2** at about 0.5 each, never both at 1.0. They read more from the pixels: stronger likeness, but backgrounds leak more easily. Without images they add skin texture; mute them or use 0.25 each.
- **Identity Edit V1.2** at 1.0 relies more on grounding; *pixels only* is weak with it.

Full guide with examples: [README](https://github.com/xducer/comfyui-gg-krea2#readme)
