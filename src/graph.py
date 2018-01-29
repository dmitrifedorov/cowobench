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
MAP_FILENAME = 'turn61map'

REALM_WIDTH = 100
REALM_HEIGHT = 100
REALM_BORDER = 1
REALMS_MAX_X = 32
REALMS_MAX_Y = REALMS_MAX_X
RGBA = 'RGBA'
EMPTY_IMAGE_RGBA = (255, 255, 255, 0)

from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
from collections import namedtuple
import queue

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
               is_zero_cell: bool=False, zero_call_label: str=None) -> ImageDraw.Draw:
    """Write text on one cell"""
    CELL_POINTS_FONT_TYPE = 'arial.ttf'
    CELL_POINTS_FONT_SIZE = 35
    CELL_POINTS_FONT = ImageFont.truetype(CELL_POINTS_FONT_TYPE, CELL_POINTS_FONT_SIZE)
    CELL_POINTS_POSITION = (15, 15)
    ZERO_CELL_FONT_TYPE = 'arialbd.ttf'
    ZERO_CELL_FONT_SIZE = 60
    ZERO_CELL_FONT = ImageFont.truetype(ZERO_CELL_FONT_TYPE, ZERO_CELL_FONT_SIZE)
    ZERO_CELL_POSITION = (3, 3)
    TRANSPARENT_FILL = (0, 0, 0, 255)

    draw_context = ImageDraw.Draw(cell_image)
    if is_zero_cell:
        draw_context.text(ZERO_CELL_POSITION, zero_call_label, font=ZERO_CELL_FONT, fill=TRANSPARENT_FILL)
    else:
        realm_points = cell_content.split(' ')[0]
        draw_context.text(CELL_POINTS_POSITION, realm_points, font=CELL_POINTS_FONT, fill=TRANSPARENT_FILL)


def get_one_row_image(zero_call_label: str, row_index: int, row_data: []) -> Image:
    """Build one row image from the row data"""
    row_image = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT), EMPTY_IMAGE_RGBA)
    for cell_index, cell_data in enumerate(row_data):
        cell_content, cell_colour = cell_data
        cell_image = Image.new(RGBA, (REALM_WIDTH - REALM_BORDER * 2, REALM_HEIGHT - REALM_BORDER * 2),
                               html_colour_to_rgba(cell_colour))
        if row_index == 0 and cell_index == 0:
            write_on_cell(cell_image, cell_content, True, zero_call_label)
        else:
            write_on_cell(cell_image, cell_content)
            
        if len(cell_content.split(' ')) > 1:
            cell_symbol = cell_content.split(' ')[1].strip()
            if cell_symbol in ['*']:
                cell_icon = Image.open('crossed-swords.png').resize((70, 70))
                cell_image.paste(cell_icon, (15, 15), cell_icon)
            if cell_symbol in ['+']:
                cell_icon = Image.open('dagger-knife.png').resize((70, 70))
                cell_image.paste(cell_icon, (15, 15), cell_icon)
            
        cell_image = ImageOps.expand(cell_image, REALM_BORDER)
        row_image.paste(cell_image, (cell_index * REALM_WIDTH, 0))
    return row_image


XY = namedtuple('XY', 'x, y')
AdjList = namedtuple('AdjList', 'w, list, vr')

# (x, y): ( w, list[(x, y)], (c, d, pi) )

VR = namedtuple('VR', 'c, d, pi')
WHITE = 'WHITE'
GREY = 'GREY'
BLACK = 'BLACK'
DEFAULT_WHITE = VR(WHITE, None, None)


def get_lists(_: str, is_turn_map: bool, result_filename: str) -> Image:
    """builds one map"""
    for _, one_table in enumerate(get_table(open(result_filename).read(), is_turn_map)):
        vertex_weights, MAX_ROW_INDEX, MAX_COLUMN_INDEX = get_vertex_weights(one_table)
        adj_lists = {}
        for x, y in vertex_weights:
            value = int(vertex_weights[x, y].split(' ')[0])
            adj_list = []
            if value > 0:
                adj_list = get_adj_list(vertex_weights, x - 1, y, x - 1, MAX_COLUMN_INDEX, adj_list)
                adj_list = get_adj_list(vertex_weights, x + 1, y, x + 1, MAX_COLUMN_INDEX, adj_list)
                adj_list = get_adj_list(vertex_weights, x, y - 1, y - 1, MAX_ROW_INDEX, adj_list)
                adj_list = get_adj_list(vertex_weights, x, y + 1, y + 1, MAX_ROW_INDEX, adj_list)
            adj_lists[XY(x, y)] = AdjList(value, adj_list, DEFAULT_WHITE)
        yield adj_lists

def get_adj_list(vertex_weights, x, y, i, max_index, adj_list):
    if i > 0 and i < max_index:
        value = int(vertex_weights[x, y].split(' ')[0])
        if value > 0:
            adj_list.append(XY(x, y))
    return adj_list

def get_vertex_weights(one_table: []) -> {}:
    vertex_weights = {}
    MAX_ROW_INDEX = 0
    MAX_COLUMN_INDEX = 0
    for row_index, row_data in enumerate(one_table):
        MAX_ROW_INDEX = row_index
        for column_index, cell_data in enumerate(row_data):
            MAX_COLUMN_INDEX = column_index
            if row_index > 0 and column_index > 0:
                vertex_weights[(row_index, column_index)] = cell_data[0]
    return vertex_weights, MAX_ROW_INDEX, MAX_COLUMN_INDEX 


def colour_vertex(adj_lists: {}, xy: XY, c: str, d: int=0, p: XY=None):
    for x, y in adj_lists:
        if XY(x, y) == xy:
            curr_adj_list = adj_lists[xy]
            adj_lists[XY(x, y)] = AdjList(curr_adj_list.w, curr_adj_list.list, VR(c, d, p))
            break 
    return adj_lists


def bfs(start: XY, adj_lists: {}) -> {}:
    adj_lists = colour_vertex(adj_lists, start, GREY)
    vertex_queue = queue.Queue()
    vertex_queue.put(start)
    while not vertex_queue.empty():
        u = vertex_queue.get()
        for v in adj_lists[u].list:
            if adj_lists[v].vr.c == WHITE:
                adj_lists = colour_vertex(adj_lists, v, GREY, adj_lists[u].vr.d + 1, u)
                vertex_queue.put(v)
        adj_lists = colour_vertex(adj_lists, u, BLACK, adj_lists[u].vr.d, adj_lists[u].vr.pi)
    return adj_lists

if __name__ == '__main__':
    map_filenames = [
        ('T6', True, '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_6_NCR.html'),
    ]
    for label, is_turn_map, map_filename in map_filenames:
        for adj_lists in get_lists(label, is_turn_map, map_filename):
            result = bfs(XY(2, 20), adj_lists)
            print(result)

            #print(result)
            # for item in result:
            #    print(item, result[item])
