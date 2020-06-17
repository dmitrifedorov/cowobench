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
@file cowert.py

'''

# makes a movie from impulse files of one or more last turns

RESULT_DIRECTORY = "C:\\Users\\dfedorov\\!nosync\\!cow"
NUMBER_OF_TURNS = 3

REALM_WIDTH = 50
REALM_HEIGHT = 50
REALM_BORDER = 1
REALMS_MAX_X = 38
REALMS_MAX_Y = 38

EMPTY_IMAGE_RGBA = (255, 255, 255)
RGBA = 'RGB'

MAP_CHANGE_RATE_PER_SECOND = 10

from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
from collections import namedtuple
import imageio, numpy, os, datetime, itertools

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
                if not unit_name.isdigit():
                    write_unit_name(cell_image, unit_name)
            
        cell_image = ImageOps.expand(cell_image, REALM_BORDER)
        row_image.paste(cell_image, (cell_index * REALM_WIDTH, 0))
    return row_image


def read_turnmap(turnmap_filename):
    with open(turnmap_filename) as result_file:
        return result_file.read().replace('<b>', ' ').replace('</b>', ' ')\
            .replace('<i>x1</i>', ' ').replace('<i>x2</i>', ' ').replace('<i>x3</i>', ' ').replace('<i>x4</i>', ' ')\
            .replace('<i>x5</i>', ' ').replace('<i>x6</i>', ' ').replace('<i>x7</i>', ' ').replace('<i>x8</i>', ' ')\
            .replace('<i>X1</i>', ' ').replace('<i>X2</i>', ' ').replace('<i>X3</i>', ' ').replace('<i>X4</i>', ' ')\
            .replace('<i>X5</i>', ' ').replace('<i>X6</i>', ' ').replace('<i>X7</i>', ' ').replace('<i>X8</i>', ' ')\
            .replace('<i>', ' ').replace('</i>', ' ')


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


def get_row_image(table_index: int, zero_cell_label: str, row_index: int, row_data: []) -> Image:
    row_image = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT), EMPTY_IMAGE_RGBA)
    for cell_index, cell_data in enumerate(row_data):
        cell_content, cell_colour = cell_data
        cell_image = Image.new(RGBA, (REALM_WIDTH - REALM_BORDER * 2, REALM_HEIGHT - REALM_BORDER * 2),
                               html_colour_to_rgba(cell_colour))
        if row_index == 0 and cell_index == 0:
            write_on_cell(cell_image, cell_content, True, zero_cell_label)
        else:
            write_on_cell(cell_image, cell_content)
        if len(cell_content.split(' ')) > 1:
            cell_contents = cell_content.split(' ')
            cell_symbol = cell_contents[1].strip()
            if cell_symbol in ['*']:
                mark_moved_unit(cell_image, table_index, cell_index, row_index)
            elif cell_symbol in ['+']:
                mark_attacked_unit(cell_image, table_index, cell_index, row_index)
        cell_image = ImageOps.expand(cell_image, REALM_BORDER)
        row_image.paste(cell_image, (cell_index * REALM_WIDTH, 0))
    return row_image


def get_one_map(impulse_files) -> Image:
    for map_label, is_turn_map, turnmap_filename in impulse_files:
        print('Processing file {0}...'.format(turnmap_filename))
        for table_index, one_table in enumerate(get_table(read_turnmap(turnmap_filename), is_turn_map)):
            print('Table {0}...'.format(table_index))
            one_map = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT * REALMS_MAX_Y), EMPTY_IMAGE_RGBA)
            for row_index, row_data in enumerate(one_table):
                one_map.paste(get_row_image(table_index,
                                            map_label if is_turn_map else '{0}-{1}'.format(map_label, table_index),
                                            row_index, row_data),
                              (0, row_index * REALM_HEIGHT))
            yield one_map


def written(map_images, number_of_turns):
    if map_images and len(map_images) > 0:
        video_filename = 'last-{0}-turns-{1}.mp4'.format(number_of_turns, datetime.date.today())
        with imageio.get_writer(video_filename, fps=MAP_CHANGE_RATE_PER_SECOND) as writer:
            last_map_image = None
            for map_image in map_images:
                for _ in range(0, MAP_CHANGE_RATE_PER_SECOND):
                    writer.append_data(map_image)
                last_map_image = map_image
            for _ in range(0, MAP_CHANGE_RATE_PER_SECOND*5):
                writer.append_data(last_map_image)
            writer.close()
        return video_filename
    print('no map images collected')
    return False


def video_written(impulse_files, number_of_turns):
    def get_map_images(impulse_files):
        map_images = []
        for map_image in get_one_map(impulse_files):
            map_images.append(numpy.array(map_image))
        return map_images
    return written(get_map_images(impulse_files), number_of_turns) if (impulse_files and len(impulse_files) > 0) else None


def main(result_directory, number_of_turns):
    print('Collecting last {0} turns in directory {1}...'.format(number_of_turns, result_directory))
    video_filename = video_written([x for x in get_impulse_files(result_directory)][-number_of_turns:], number_of_turns)
    print('Video done: {0}'.format(video_filename) if video_filename else 'Video was not written.')


if __name__ == '__main__':
    main(RESULT_DIRECTORY, NUMBER_OF_TURNS)

