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

LOWEST_POINTS = 5


def get_adj_lists(turnmap_filename: str) -> {}:
    for one_table in get_table(open(turnmap_filename).read(), True):
        return { k: v for k, v in get_vertex_adj_lists(get_all_vertices(one_table)) }


def get_vertex_adj_lists(all_vertices: {}, defaul_colour: VR=DEFAULT_WHITE) -> ():
    for curr_vertex in all_vertices.keys():
        if not is_wall(all_vertices, curr_vertex):
            adj_list = [x for x in get_adj_cell(all_vertices, curr_vertex)]
            yield curr_vertex, AdjList(get_vertex_value(all_vertices, curr_vertex), adj_list, defaul_colour)


def get_vertex_value(vertices: {}, xy: XY) -> int:
    return int(vertices[xy].split(' ')[0])


def is_wall(vertices: {}, xy: XY) -> bool:
    return get_vertex_value(vertices, xy) == WALL_VALUE


def is_on_map(xy: XY) -> bool:
    return (xy.x > REALMS_MIN_X and xy.x < REALMS_MAX_X) and (xy.y > REALMS_MIN_X and xy.y < REALMS_MAX_Y) 


def get_adj_cell(vertices: {}, vertex: XY) -> ():
    for xc in [vertex.x - 1, vertex.x + 1]:
        step = XY(xc, vertex.y)
        if is_on_map(step) and not is_wall(vertices, step):
            yield step
    for yc in [vertex.y - 1, vertex.y + 1]:
        step = XY(vertex.x, yc)
        if is_on_map(step) and not is_wall(vertices, step):
            yield step


def get_all_vertices(one_table: []) -> {}:
    return { k: v for k, v in get_vertex(one_table) }


def get_vertex(one_table: []) -> ():
    for row_index, row_data in get_row(one_table):
        for column_index, cell_data in get_column(row_data):
            yield XY(row_index, column_index), cell_data[0]


def get_row(one_table: []) -> {}:
    for row_index, row_data in enumerate(one_table):
        if row_index > REALMS_MIN_Y:
            yield row_index, row_data

            
def get_column(row_data: []) -> {}:
    for column_index, cell_data in enumerate(row_data):
        if column_index > REALMS_MIN_X:
            yield column_index, cell_data[0]


def colour_vertex(vertex_adj_lists: {}, xy: XY, c: str, d: int=0, p: XY=None):
    curr_adj_list = vertex_adj_lists[xy]
    vertex_adj_lists[xy] = AdjList(curr_adj_list.w, curr_adj_list.list, VR(c, d, p))


def bfs(start: XY, vertex_adj_lists: {}) -> {}:
    colour_vertex(vertex_adj_lists, start, GREY)
    vertex_queue = queue.Queue()
    vertex_queue.put(start)
    while not vertex_queue.empty():
        u = vertex_queue.get()
        for v in vertex_adj_lists[u].list:
            if vertex_adj_lists[v].vr.c == WHITE:
                colour_vertex(vertex_adj_lists, v, GREY, vertex_adj_lists[u].vr.d + 1, u)
                vertex_queue.put(v)
        colour_vertex(vertex_adj_lists, u, BLACK, vertex_adj_lists[u].vr.d, vertex_adj_lists[u].vr.pi)
    return vertex_adj_lists


def is_owner_me(xy: XY) -> bool:
    if xy.y < 16: return False
    if xy.y > 22: return False
    if xy.x > 12: return False
    if xy.y == 16:
        if xy.x < 5: return False
    if xy.y == 22:
        if xy.x < 8: return False
        if xy.x > 9: return False
    return True


def get_turn_adj_lists(vertex_adj_lists: {}, start: XY) -> {}:
    turn_adj_lists = bfs(start, copy.deepcopy(vertex_adj_lists))
    return { k: v for k, v in turn_adj_lists.items() if (v.vr.d <= 3) and is_owner_me(k) }


def get_turn_cmd(distance: int) -> str:
    if distance == 3:
        yield 'SSS'
    elif distance == 2:
        for cmd in ['DSS', 'SDS', 'SSD']:
            yield cmd
    elif distance == 1:
        for cmd in ['SDD', 'DSD', 'DDS']:
            yield cmd
    elif distance == 0:
        yield 'DDD'
    

def get_points(from_xy: XY, to_xy: XY, cmd: str, dig_map: {}) -> int:
    if cmd in ['DDD']:
        yield dig(from_xy, dig_map) + dig(from_xy, dig_map) + dig(from_xy, dig_map)
    elif cmd in ['SDD']:
        yield dig(to_xy, dig_map) + dig(to_xy, dig_map)
    elif cmd in ['DSD']:
        yield dig(from_xy, dig_map) + dig(to_xy, dig_map)
    elif cmd in ['DDS']:
        yield dig(from_xy, dig_map) + dig(from_xy, dig_map)
    elif cmd in ['DSS']:
        yield dig(from_xy, dig_map)
    elif cmd in ['SDS']:
        if from_xy.x == to_xy.x:
            through_xy = XY(from_xy.x, (from_xy.y + to_xy.y) / 2)
            yield dig(through_xy, dig_map)
        elif from_xy.y == to_xy.y:
            through_xy = XY((from_xy.x + to_xy.x) / 2, from_xy.y)
            yield dig(through_xy, dig_map)
        else:
            for through_xy in [XY(from_xy.x, to_xy.y), XY(to_xy.x, from_xy.y)]:
                if is_owner_me(through_xy) and (through_xy in dig_map.keys()):
                    yield dig(through_xy, dig_map)
    elif cmd in ['SSD']:
        yield dig(to_xy, dig_map)
    elif cmd in ['SSS']:
        yield 0


def dig(xy: XY, dig_map: {}) -> int:
    points = dig_map[xy].w
    if points == 0: points = 1
    curr_adj_list = dig_map[xy]
    dig_map[xy] = AdjList(points - 1, curr_adj_list.list, curr_adj_list.vr) 
    return points


Path = namedtuple('Path', 'points, start, finish, cmd, dig_map, master_map')


def process_turn(prev_turn_paths: {}, master_map: {}):
    next_turn_paths = []
    
    for prev_turn_path in prev_turn_paths:
        for prev_turn_xy in prev_turn_path.dig_map:
            prev_weight = prev_turn_path.dig_map[prev_turn_xy].w
            curr_adj_list = master_map[prev_turn_xy]
            master_map[prev_turn_xy] = AdjList(prev_weight, curr_adj_list.list, curr_adj_list.vr)
        
    for prev_turn_path in prev_turn_paths:
        from_vertex = prev_turn_path.finish
        curr_turn_adj_lists = get_turn_adj_lists(master_map, from_vertex)
        for to_vertex in curr_turn_adj_lists:
            if not to_vertex == HOME_VERTEX:
                for cmd in get_turn_cmd(curr_turn_adj_lists[to_vertex].vr.d):
                    dig_map = copy.deepcopy(curr_turn_adj_lists)
                    for points in get_points(from_vertex, to_vertex, cmd, dig_map):
                        for xy in dig_map:
                            curr_adj_list = master_map[xy]
                            master_map[xy] = AdjList(dig_map[xy].w, curr_adj_list.list, curr_adj_list.vr)
                        if points > LOWEST_POINTS:
                            next_turn_paths.append(Path(points, from_vertex, to_vertex, cmd, copy.deepcopy(dig_map), copy.deepcopy(master_map)))
    return next_turn_paths


def get_first_turn(master_map: {}):
    from_vertex = HOME_VERTEX
    first_turn_paths = []
    turn_adj_lists = get_turn_adj_lists(master_map, from_vertex)
    for to_vertex in turn_adj_lists:
        if not to_vertex == HOME_VERTEX:
            for cmd in get_turn_cmd(turn_adj_lists[to_vertex].vr.d):
                dig_map = copy.deepcopy(turn_adj_lists)
                for points in get_points(from_vertex, to_vertex, cmd, dig_map):
                    for xy in dig_map:
                        curr_adj_list = master_map[xy]
                        master_map[xy] = AdjList(dig_map[xy].w, curr_adj_list.list, curr_adj_list.vr)
                    if points > LOWEST_POINTS:
                        first_turn_paths.append(Path(points, from_vertex, to_vertex, cmd, copy.deepcopy(dig_map), copy.deepcopy(master_map)))
    return first_turn_paths


if __name__ == '__main__':
    map_filenames = [
        '/Users/Dmitri Fedorov/Google Drive/cow2/turnmaps/CoW_Results_Game_2_Turn_6_NCR.html',
    ]
    for map_filename in map_filenames:
        vertex_adj_lists = get_adj_lists(map_filename)

        first_turn_paths = get_first_turn(vertex_adj_lists)
        print(len(first_turn_paths))
        second_turn_paths = process_turn(first_turn_paths, vertex_adj_lists)
        print(len(second_turn_paths))
        third_turn_paths = process_turn(second_turn_paths, vertex_adj_lists)
        print(len(third_turn_paths))
        
        most_points = 0
        path = None
        for first_turn_path in first_turn_paths:
            for second_turn_path in second_turn_paths:
                for third_turn_path in third_turn_paths:
                    if first_turn_path.finish == second_turn_path.start and second_turn_path.finish == third_turn_path.start:
                        total = first_turn_path.points + second_turn_path.points + third_turn_path.points
                        if total > most_points:
                            most_points = total
                            path = (first_turn_path, second_turn_path, third_turn_path)
        
        print(most_points, path[0].start, path[0].finish, path[0].cmd, path[1].start, path[1].finish, path[1].cmd, path[2].start, path[2].finish, path[2].cmd)

        #print(path[0].master_map)
        #print(path[1].master_map)
        #print(path[2].master_map)
