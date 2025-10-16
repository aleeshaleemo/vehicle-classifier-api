import numpy as np
from PIL import Image
from typing import Tuple


def preprocess_image(image: Image.Image, input_size: Tuple[int, int] = (224, 224)) -> np.ndarray:
    image = image.resize(input_size, Image.BILINEAR)
    img_data = np.array(image).astype('float32') / 255.0
    img_data = np.transpose(img_data, (2, 0, 1))
    img_data = np.expand_dims(img_data, axis=0)
    return img_data


def postprocess_output(output: np.ndarray) -> Tuple[int, float]:
    pred_index = int(np.argmax(output))
    confidence = float(np.max(output))
    return pred_index, confidence


def get_class_name(index: int) -> str:
    classes = ["front_vehicle", "rear_vehicle"]
    if 0 <= index < len(classes):
        return classes[index]
    else:
        return "unknown"
