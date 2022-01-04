import os.path
import logging
import pyogg
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

base_file_start = r'<?xml version="1.0" encoding="UTF-8"?>' + '\n' + \
                r'<!DOCTYPE svg PUBLIC "-//W3C//DRD SVG 1.1//EN" ' \
                r'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + '\n' + \
                r'<svg xmlns="http://www.w3.org/2000/svg"' + '\n' + \
                r'xmlns:xlink="http://www.w3.org/1999/xlink"' + '\n' + \
                r'xmlns:ev="http://www.w3.org/2001/xml-events" version="1.1"' + '\n' + \
                r'width="600" ' + '\n' + \
                r'height="100" ' + '\n' + \
                r'>'
base_file_end = r'</svg>'

x_placeholder = 'X_VAL'
y_placeholder = 'Y_VAL'
h_placeholder = 'H_VAL'
w_placeholder = 'W_VAL'
box_template = r'<rect ' \
                r'y="' + y_placeholder + r'" '\
                r'x="' + x_placeholder + r'" '\
                r'height="' + h_placeholder + '" ' \
                r'width="' + w_placeholder + '" ' \
                r'style="fill:rgb(255,255,255)"/>'


def create_graph(y_values, target):
    scaled_y_values = []
    for y in y_values:
        m = max(y_values)
        scaled_y = (int(100 * y / m))
        scaled_y = scaled_y - scaled_y % 10
        scaled_y = max(scaled_y, 10)
        scaled_y_values.append(scaled_y)

    file_content = base_file_start
    for i in range(len(scaled_y_values)):
        curr_box = box_template.replace(x_placeholder, str(i * 20))
        curr_box = curr_box.replace(y_placeholder, str(100 - scaled_y_values[i]))
        curr_box = curr_box.replace(h_placeholder, str(scaled_y_values[i]))
        curr_box = curr_box.replace(w_placeholder, '10')
        file_content += curr_box + '\n'

    file_content += base_file_end

    with open(target, 'w') as f:
        f.write(file_content)


def get_ogg_values(path, target_amount=30):
    opus_file = pyogg.OpusFile(path)
    buf = opus_file.as_array()
    n = buf.shape[0]
    step_size = int(n / target_amount)

    value_list = []
    for i in range(target_amount):
        value_list.append(int(buf[i * step_size]))

    return value_list


def svg_to_pdf(svg_path, delete=True):
    dirname, fname = os.path.split(svg_path)

    if fname.endswith('.svg'):
        pdf_path = os.path.join(dirname, fname[:-4] + '.pdf')
    else:
        pdf_path = os.path.join(dirname, fname + '.pdf')

    drawing = svg2rlg(svg_path)
    renderPDF.drawToFile(drawing, pdf_path)

    if delete:
        os.remove(svg_path)

    return pdf_path


def ogg_to_pdf(source_path, target_path):
    if source_path.endswith('.ogg'):
        dirname, fname = os.path.split(source_path)
        v = get_ogg_values(source_path)
        nfn = fname[:-3] + 'svg'
        full_target_path = os.path.join(target_path, nfn)
        create_graph(v, full_target_path)
        return svg_to_pdf(full_target_path, True)
    else:
        logging.error('{} is not an OGG file')
        return None
