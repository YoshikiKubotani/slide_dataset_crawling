import json

def annotation_in_labelme_format(filename, annotation_list):
    shapes = []
    for d in annotation_list:
        x, y, w, h = d["x"], d["y"], d["width"], d["height"]
        shapes.append({
          "label": "text",
          "points": [[x, y], [x+w, y+h]],
          "group_id": None,
          "shape_type": "rectangle",
          "flags": {}
        })
    labelme = {
      "version": "5.0.1",
      "flags": {},
      "shapes": shapes,
      "imagePath": filename,
      "imageData": None,
      "imageHeight": 1024,
      "imageWidth": 1024
    }
    return labelme