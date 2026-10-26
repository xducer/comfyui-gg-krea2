import inspect

import torch

import nodes

FIT_MODES = ["fit", "crop (legacy)"]
NEGATIVE_MODES = ["zero (CFG 1)", "grounded (CFG > 1)"]
POSITIONS = ["aligned (trained)", "beside (right of target)", "bag of features"]
# Default per-layer weights of Conditioning Krea2 Rebalance by nova452
# (https://github.com/nova452/ComfyUI-ConditioningKrea2Rebalance, Apache-2.0).
REBALANCE_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.5, 5.0, 1.1, 4.0, 1.0]


def rebalance_conditioning(conditioning, multiplier):
    # Krea 2 conditioning concatenates 12 text encoder layer taps; each tap gets its own weight.
    out = []
    for cond, extras in conditioning:
        gains = torch.tensor(REBALANCE_WEIGHTS, dtype=cond.dtype, device=cond.device) * multiplier
        out.append([(cond.unflatten(-1, (len(REBALANCE_WEIGHTS), -1)) * gains[:, None]).flatten(-2), extras.copy()])
    return out


def krea2edit_node(name):
    node = nodes.NODE_CLASS_MAPPINGS.get(name)
    if node is None:
        raise RuntimeError(f"Krea2 Edit Prep needs the comfyui-krea2edit pack ({name} is not installed). Install "
                           "version 2.0.0 or newer with git clone from https://github.com/lbouaraba/comfyui-krea2edit")
    return node()


class Krea2EditPrep:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "Krea 2 with an edit LoRA (identity or general) applied"}),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "latent": ("LATENT", {"tooltip": "the same latent you feed KSampler.latent_image"}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "grounding_px": ("INT", {"default": 1024, "min": 0, "max": 4096, "step": 64,
                                         "tooltip": "lower = stronger edit adherence, higher = stronger identity; 0 = native"}),
                "fit_mode": (FIT_MODES, {"default": "fit"}),
                "image_boost": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1000.0, "step": 0.01, "round": 0.001,
                                          "tooltip": "fidelity to image; 0 leaves image out"}),
                "image_b_boost": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1000.0, "step": 0.01, "round": 0.001,
                                            "tooltip": "fidelity to image_b; 0 leaves image_b out"}),
                "negative": (NEGATIVE_MODES, {"default": NEGATIVE_MODES[0],
                                              "tooltip": "grounded = empty prompt on the same images, the trained unconditional for CFG > 1"}),
                "image_position": (POSITIONS, {"default": POSITIONS[0],
                                               "tooltip": "aligned = pinned to the output layout; beside = identity without the layout pin, "
                                                          "restages more freely, needs a width that is a multiple of 16; bag of features = experimental"}),
                "image_b_position": (POSITIONS, {"default": POSITIONS[1],
                                                 "tooltip": "beside keeps the person's identity but copies much less of the photo's pose and lighting; needs a width that is a multiple of 16"}),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "scene, or the only reference"}),
                "image_b": ("IMAGE", {"tooltip": "subject; used as the only reference when image is absent"}),
                "image_mask": ("MASK", {"tooltip": "region of image its boost applies to, e.g. a face; "
                                                   "used only when image is the only reference"}),
                "image_b_mask": ("MASK", {"tooltip": "region of image_b its boost applies to, e.g. the face"}),
                "rebalance": ("BOOLEAN", {"default": False,
                                          "tooltip": "applies Conditioning Krea2 Rebalance's default per-layer weights to positive and a grounded negative"}),
                "rebalance_multiplier": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.05,
                                                   "tooltip": "scales every layer; about 0.7-0.8 with the V2 LoRAs, 1.0 with V1.2 or no edit LoRA"}),
            },
        }

    RETURN_TYPES = ("MODEL", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("model", "positive", "negative")
    FUNCTION = "prep"
    CATEGORY = "krea2edit/gg"
    DESCRIPTION = ("Prepares model and conditioning for KSampler from zero, one or two reference images: "
                   "no image = text-to-image without the source patch, one image = single-reference edit, "
                   "two = scene + subject. A boost of 0 leaves that image out. Needs comfyui-krea2edit 2.0.0 or newer.")

    def prep(self, model, clip, vae, latent, prompt, grounding_px, fit_mode, image_boost, image_b_boost,
             negative, image_position, image_b_position,
             image=None, image_b=None, image_mask=None, image_b_mask=None, rebalance=False, rebalance_multiplier=1.0):
        # A boost of 0 leaves the image out. The Krea2 Edit nodes ignore the second slot without
        # the first, so a lone image moves up.
        refs = [(ref, boost, mask, position) for ref, boost, mask, position in
                ((image, image_boost, image_mask, image_position), (image_b, image_b_boost, image_b_mask, image_b_position))
                if ref is not None and boost > 0]
        (first, first_boost, _, _), (second, second_boost, _, _) = (refs + [(None, 1.0, None, None)] * 2)[:2]

        encoder = krea2edit_node("Krea2EditGroundedEncode")
        positive = encoder.encode(clip, prompt, image=first, image_b=second, grounding_px=grounding_px)[0]
        if rebalance:
            positive = rebalance_conditioning(positive, rebalance_multiplier)
        if negative == NEGATIVE_MODES[1]:
            negative = encoder.encode(clip, "", image=first, image_b=second, grounding_px=grounding_px)[0]
            if rebalance:
                negative = rebalance_conditioning(negative, rebalance_multiplier)
        else:
            negative = nodes.ConditioningZeroOut().zero_out(positive)[0]

        # Without a reference the source patch would add a blank source image.
        if first is None:
            return (model, positive, negative)

        # The patch's ref_boost and ref_position apply to the last reference, the _a inputs to the first of two.
        ref_boost, ref_boost_a = (second_boost, first_boost) if second is not None else (first_boost, 1.0)
        # The patch masks only the last reference's boost. Load Image's MASK is empty when nothing
        # is painted, which would cancel the boost, so an empty mask means the whole image.
        mask = refs[-1][2]
        if mask is not None and not mask.any():
            mask = None
        # The image path replaces source_latent; one batch item keeps its normalization from failing on batches.
        source = {"samples": latent["samples"][:1]}
        patch = krea2edit_node("Krea2EditModelPatch")
        position, position_a = refs[-1][3], refs[0][3]
        # Versions before 2.0.0 accept and drop unknown inputs, so the positions would be silently ignored.
        if (position, position_a) != (POSITIONS[0], POSITIONS[0]) and "ref_position" not in inspect.signature(patch.patch).parameters:
            raise RuntimeError("Krea2 Edit Prep's position settings need comfyui-krea2edit 2.0.0 or newer. Update it with "
                               "git pull (ComfyUI Manager still installs 1.2.3), or set both positions to aligned.")
        model = patch.patch(
            model, source, vae=vae, source_image=first, source_image_b=second, target_latent=latent,
            fit_mode=fit_mode, ref_boost=ref_boost, ref_boost_a=ref_boost_a, ref_boost_mask=mask,
            ref_position=position, ref_position_a=position_a)[0]
        return (model, positive, negative)


NODE_CLASS_MAPPINGS = {"Krea2EditPrep": Krea2EditPrep}
NODE_DISPLAY_NAME_MAPPINGS = {"Krea2EditPrep": "Krea2 Edit Prep (gg)"}
