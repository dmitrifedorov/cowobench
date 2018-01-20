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

REALM_WIDTH = 100
REALM_HEIGHT = 100
REALM_BORDER = 1
REALMS_MAX_X = 32 
REALMS_MAX_Y = REALMS_MAX_X


from html.parser import HTMLParser
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio


class TurnResultHTMLParser(HTMLParser):

    tables = []
    table = []
    row = []
    is_table_data = False
    colour = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.is_table_data = True
        if tag == 'td':
            for attr, value in attrs:
                if attr == 'bgcolor':
                    self.colour = value
                    break

    def handle_endtag(self, tag):
        if tag == 'table':
            self.tables.append(self.table)
            self.table = []
            self.is_table_data = False
        if tag == 'tr':
            self.table.append(self.row)
            self.row = []

    def handle_data(self, data):
        if self.is_table_data:
            value = data.strip()
            if len(value) > 0:
                self.row.append((value, self.colour))


def html_colour_to_rgba(html_colour: str) -> ():
    html_colour = html_colour.strip()
    if html_colour[0] == '#':
        html_colour = html_colour[1:]
    r, g, b = html_colour[:2], html_colour[2:4], html_colour[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    return (r, g, b, 0)


def build_turn_map(turn_result: str) -> Image:
    parser = TurnResultHTMLParser()
    parser.feed(open(turn_result).read())
    turn_table = parser.tables[-1]

    cell_font = ImageFont.truetype('arial.ttf', 30)

    result = Image.new('RGBA', (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT * REALMS_MAX_Y), (255, 255, 255, 0))
    for y, row in enumerate(turn_table):
        row_image_size = (REALM_WIDTH * REALMS_MAX_X, REALM_HEIGHT)
        row_image = Image.new('RGBA', row_image_size, (255, 255, 255, 0))
        for x, cell in enumerate(row):
            cell_image = Image.new('RGBA', (REALM_WIDTH - REALM_BORDER * 2, REALM_HEIGHT - REALM_BORDER * 2), html_colour_to_rgba(cell[1]))
            draw_context = ImageDraw.Draw(cell_image)
            realm_points = cell[0].split(' ')[0]
            draw_context.text((15, 10), realm_points, font=cell_font, fill=(0, 0, 0, 255))
            # if len(cell[0].split(' ')) > 1:
            #    realm_occupant = ' '.join(cell[0].split(' ')[1:])
            #    draw_context.text((15, 40), realm_occupant, font=cell_font, fill=(0, 0, 0, 255))

            cell_image = ImageOps.expand(cell_image, REALM_BORDER)
            row_image.paste(cell_image, (x * REALM_WIDTH, 0))
        result.paste(row_image, (0, y * REALM_HEIGHT))
    return result
    
        
if __name__ == '__main__':
    map_filenames = [
        '/Users/Dmitri Fedorov/Google Drive/cow2/CoW_Results_Game_2_Turn_1_NCR.html',
        '/Users/Dmitri Fedorov/Google Drive/cow2/CoW_Results_Game_2_Turn_2_NCR.html',
        '/Users/Dmitri Fedorov/Google Drive/cow2/CoW_Results_Game_2_Turn_3_NCR.html',
        '/Users/Dmitri Fedorov/Google Drive/cow2/CoW_Results_Game_2_Turn_4_NCR.html',
        '/Users/Dmitri Fedorov/Google Drive/cow2/CoW_Results_Game_2_Turn_5_NCR.html',
    ]
    turn_maps = []
    for map_filename in map_filenames:
        image = build_turn_map(map_filename)
        image.save('./image.gif')
        turn_maps.append(imageio.imread('./image.gif'))
    imageio.mimsave('turnsmap.gif', turn_maps, duration=2)
    # turn_map.show()
    
