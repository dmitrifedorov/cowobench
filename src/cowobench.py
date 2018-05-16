#!/usr/bin/python

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
@copyright: 2018 by EKDF Consulting and Dmitri Fedorov
'''

MAP_CHANGE_RATE_PER_SECOND = 1
MAP_FILENAME = 'turn15map'

DO_RECON = True

REALM_WIDTH = 50
REALM_HEIGHT = 50
REALM_BORDER = 1
REALMS_MAX_X = 32
REALMS_MAX_Y = REALMS_MAX_X
RGBA = 'RGBA'
EMPTY_IMAGE_RGBA = (255, 255, 255, 0)

from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio, numpy
imageio.plugins.ffmpeg.download()

known_units = []
known_digs = []


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


def write_unit(cell_image: Image, unit: str):
    """Write text on one cell"""
    CELL_POINTS_FONT_TYPE = 'seguisym.ttf'
    CELL_POINTS_FONT_SIZE = 10
    CELL_POINTS_FONT = ImageFont.truetype(CELL_POINTS_FONT_TYPE, CELL_POINTS_FONT_SIZE)
    CELL_POINTS_POSITION = (0, 35)
    TRANSPARENT_FILL = (255, 255, 255, 255)

    draw_context = ImageDraw.Draw(cell_image)
    draw_context.text(CELL_POINTS_POSITION, unit, font=CELL_POINTS_FONT, fill=TRANSPARENT_FILL)


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
        
        if DO_RECON:
            for known_unit in known_units:
                if (known_unit[0], known_unit[1]) == (row_index, cell_index):
                    cell_image.paste(known_unit[2], (7, 7), known_unit[2])
            for known_dig in known_digs:
                if (known_dig[0], known_dig[1]) == (row_index, cell_index):
                    cell_image.paste(known_dig[2], (7, 7), known_dig[2])
            if prev_row_data:
                curr_cell_content = cell_content.split(' ')[0].strip()
                prev_cell_content = prev_row_data[cell_index][0].split(' ')[0].strip()
                if not prev_cell_content == curr_cell_content:
                    cell_icon = Image.open('dig.png').resize((35, 35))
                    cell_image.paste(cell_icon, (7, 7), cell_icon)
                    write_table_index(cell_icon, table_index)
                    known_digs.append((row_index, cell_index, cell_icon))
        
        if len(cell_content.split(' ')) > 1:
            cell_contents = cell_content.split(' ')
            cell_symbol = cell_contents[1].strip()
            if cell_symbol in ['*']:
                cell_icon = Image.open('crossed-swords.png').resize((35, 35))
                cell_image.paste(cell_icon, (7, 7), cell_icon)
                write_table_index(cell_icon, table_index)
                if DO_RECON:
                    known_units.append((row_index, cell_index, cell_icon))
            elif cell_symbol in ['+']:
                cell_icon = Image.open('dagger-knife.png').resize((35, 35))
                cell_image.paste(cell_icon, (7, 7), cell_icon)
                write_table_index(cell_icon, table_index)
                if DO_RECON:
                    known_units.append((row_index, cell_index, cell_icon))
            else:
                unit = cell_contents[-1] if not cell_contents[-1] == 'A' else cell_contents[-2]
                if not unit.isdigit() and DO_RECON:
                    write_unit(cell_image, unit)
            
        cell_image = ImageOps.expand(cell_image, REALM_BORDER)
        row_image.paste(cell_image, (cell_index * REALM_WIDTH, 0))
    return row_image


def get_adj_lists(map_label: str, is_turn_map: bool, turnmap_filename: str) -> Image:
    """builds one map"""
    prev_imp_table = None
    for table_index, one_table in enumerate(
        get_table(open(turnmap_filename).read()
                  .replace('<b>', ' ').replace('</b>', ' ')
                  .replace('<i>x1</i>', ' ').replace('<i>x2</i>', ' ').replace('<i>x3</i>', ' ').replace('<i>x4</i>', ' ')
                  .replace('<i>x5</i>', ' ').replace('<i>x6</i>', ' ').replace('<i>x7</i>', ' ').replace('<i>x8</i>', ' ')
                  .replace('<i>X1</i>', ' ').replace('<i>X2</i>', ' ').replace('<i>X3</i>', ' ').replace('<i>X4</i>', ' ')
                  .replace('<i>X5</i>', ' ').replace('<i>X6</i>', ' ').replace('<i>X7</i>', ' ').replace('<i>X8</i>', ' ')
                  .replace('<i>', ' ').replace('</i>', ' '),
                  is_turn_map)):
        one_map = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT * REALMS_MAX_Y), EMPTY_IMAGE_RGBA)
        for row_index, row_data in enumerate(one_table):
            one_map.paste(get_one_row_image(
                table_index,
                map_label if is_turn_map else '{0}-{1}'.format(map_label, table_index),
                row_index, row_data,
                prev_imp_table[row_index] if prev_imp_table else None),
                (0, row_index * REALM_HEIGHT))
        prev_imp_table = one_table
        yield one_map


if __name__ == '__main__':
    print('Writing {0}...'.format(MAP_FILENAME))
    map_filenames = [
        # ('T1', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_1_NCR.html'),
        # ('T2', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_2_NCR.html'),
        # ('T3', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_3_NCR.html'),
        # ('4', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_4.html'),
        # ('T4', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_4_NCR.html'),
        # ('5', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_5.html'),
        # ('T5', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_5_NCR.html'),
        # ('6', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_6.html'),
        # ('T6', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_6_NCR.html'),
        # ('7', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_7.html'),
        # ('T7', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_7_NCR.html'),
        # ('8', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_8.html'),
        # ('T8', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_8_NCR.html'),
        # ('9', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_9.html'),
        # ('T9', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_9_NCR.html'),
        #('10', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_10.html'),
        #('T10', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_10_NCR.html'),
        #('11', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_11.html'),
        #('T11', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_11_NCR.html'),
        #('12', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_12.html'),
        #('T12', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_12_NCR.html'),
        #('13', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_13.html'),
        #('T13', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_13_NCR.html'),
        #('14', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_14.html'),
        ('T14', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_14_NCR.html'),
        ('15', False, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_impulse_map_Turn_15.html'),
        ('T15', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_15_NCR.html'),
    ]
    map_images = []
    last_image = None
    for label, is_turn_map, map_filename in map_filenames:
        for map_image in get_adj_lists(label, is_turn_map, map_filename):
            map_images.append(numpy.array(map_image))
            last_image = map_image
    if DO_RECON:
        last_image.save('{0}-recon.gif'.format(MAP_FILENAME), format='gif')
        print('Recon GIF done.')
    imageio.mimsave('{0}.gif'.format(MAP_FILENAME), map_images, duration=MAP_CHANGE_RATE_PER_SECOND)
    print('Animated GIF done.')
    writer = imageio.get_writer('{0}.mp4'.format(MAP_FILENAME), fps=1)
    for map_image in map_images:
        writer.append_data(map_image)
    writer.close()
    print('MP4 done.')
        
