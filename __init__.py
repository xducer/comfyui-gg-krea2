import nodes

FIT_MODES = ["fit", "crop (legacy)"]
NEGATIVE_MODES = ["zero (CFG 1)", "grounded (CFG > 1)"]


def krea2edit_node(name):
    node = nodes.NODE_CLASS_MAPPINGS.get(name)
    if node is None:
        raise RuntimeError(f"Krea2 Edit Prep needs the comfyui-krea2edit pack ({name} is not installed).")
    return node()


class Krea2EditPrep:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "Krea 2 with the identity edit LoRA applied"}),
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
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "scene, or the only reference"}),
                "image_b": ("IMAGE", {"tooltip": "subject; used as the only reference when image is absent"}),
                "image_mask": ("MASK", {"tooltip": "region of image its boost applies to, e.g. a face; "
                                                   "used only when image is the only reference"}),
                "image_b_mask": ("MASK", {"tooltip": "region of image_b its boost applies to, e.g. the face"}),
            },
        }

    RETURN_TYPES = ("MODEL", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("model", "positive", "negative")
    FUNCTION = "prep"
    CATEGORY = "krea2edit"
    DESCRIPTION = ("Prepares model and conditioning for KSampler from zero, one or two reference images: "
                   "no image = text-to-image with the model unpatched, one image = single-reference edit, "
                   "two = scene + subject. A boost of 0 leaves that image out.")

    def prep(self, model, clip, vae, latent, prompt, grounding_px, fit_mode, image_boost, image_b_boost,
             negative, image=None, image_b=None, image_mask=None, image_b_mask=None):
        # A boost of 0 leaves the image out. The Krea2 Edit nodes ignore the second slot without
        # the first, so a lone image moves up.
        refs = [(ref, boost, mask) for ref, boost, mask in
                ((image, image_boost, image_mask), (image_b, image_b_boost, image_b_mask))
                if ref is not None and boost > 0]
        (first, first_boost, _), (second, second_boost, _) = (refs + [(None, 1.0, None)] * 2)[:2]

        encoder = krea2edit_node("Krea2EditGroundedEncode")
        positive = encoder.encode(clip, prompt, image=first, image_b=second, grounding_px=grounding_px)[0]
        if negative == NEGATIVE_MODES[1]:
            negative = encoder.encode(clip, "", image=first, image_b=second, grounding_px=grounding_px)[0]
        else:
            negative = nodes.ConditioningZeroOut().zero_out(positive)[0]

        # Without a reference the source patch would add a blank source image.
        if first is None:
            return (model, positive, negative)

        # The patch's ref_boost applies to the last reference and ref_boost_a to the first of two.
        ref_boost, ref_boost_a = (second_boost, first_boost) if second is not None else (first_boost, 1.0)
        # The patch masks only the last reference's boost. Load Image's MASK is empty when nothing
        # is painted, which would cancel the boost, so an empty mask means the whole image.
        mask = refs[-1][2]
        if mask is not None and not mask.any():
            mask = None
        # The image path replaces source_latent; one batch item keeps its normalization from failing on batches.
        source = {"samples": latent["samples"][:1]}
        model = krea2edit_node("Krea2EditModelPatch").patch(
            model, source, vae=vae, source_image=first, source_image_b=second, target_latent=latent,
            fit_mode=fit_mode, ref_boost=ref_boost, ref_boost_a=ref_boost_a, ref_boost_mask=mask)[0]
        return (model, positive, negative)


NODE_CLASS_MAPPINGS = {"Krea2EditPrep": Krea2EditPrep}
NODE_DISPLAY_NAME_MAPPINGS = {"Krea2EditPrep": "Krea2 Edit Prep (gg)"}
