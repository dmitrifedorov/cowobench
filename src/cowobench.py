#!/usr/bin/python3.8
'''
Copyright 2018 by EKDF Consulting and Dmitri Fedorov

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Dmitri Fedorov
@copyright: 2020 by EKDF Consulting and Dmitri Fedorov
@file cowobench.py
'''

# makes a movie out of results and generates a recon map

RESULT_DIRECTORY = "C:\\Users\\dfedorov\\!nosync\\!cow"

MAP_CHANGE_RATE_PER_SECOND = 10

REALM_WIDTH = 50
REALM_HEIGHT = 50
REALM_BORDER = 1
REALMS_MAX_X = 38
REALMS_MAX_Y = 38

EMPTY_IMAGE_RGBA = (255, 255, 255)
RGBA = 'RGB'

from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio, numpy, os, datetime, itertools
from collections import namedtuple

do_recon = False
known_units = []
known_digs = []

XY = namedtuple('XY', 'x, y')
UnitIconPosition = namedtuple('UnitIconPosition', 'icon, position')


def get_table(data: str, is_turn_map: bool) -> []:
    """Give the data, yields one curr_table"""

    class TurnResultHTMLParser(HTMLParser):
        """HTML parcer helper"""
        tables = []
        curr_table = []
        curr_row = []
        is_table_data = False
        colour = None

        def handle_starttag(self, tag: str, attrs: ()):
            if tag == 'table':
                self.is_table_data = True
            elif tag == 'td':
                for attr, value in attrs:
                    if attr == 'bgcolor':
                        self.colour = value
                        break

        def handle_endtag(self, tag: str):
            if tag == 'table':
                self.tables.append(self.curr_table)
                self.curr_table = []
                self.is_table_data = False
            elif tag == 'tr':
                self.curr_table.append(self.curr_row)
                self.curr_row = []

        def handle_data(self, data: str):
            if self.is_table_data:
                value = data.strip()
                if len(value) > 0:
                    self.curr_row.append((value, self.colour))

    parser = TurnResultHTMLParser()
    parser.feed(data)
    if is_turn_map:
        yield parser.tables[-1]
    else:
        for table in parser.tables:
            yield table


def html_colour_to_rgba(html_colour: str) -> ():
    """Convers HTML colout to its RGB values"""
    html_colour = html_colour.strip()
    if html_colour[0] == '#':
        html_colour = html_colour[1:]
    return tuple([int(x, 16) for x in (html_colour[:2], html_colour[2:4], html_colour[4:], '0')])


def write_on_cell(cell_image: Image, cell_content: str,
                  is_zero_cell: bool=False, zero_call_label: str=None):
    """Write text on one cell"""
    CELL_POINTS_FONT_TYPE = 'arial.ttf'
    CELL_POINTS_FONT_SIZE = 18
    CELL_POINTS_FONT = ImageFont.truetype(CELL_POINTS_FONT_TYPE, CELL_POINTS_FONT_SIZE)
    CELL_POINTS_POSITION = (7, 7)
    ZERO_CELL_FONT_TYPE = 'arialbd.ttf'
    ZERO_CELL_FONT_SIZE = 30
    ZERO_CELL_FONT = ImageFont.truetype(ZERO_CELL_FONT_TYPE, ZERO_CELL_FONT_SIZE)
    ZERO_CELL_POSITION = (1, 1)
    TRANSPARENT_FILL = (0, 0, 0, 255)

    draw_context = ImageDraw.Draw(cell_image)
    if is_zero_cell:
        draw_context.text(ZERO_CELL_POSITION, zero_call_label, font=ZERO_CELL_FONT, fill=TRANSPARENT_FILL)
    else:
        realm_points = cell_content.split(' ')[0]
        draw_context.text(CELL_POINTS_POSITION, realm_points, font=CELL_POINTS_FONT, fill=TRANSPARENT_FILL)


def write_unit_name(cell_image: Image, unit_name: str):
    """Write text on one cell"""
    CELL_POINTS_FONT_TYPE = 'seguisym.ttf'
    CELL_POINTS_FONT_SIZE = 10
    CELL_POINTS_FONT = ImageFont.truetype(CELL_POINTS_FONT_TYPE, CELL_POINTS_FONT_SIZE)
    CELL_POINTS_POSITION = (0, 35)
    TRANSPARENT_FILL = (255, 255, 255, 255)

    draw_context = ImageDraw.Draw(cell_image)
    draw_context.text(CELL_POINTS_POSITION, unit_name, font=CELL_POINTS_FONT, fill=TRANSPARENT_FILL)


def mark_moved_unit(cell_image: Image, table_index: int, cell_index: int, row_index: int):
    mark_unit('crossed-swords.png', cell_image, table_index, cell_index, row_index)


def mark_attacked_unit(cell_image: Image, table_index: int, cell_index: int, row_index: int):
    mark_unit('dagger-knife.png', cell_image, table_index, cell_index, row_index)


def mark_unit(mark_filename: str, cell_image: Image, table_index: int, cell_index: int, row_index: int):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cell_icon = Image.open(os.path.join(dir_path, mark_filename)).resize((35, 35))
    cell_image.paste(cell_icon, (7, 7), cell_icon)
    write_table_index(cell_icon, table_index)
    if do_recon:
        known_units.append(UnitIconPosition(cell_icon, XY(cell_index, row_index)))


def mark_dig(cell_image: Image, table_index: int, cell_index: int, row_index: int):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cell_icon = Image.open(os.path.join(dir_path, 'dig.png')).resize((35, 35))
    cell_image.paste(cell_icon, (7, 7), cell_icon)
    write_table_index(cell_icon, table_index)
    known_digs.append(UnitIconPosition(cell_icon, XY(cell_index, row_index)))


def write_table_index(cell_image: Image, table_index: int):
    """Write table index on one cell"""
    CELL_POINTS_FONT_TYPE = 'arialbd.ttf'
    CELL_POINTS_FONT_SIZE = 18
    CELL_POINTS_FONT = ImageFont.truetype(CELL_POINTS_FONT_TYPE, CELL_POINTS_FONT_SIZE)
    CELL_POINTS_POSITION = (19, 19)
    TEXT_FILL = (0, 0, 0, 255)
    draw_context = ImageDraw.Draw(cell_image)
    draw_context.text(CELL_POINTS_POSITION, str(table_index), font=CELL_POINTS_FONT, fill=TEXT_FILL)


def get_one_row_image(table_index: int, zero_cell_label: str, row_index: int, row_data: [], prev_row_data: []) -> Image:
    """Build one row image from the row data"""
    row_image = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT), EMPTY_IMAGE_RGBA)
    for cell_index, cell_data in enumerate(row_data):
        cell_content, cell_colour = cell_data
        cell_image = Image.new(RGBA, (REALM_WIDTH - REALM_BORDER * 2, REALM_HEIGHT - REALM_BORDER * 2),
                               html_colour_to_rgba(cell_colour))
        if row_index == 0 and cell_index == 0:
            write_on_cell(cell_image, cell_content, True, zero_cell_label)
        else:
            write_on_cell(cell_image, cell_content)
        
        if do_recon:
            for known_unit in known_units:
                if known_unit.position == XY(cell_index, row_index):
                    cell_image.paste(known_unit.icon, (7, 7), known_unit.icon)
            for known_dig in known_digs:
                if known_dig.position == XY(cell_index, row_index):
                    cell_image.paste(known_dig.icon, (7, 7), known_dig.icon)
            if prev_row_data:
                curr_cell_content = cell_content.split(' ')[0].split('-')[0].strip()
                prev_cell_content = prev_row_data[cell_index][0].split(' ')[0].split('-')[0].strip()
                if not prev_cell_content == curr_cell_content:
                    mark_dig(cell_image, table_index, cell_index, row_index)
        
        if len(cell_content.split(' ')) > 1:
            cell_contents = cell_content.split(' ')
            cell_symbol = cell_contents[1].strip()
            if cell_symbol in ['*']:
                mark_moved_unit(cell_image, table_index, cell_index, row_index)
            elif cell_symbol in ['+']:
                mark_attacked_unit(cell_image, table_index, cell_index, row_index)
            else:
                unit_name = cell_contents[-1] if not cell_contents[-1] == 'A' else cell_contents[-2]
                if not unit_name.isdigit() and do_recon:
                    write_unit_name(cell_image, unit_name)
            
        cell_image = ImageOps.expand(cell_image, REALM_BORDER)
        row_image.paste(cell_image, (cell_index * REALM_WIDTH, 0))
    return row_image


def get_adj_lists(map_label: str, is_turn_map: bool, turnmap_filename: str) -> Image:
    """builds one map"""
    prev_imp_table = None
    print('Processing file {0}...'.format(turnmap_filename))
    for table_index, one_table in enumerate(get_table(open(turnmap_filename).read()
                  .replace('<b>', ' ').replace('</b>', ' ')
                  .replace('<i>x1</i>', ' ').replace('<i>x2</i>', ' ').replace('<i>x3</i>', ' ').replace('<i>x4</i>', ' ')
                  .replace('<i>x5</i>', ' ').replace('<i>x6</i>', ' ').replace('<i>x7</i>', ' ').replace('<i>x8</i>', ' ')
                  .replace('<i>X1</i>', ' ').replace('<i>X2</i>', ' ').replace('<i>X3</i>', ' ').replace('<i>X4</i>', ' ')
                  .replace('<i>X5</i>', ' ').replace('<i>X6</i>', ' ').replace('<i>X7</i>', ' ').replace('<i>X8</i>', ' ')
                  .replace('<i>', ' ').replace('</i>', ' '),
                  is_turn_map)):
        print('Processing table {0}...'.format(table_index))
        one_map = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT * REALMS_MAX_Y), EMPTY_IMAGE_RGBA)
        for row_index, row_data in enumerate(one_table):
            one_map.paste(get_one_row_image(table_index,
                map_label if is_turn_map else '{0}-{1}'.format(map_label, table_index),
                row_index, row_data,
                prev_imp_table[row_index] if prev_imp_table else None),
                (0, row_index * REALM_HEIGHT))
        prev_imp_table = one_table
        yield one_map


def get_map_images(map_filenames: []) -> ():
    map_images = []
    last_image = None
    for label, is_turn_map, map_filename in map_filenames:
        for map_image in get_adj_lists(label, is_turn_map, map_filename):
            map_images.append(numpy.array(map_image))
            last_image = map_image
    return map_images, last_image


def write_recon(last_image: Image, filename: str):
    last_image.save(filename, format='png')
    print('Recon PNG done: {0}'.format(filename))


def write_video(map_images: [], filename: str):
    writer = imageio.get_writer(filename, fps=MAP_CHANGE_RATE_PER_SECOND)
    last_map_image = None
    for map_image in map_images:
        for _ in range (0, MAP_CHANGE_RATE_PER_SECOND):
            writer.append_data(map_image)
        last_map_image = map_image
    for _ in range (0, MAP_CHANGE_RATE_PER_SECOND*5):
        writer.append_data(last_map_image)
    writer.close()
    print('Video done: {0}'.format(filename))


# TODO: extract it from results file
FACTION_HTML_COLOUR_MAP = {
    'MUN': '#ff9900',
    'WW':  '#cc9933',
    'VUP': '#00cccc',
    'AAK': '#ffcc66',
    'CP':  '#006600',
    'VOX': '#999900',
    'TSC': '#993300',
    'ABY': '#C00000',
    'PAT': '#7030A0',
    'ROD': '#00B0F0',
    'BF4': '#66ffff',
    'ALT': '#F4B084',
    'NCR': '#666600',
    'TBB': '#0070C0',
    'WTF': '#cc66cc',
    'SOL': '#3333ff',
    'AP':  '#ffcc00',
    'BF4': '#993399',
    'DMT': '#ff0000',
    }

# TODO: extract it from results file
FACTION_HOME_REALM_MAP = {
    'CP':  XY(7, 7),
    'SOL': XY(7, 19),
    'AP':  XY(7, 31),
    'WTF': XY(19, 7),
    'VOX': XY(19, 19),
    'BF4': XY(19, 31),
    'NCR': XY(31, 7),
    'VUP': XY(31, 19),
    'DMT': XY(31, 31),
    }


def get_contrast_colour(hex_color: str, brightness_offset=50):
    rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]  # make sure new values are between 0 and 255
    return "#" + "".join([hex(i)[2:] for i in new_rgb_int])

    
def get_result_files(dir_name: str):
    return get_named_files('CoW_Results_Game_g7_Turn_', dir_name)
    

def get_impulse_files(dir_name: str):
    return get_named_files('CoW_impulse_map_Turn_', dir_name)


def get_named_files(name: str, dir_name: str):
    for file_name in os.listdir(dir_name):
        try:
            tokens = file_name.split(name)[1].split('_')
            turn_number = tokens[0]
            if len(tokens[0].split('.')) > 0:
                turn_number = tokens[0].split('.')[0]
            turn_number = int(turn_number)
            faction_name = None
            if len(tokens) > 1:
                faction_name = tokens[1].split('.')[0]
            yield (turn_number, faction_name, os.path.join(dir_name, file_name))
        except:
            pass


def get_turn_map_files(work_dir: str):
    MAX_TURNS = 100
    impulse_files = [x for x in get_impulse_files(work_dir)]
    result_files = [x for x in get_result_files(work_dir)]    
    map_files = []
    turn_result_count = None
    for turn_number in range(0, MAX_TURNS):
        impulse_file = next((x for x in impulse_files if x[0] == turn_number), None)
        result_file = next((x for x in result_files if x[0] == turn_number), None)
        if not impulse_file and not result_file:
            break
        if impulse_file:
            map_files.append(('{0}'.format(turn_number), False, os.path.join(work_dir, impulse_file[2])))
        if result_file:
            map_files.append(('T{0}'.format(turn_number), True, os.path.join(work_dir, result_file[2])))
        turn_result_count = turn_number
    print('Found {0} result files'.format(turn_result_count))
    last_turn_map_files = [x for i, x in enumerate(map_files) if x[1] and (i < turn_result_count * 2)]
    last_turn_map_files.extend(map_files[-2:])
    return turn_result_count, last_turn_map_files


def main(do_recon, include_units, exclude_units, dir):
    print('Collecting result files in directory {0}...'.format(dir))
    turn_result_count, map_files = get_turn_map_files(dir)
    
    print('Extracting map image files from result files...')
    map_images, last_image = get_map_images(map_files)

    print('Writing Turn {0} results and plans...'.format(turn_result_count))

    if do_recon:
        print('Generating Turn {0} recon ...'.format(turn_result_count + 1))
        write_recon(last_image, 'turn{0}-recon.png'.format(turn_result_count + 1))
        
    # do not write the animated PNG because nobody wants it
    # imageio.mimsave('{0}.png'.format(map_filename), map_images,
    # duration=MAP_CHANGE_RATE_PER_SECOND)
    # print('Animated PNG done.')
    
    write_video(map_images, 'turn{0}-result.mp4'.format(turn_result_count))


if __name__ == '__main__':
    do_recon = True
    main(do_recon, [], [], RESULT_DIRECTORY);
    exit(0)
    
    import argparse
    parser = argparse.ArgumentParser(description='Generate recon and plans.')
    parser.add_argument('-d', '--dir', help='working directory', default='./')
    parser.add_argument('-r', '--recon', help='generate recon', action='store_true', default=False)
    args = parser.parse_args()
    main(args.recon, args.dir);

