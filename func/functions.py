import yaml
from PIL import Image

# 配置文件读取
def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_xy_value(image_path, x_float, y_float):
    image = Image.open(image_path)
    width, height = image.size

    x = int(x_float * width  // 2)
    y = int(y_float * height // 2)
    return x, y