# LOOTMATH - BORDERLANDS

import pandas as pd
import xml.etree.ElementTree as ET

def parse_gun_parts():
    # first, we parse the XML file into an ElementTree for QOL
    tree = ET.parse('xml/WeaponParts.xml')

    gun_parts = {} # dict to store essential part info

    # iterates through ET until it finds "part" elements
    for part in tree.findall('.//Part'):

        id = part.attrib['id']
        name = part.find('Name').text

        gun_parts[name] = {}
        gun_parts[name]['id'] = id

        # then stores all essential data of the part in the dict
        for attr in part:
            # the part name is already the part's dict key, so we skip it
            if attr.tag in ['Name', 'Part']:
                continue

            # there are 4 part attributes that have problematic structures:
            #   1. AttrMod: contains all gun stat modifiers
            #   2. CardMod: contains all gun CARD stat modifiers
            #   3. TechAbility: describes elemental damage statistics,
            #         also annoyingly has one version per elem stage (1-4)
            #   4. CardText: used to store data for flavor text on unique weapons
            # to solve this, we will flatten these subattributes like so:
            elif attr.tag in ['AttrMod']:
                for subattr in attr:
                    keyname = "%s_%s_%s" % (attr.tag, subattr.tag, subattr.attrib['modType'])
                    gun_parts[name][keyname] = subattr.text

            elif attr.tag in ['TechAbility']:
                elem_grade = attr.attrib['grade']
                for subattr in attr:
                    keyname = "Tech%s_%s" % (elem_grade, subattr.tag)
                    gun_parts[name][keyname] = subattr.text

            elif attr.tag in ['CardMod', 'CardText']:
                for subattr in attr:
                    keyname = "%s_%s" % (attr.tag, subattr.tag)
                    gun_parts[name][keyname] = subattr.text

            # for everything else, we simply store the tag and its text
            else:
                gun_parts[name][attr.tag] = attr.text

    guns_df = pd.DataFrame.from_dict(gun_parts, 'index')
    guns_df2 = guns_df[~guns_df['PartType'].isin(['Gear Type', 'Item Grade', 'Manufacturer', 'Bullet'])]
    guns_df2.to_csv('gun_parts.csv')


if __name__ == "__main__":
    parse_gun_parts()