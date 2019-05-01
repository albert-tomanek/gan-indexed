import numpy as np

def onehot_to_indexed(imgs):
    return imgs.argmax(axis=-1)

def idx_to_rgb(imgs_idx, palette):
    return palette[imgs_idx]
