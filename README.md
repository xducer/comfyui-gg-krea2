<p align="center">
  <img src="assets/readme/routing.svg" width="100%" alt="Krea2 Edit Prep routing: no image gives text-to-image, one image in either slot gives a single-image edit, with a lone image_b moved into the first slot, and two images give a scene plus subject edit. Every case returns model, positive and negative for a KSampler.">
</p>

# GG Krea2

**Krea2 Edit Prep (gg)** turns zero, one or two reference images into a ready `model`, `positive` and `negative` for a KSampler, for Krea 2 with a Krea 2 Edit LoRA. It runs the Krea2 Edit nodes (grounded encode and source patch) internally, so you don't place them yourself.

![The same scene and person through each route: both images put the person on the chair under the scene's spotlight; image only keeps the scene with a generic person; image_b only keeps the person in a plain studio; no image gives a generic text-to-image result.](assets/readme/routes.jpg)

*One prompt and seed for all four: "the person from the second image sitting on the chair in the first image, blue backdrop". Krea 2 Turbo with the Identity Edit V2 LoRA, 9 steps, CFG 1, euler / normal, 832 × 1264, default node settings.*

## Requirements

- [comfyui-krea2edit](https://github.com/lbouaraba/comfyui-krea2edit) 2.0.0 or newer (older versions ignore the position settings).
- Krea 2 with one edit LoRA ([weights](https://huggingface.co/conradlocke/krea2-identity-edit)) applied **before** this node, plus any other LoRAs you use:
  - `krea2_identity_edit_v2` to put a person from one photo into a scene, pose or outfit;
  - `krea2_general_edit_v2` for instruction edits (remove, recolour, relight, backgrounds, objects, text).

  Use one per task. Both at 1.0 break the image; about 0.6 each if you combine them.
- The Krea 2 text encoder (Qwen3-VL) loaded with type `krea2`, as the Krea2 Edit nodes require.

## Install

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/xducer/comfyui-gg-krea2.git
```

Restart ComfyUI. The node is under **krea2edit** as **Krea2 Edit Prep (gg)**.

## Wiring

![A ComfyUI workflow: two Load Image nodes (scene and person) and an Empty Latent Image feed Krea2 Edit Prep along with the model, CLIP, VAE and prompt; its model, positive and negative go to a KSampler, which also takes the same latent, then VAE Decode and Preview Image.](assets/readme/wiring.png)

- **Into the node:** `model` (Krea 2 + edit LoRA and any other LoRAs), `clip`, `vae`, `latent`, `prompt`, and optionally `image`, `image_b` and their masks.
- **Out to the KSampler:** `model`, `positive` and `negative`.

Connect the same `latent` to the KSampler. Any batch size works. Seed, steps and sampler stay on the KSampler.

**Negative:** connect the node's `negative` straight to the KSampler; no extra ConditioningZeroOut is needed. With `negative` set to **zero**, the output already is the zeroed positive, and at CFG 1 ComfyUI doesn't evaluate the negative at all.

**Rebalance and other conditioning nodes** go between the node's `positive` and the KSampler, for example `positive → Conditioning Krea2 Rebalance → KSampler.positive` (from [ComfyUI-ConditioningKrea2Rebalance](https://github.com/nova452/ComfyUI-ConditioningKrea2Rebalance)). To turn it off, bypass it (Ctrl+B). At CFG above 1 with a **grounded** negative, CFG amplifies a rebalance applied only to the positive; try applying it to the negative too.

## The two image slots

`image` is always the first reference and `image_b` the second, whatever your files are called:

| Slot | Role |
| --- | --- |
| `image` (first) | **Scene**: the setting, plus the pose and clothing of any person already in it. Also the slot for single-image edits. |
| `image_b` (second) | **Subject**: the person carried into the scene, usually with their clothing unless the prompt changes it. |

| What arrives | Result |
| --- | --- |
| no image, or both boosts at 0 | Text-to-image: plain text encoding, model unpatched. |
| one image (the other missing or at boost 0) | Single-image edit. A lone `image_b` moves into the first slot. |
| both | Scene + subject edit. |

With two images, "the first image" in the prompt is `image` and "the second image" is `image_b`. With one image, whichever slot it is in, it is the only image the model sees, so call it "the image".

## Boosts and masks

**A boost sets how closely the result copies that image.**

| Boost | Effect |
| --- | --- |
| 1.0 | Neutral (default). |
| above 1 | Copies that image more closely. Start at 1.3–1.5; far above 2 it can copy too literally (pasted-in lighting, the reference's pose or backdrop, duplicates). |
| below 1 | Copies it more loosely, so edits take hold more easily. |
| 0 | Leaves that image out entirely. |

**A mask limits that image's boost to the painted area.** Outside it the image keeps the neutral weight. It is not an inpainting mask: the prompt can still change anything anywhere.

- Paint it in the mask editor of the picture's Load Image node (right-click → Open in MaskEditor) and connect that node's `MASK`.
- The boost must differ from 1.0, or the mask has no effect.
- With both images, only `image_b_mask` applies; the scene can't be masked. With one image, that image's own mask applies.
- An empty mask (nothing painted) means the whole image, so leaving `MASK` connected is safe, unless the picture has transparency: Load Image then makes the transparent area the mask.

At 1.0 the identity LoRA usually reproduces the face well already. When you need a stronger boost on an `aligned` image, a face mask keeps it on the face, so the rest of the photo isn't copied too literally (see the board below).

## Positions

**A position sets whether the result keeps that image's layout.** Each image has its own; like the boosts, it follows the image, whichever slot it ends up in. `image` defaults to `aligned`, `image_b` to `beside`.

| Position | Effect |
| --- | --- |
| aligned (trained) | Pinned to the output layout, as the LoRAs were trained. |
| beside (right of target) | Placed next to the canvas: the identity still comes through, but the layout pin is gone, so the person can be restaged more freely. |
| bag of features | Experimental: the image's content without its layout. |

Keep the scene `aligned` so its layout and lighting carry over. For the person, `beside` keeps the likeness without copying the photo's pose and lighting, even at boost 2.5; on `aligned` the V2 identity LoRA tends to copy both. For a single-image edit that should keep the picture's layout, use `image` (aligned).

![A reference photo of a man mid-dance with his face painted as the mask, then four results on the chair: aligned at 1.0 copies the dance pose and the photo's hard wall shadow; aligned at 2.5 copies even more; aligned at 2.5 with the face mask looks like the 1.0 result; beside at 1.0 sits naturally under the scene's spotlight.](assets/readme/positions.jpg)

*Same scene, prompt, seed and sampler in all four; `image` stays aligned at 1.0. Only `image_b`'s position, boost and mask change.*

With `beside`, use an output width that is a multiple of 16 (for example 832 × 1264). Other widths get a streak of noise along the right edge ([krea2edit#35](https://github.com/lbouaraba/comfyui-krea2edit/issues/35)).

## Recipes

**Put the person from one photo into a scene**
1. `image` = the scene; `image_b` = the person. Leave the positions at their defaults (scene aligned, person beside).
2. Prompt: *The man from the second image sitting on the chair in the first image.*

**Put the face from one photo onto the person in another**
1. `image` = the photo with the body, pose, clothes and background to keep.
2. `image_b` = the photo with the face; paint the face (a little past hairline, ears and jaw) and connect its `MASK` to `image_b_mask`.
3. Leave the defaults. If likeness is weak, raise `image_b_boost` to 1.5–2.5; the face mask keeps the rest of that photo from being copied.
4. Prompt: *Give the man in the first image the face of the man in the second image. Keep his pose, clothing and the background unchanged.*

The LoRA restages a person; it is not a pixel-exact face swap. If too much of the face photo bleeds in, lower the boost or tighten the mask.

**Edit one picture and keep the face**
Connect only `image`, paint the face into `image_mask`, set `image_boost` to about 1.3, and describe the edit (*change his shirt to a black suit*).

**An edit that won't take**
In a single-image edit, paint the stubborn area (for example the shirt) into that image's mask and set its boost to 0.6–0.8 to loosen it. Keep it above 0, because 0 leaves the image out.

**Text-to-image**
Disconnect both images, mute or bypass their Load Image nodes, or set both boosts to 0.

## Other settings

- `negative`: **zero** for CFG 1 (Turbo, the negative isn't evaluated). **grounded** for CFG above 1 (e.g. the Raw model at CFG ~3): an empty prompt on the same images, the trained unconditional. It costs one extra encoder pass.
- `grounding_px`: caps the longest side of each image shown to the text encoder (smaller images are not enlarged; 0 = native size). Lower follows the instruction more, higher keeps identity better; 1024 suits people.
- `fit_mode`: keep `fit`; `crop (legacy)` is for older weights, and masks can drift with it.
- Generate at about 2 MP or less; larger outputs can bleed source content or duplicate subjects.
