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

REALMS_MIN_X = 0
REALMS_MAX_X = 32

REALMS_MIN_Y = REALMS_MIN_X
REALMS_MAX_Y = REALMS_MAX_X

WALL_VALUE = 0

from html.parser import HTMLParser
from collections import namedtuple
import queue, copy

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


XY = namedtuple('XY', 'x, y')
AdjList = namedtuple('AdjList', 'w, list, vr')

# (x, y): ( w, list[(x, y)], (c, d, pi) )

VR = namedtuple('VR', 'c, d, pi')
WHITE = 'WHITE'
GREY = 'GREY'
BLACK = 'BLACK'
DEFAULT_WHITE = VR(WHITE, None, None)

HOME_VERTEX = XY(2, 20)


def get_adj_lists(turnmap_filename: str) -> {}:
    for one_table in get_table(open(turnmap_filename).read(), True):
        all_vertices = get_all_vertices(one_table)
        vertex_adj_lists = {}
        for curr_vertix in all_vertices.keys():
            if not is_wall(all_vertices, curr_vertix):
                adj_list = [step for step in get_adj_cell(all_vertices, curr_vertix)]
                vertex_adj_lists[curr_vertix] = AdjList(get_value(all_vertices, curr_vertix), adj_list, DEFAULT_WHITE)
        return vertex_adj_lists


def get_value(vertices: {}, xy: XY) -> int:
    return int(vertices[xy].split(' ')[0])


def is_wall(vertices: {}, xy: XY) -> bool:
    return get_value(vertices, xy) == WALL_VALUE


def is_on_map(xy: XY) -> bool:
    return (xy.x > REALMS_MIN_X and xy.x < REALMS_MAX_X) and (xy.y > REALMS_MIN_X and xy.y < REALMS_MAX_Y) 


def get_adj_cell(vertices: {}, vertix: XY) -> ():
    for xc in [vertix.x - 1, vertix.x + 1]:
        step = XY(xc, vertix.y)
        if is_on_map(step) and not is_wall(vertices, step):
            yield step
    for yc in [vertix.y - 1, vertix.y + 1]:
        step = XY(vertix.x, yc)
        if is_on_map(step) and not is_wall(vertices, step):
            yield step


def get_all_vertices(one_table: []) -> {}:
    vertices = {}
    for row_index, row_data in enumerate(one_table):
        if row_index > REALMS_MIN_Y:
            for column_index, cell_data in enumerate(row_data):
                if column_index > REALMS_MIN_X:
                    vertices[XY(row_index, column_index)] = cell_data[0]
    return vertices


def colour_vertex(vertex_adj_lists: {}, xy: XY, c: str, d: int=0, p: XY=None):
    for x, y in vertex_adj_lists:
        if XY(x, y) == xy:
            curr_adj_list = vertex_adj_lists[xy]
            vertex_adj_lists[XY(x, y)] = AdjList(curr_adj_list.w, curr_adj_list.list, VR(c, d, p))
            break 
    return vertex_adj_lists


def bfs(start: XY, vertex_adj_lists: {}) -> {}:
    vertex_adj_lists = colour_vertex(vertex_adj_lists, start, GREY)
    vertex_queue = queue.Queue()
    vertex_queue.put(start)
    while not vertex_queue.empty():
        u = vertex_queue.get()
        for v in vertex_adj_lists[u].list:
            if vertex_adj_lists[v].vr.c == WHITE:
                vertex_adj_lists = colour_vertex(vertex_adj_lists, v, GREY, vertex_adj_lists[u].vr.d + 1, u)
                vertex_queue.put(v)
        vertex_adj_lists = colour_vertex(vertex_adj_lists, u, BLACK, vertex_adj_lists[u].vr.d, vertex_adj_lists[u].vr.pi)
    return vertex_adj_lists


def get_turn_steps(vertex_adj_lists: {}, start: XY):
    turn_steps = bfs(start, copy.deepcopy(vertex_adj_lists))
    return { k: v for k, v in turn_steps.items() if v.vr.d <= 3 }

if __name__ == '__main__':
    map_filenames = [
        '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_6_NCR.html',
    ]
    for map_filename in map_filenames:
        vertex_adj_lists = get_adj_lists(map_filename)
        for x, y in get_turn_steps(vertex_adj_lists, XY(2, 20)):
            print(vertex_adj_lists[x, y])
