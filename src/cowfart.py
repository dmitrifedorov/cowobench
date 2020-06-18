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
@copyright: 2020 by EKDF Consulting and Dmitri Fedorov
@file: cowfart.py
'''


RESULT_DIRECTORY = "C:\\Users\\dfedorov\\!nosync\\!cow"

REALM_WIDTH = 50
REALM_HEIGHT = 50
REALM_BORDER = 1
REALMS_MAX_X = 38
REALMS_MAX_Y = 38
PLAN_LINE_WIDTH = 10
TOTAL_IMPULSES = 10

EMPTY_IMAGE_RGBA = (255, 255, 255)
RGBA = 'RGB'
HOME_COLOUR = '#666600'
HOME_X = 31
HOME_Y = 7

do_recon = True
known_units = []
known_digs = []
cell_colours = []

from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
from string import ascii_uppercase
import imageio
import numpy
import os
import datetime
import itertools
from collections import namedtuple

Move = namedtuple('Move', 'unit, limbo, impulses, at')
XY_Move = namedtuple('XY_Move', 'unit, xy_moves')
Upgrade = namedtuple('Upgrade', 'unit, type, cost')
TurnOrders = namedtuple('TurnOrders', 'turn, faction, commands')
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
    global cell_colours
    row_image = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT), EMPTY_IMAGE_RGBA)
    for cell_index, cell_data in enumerate(row_data):
        cell_content, cell_colour = cell_data
        cell_colour = html_colour_to_rgba(cell_colour)
        cell_colours.append(cell_colour)
        cell_image = Image.new(RGBA,
                               (REALM_WIDTH - REALM_BORDER * 2, REALM_HEIGHT - REALM_BORDER * 2),
                               cell_colour)
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


def get_impulses(commands: str):
    result = []
    try:
        command_iterator = commands.__iter__()
        for command in command_iterator:
            if command in ['N', 'S', 'W', 'E', '.', 'H', 'D', 'U', 'C']:
                result.append(command)
            elif command in ['T']:
                teleport_command = []
                while True:
                    teleport_command.append(command_iterator.__next__())
                    if teleport_command[-1] == ')':
                        break
                result.append(''.join(teleport_command))
    except Exception as ex:
        print(ex)
    return result


def get_upgrades(orders_dir: str, orders_filename) -> TurnOrders:
    with open(os.path.join(orders_dir, orders_filename), 'r') as orders_file:
        commands = []
        for line in orders_file:
            if not line.lstrip().startswith('#') and len(line.strip()) > 0:
                upgrade_tokens = list(filter(None, line.split(' ')))
                if upgrade_tokens[0] in ['UPG', 'upg']:
                    # expect UPG MD_NCR_7 SK # cost is 16 rp...
                    upgrade_cost = int(upgrade_tokens[6])
                    commands.append(Upgrade(upgrade_tokens[1], upgrade_tokens[2], upgrade_cost))
        return TurnOrders(None, 'NCR', commands)


def get_moves(orders_dir: str, orders_filename) -> TurnOrders:
    with open(os.path.join(orders_dir, orders_filename), 'r') as orders_file:
        commands = []
        for line in orders_file:
            if not line.lstrip().startswith('#') and len(line.strip()) > 0:
                order_tokens = list(filter(None, line.strip().split(' ')))
                if order_tokens[0] in ['MOV', 'mov']:
                    # expect MOV MD_NCR_3 ESE.......  # Unit is at x35y11, has
                    unit_at = order_tokens[7].strip(',')
                    if unit_at in ['Limbo']:
                        unit_at_x = HOME_X
                        unit_at_y = HOME_Y
                    else:
                        unit_at_x = unit_at.split('y')[0].strip('x')
                        unit_at_y = unit_at.split('y')[1]
                    commands.append(Move(order_tokens[1],
                                         unit_at in ['Limbo'],
                                         get_impulses(order_tokens[2]),
                                         XY(int(unit_at_x), int(unit_at_y))))
        return TurnOrders(None, 'NCR', commands)


def unit_moved(impulses):
    count = 0
    for i in range(0, TOTAL_IMPULSES):
        if impulses[i] not in ['.']:
            count += 1
    return count


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

def read_file(turnmap_filename):
    result = open(turnmap_filename).read()
    result = result.replace('<b>', ' ').replace('</b>', ' ').replace('<i>', ' ').replace('</i>', ' ')
    return result


def get_maps(map_label: str, is_turn_map: bool, turnmap_filename: str) -> Image:
    """builds one map"""
    prev_imp_table = None
    print('Processing file {0}...'.format(turnmap_filename))
    for table_index, one_table in enumerate(get_table(read_file(turnmap_filename), is_turn_map)):
        print('Processing table {0}...'.format(table_index))
        one_map = Image.new(RGBA, (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT * REALMS_MAX_Y), EMPTY_IMAGE_RGBA)
        for row_index, row_data in enumerate(one_table):
            one_map.paste(get_one_row_image(table_index,
                                            '{0}-{1}'.format(map_label, table_index),
                                            row_index, row_data,
                                            prev_imp_table[row_index] if prev_imp_table else None),
                          (0, row_index * REALM_HEIGHT))
        prev_imp_table = one_table
        yield one_map


curr_rgb_int = (None, None, None)
import random
random.seed()

def get_next_colour():
    global curr_rgb_int
    global cell_colours
    while True:
        curr_rgb_int = tuple([random.randint(1, 250) for _ in curr_rgb_int])
        if curr_rgb_int in cell_colours:
            continue
        else:
            break
    return "#" + "".join(['{0:02x}'.format(i) for i in curr_rgb_int])


def get_unit_moves(unit_moves):
    result = []
    prev_move = None
    for unit_move in unit_moves:
        unit_moved = not (prev_move == unit_move) if prev_move else True
        if unit_moved:
            result.append(((unit_move.x+0.5)*REALM_WIDTH, (unit_move.y+0.5)*REALM_HEIGHT))
        prev_move = unit_move
    return result


def draw_plan(xy_moves, last_image: Image) -> Image:
    draw_context = ImageDraw.Draw(last_image)
    for unit_name, unit_moves in xy_moves.items():
        draw_context.line(get_unit_moves(unit_moves),
                          fill=get_next_colour(),
                          width=PLAN_LINE_WIDTH)
    return last_image

teleport_names = iter(['({0})'.format(port_letter) for port_letter in ascii_uppercase])
teleport_xs = [x for x in range(7, 43, 12)]
teleport_xs.extend([x for x in range(1, 43, 12)])
#teleport_xs = iter(teleport_ys)
#teleport_ys = iter([y for y in range(1, 43, 6)])
teleport_ys = [y for y in range(1, 43, 6)]

#while True:
#    name = next(teleport_names, None)
#    if name:
#        #x = next(teleport_xs, None)
#        #y = next(teleport_ys, None)
#        for x in teleport_xs:
#            for y in teleport_ys:
#                print(name, x, y)
#        #else:
#        #    break
#    else:
#        break;

moves_map = { 
    '.': lambda curr: XY(curr.x, curr.y),
    'H': lambda curr: XY(curr.x, curr.y),
    'N': lambda curr: XY(curr.x, curr.y-1),
    'S': lambda curr: XY(curr.x, curr.y+1),
    'W': lambda curr: XY(curr.x-1, curr.y),
    'E': lambda curr: XY(curr.x+1, curr.y),
#    }    

    '(A)': lambda curr: XY(7, 1),
    '(B)': lambda curr: XY(19, 1),
    '(C)': lambda curr: XY(31, 1),

    '(D)': lambda curr: XY(1, 7),
    '(E)': lambda curr: XY(13, 7),
    '(F)': lambda curr: XY(25, 7),
    '(G)': lambda curr: XY(37, 7),

    '(H)': lambda curr: XY(7, 13),
    '(I)': lambda curr: XY(19, 13),
    '(J)': lambda curr: XY(31, 13),

    '(K)': lambda curr: XY(1, 19),
    '(L)': lambda curr: XY(13, 19),
    '(M)': lambda curr: XY(25, 19),
    '(N)': lambda curr: XY(37, 19),

    '(O)': lambda curr: XY(7, 25),
    '(P)': lambda curr: XY(19, 25),
    '(Q)': lambda curr: XY(31, 25),

    '(R)': lambda curr: XY(1, 31),
    '(S)': lambda curr: XY(13, 31),
    '(T)': lambda curr: XY(25, 31),
    '(U)': lambda curr: XY(27, 31),

    '(V)': lambda curr: XY(7, 37),
    '(W)': lambda curr: XY(19, 37),
    '(X)': lambda curr: XY(31, 37),
    }

def get_xy_moves(moves):
    # transform into XY movements
    result = {}
    for unit_moves in moves:
        # 'unit, limbo, impulses, at'
        if unit_moves.limbo and (unit_moves.impulses == 'H.........'):
            continue
        curr = unit_moves.at
        unit_xy_moves = [curr]
        for i in unit_moves.impulses:
            curr = moves_map[i](curr)
            unit_xy_moves.append(curr)
        if len(unit_xy_moves) == TOTAL_IMPULSES + 1:
            result[unit_moves.unit] = unit_xy_moves
        else:
            raise Exception('Unexpected unit moves: {0}'.format(unit_moves))
    return result

def unit_move_const(unit_moves):
    result = 0
    result += sum(1 for i, _ in enumerate(unit_moves) if not unit_moves[i] == unit_moves[i-1])
    return result

def main(orders_dir, orders_filename):
    xy_moves = get_xy_moves(get_moves(orders_dir, orders_filename).commands)

    move_cost = sum(unit_move_const(unit_moves) for _, unit_moves in xy_moves.items())
    print('Move cost: {0}'.format(move_cost))

    upgrade_cost = sum(x.cost for x in get_upgrades(orders_dir, orders_filename).commands)
    print('Upgrade cost: {0}'.format(upgrade_cost))

    last_result_file = sorted([x for x in get_result_files(orders_dir)], key=lambda x: x[0])[-1]
    last_impulse_file = sorted([x for x in get_impulse_files(orders_dir)], key=lambda x: x[0])[-1]

    for last_file in [last_result_file, last_impulse_file]:
        last_image = [x for x in get_maps(*last_file)][-1]

    plan_image = draw_plan(xy_moves, last_image)
    plan_image.save('turn{0}-plan.png'.format(last_impulse_file[0] + 1), format='png')

    
if __name__ == '__main__':
    main(RESULT_DIRECTORY, 'CoW_Orders_Game_g7_Turn_8_NCR.txt')
