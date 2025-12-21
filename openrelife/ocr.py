from doctr.models import ocr_predictor

ocr = ocr_predictor(
    pretrained=True,
    det_arch="db_mobilenet_v3_large",
    reco_arch="crnn_mobilenet_v3_large",
)


def extract_text_from_image(image):
    result = ocr([image])
    text = ""
    words_with_coords = []
    
    for page in result.pages:
        page_height, page_width = page.dimensions
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    text += word.value + " "
                    # Store word with normalized coordinates (0-1 range)
                    x1, y1 = word.geometry[0]
                    x2, y2 = word.geometry[1]
                    words_with_coords.append({
                        'text': word.value,
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2
                    })
                text += "\n"
            text += "\n"
    return text, words_with_coords
