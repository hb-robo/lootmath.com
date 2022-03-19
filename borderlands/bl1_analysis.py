# LOOTMATH - BORDERLANDS

import pandas as pd
import xml.etree.ElementTree as ET

def parse_xml(path):
    # first, we parse the XML file into an ElementTree for QOL
    tree = ET.parse(path)
    parts = {} # dict to store essential part info

    # iterates through ET until it finds "part" elements
    for part in tree.findall('.//Part'):

        id = part.attrib['id']
        name = part.find('Name').text

        parts[name] = {}
        parts[name]['id'] = id

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
                    parts[name][keyname] = subattr.text

            elif attr.tag in ['TechAbility']:
                elem_grade = attr.attrib['grade']
                for subattr in attr:
                    keyname = "Tech%s_%s" % (elem_grade, subattr.tag)
                    parts[name][keyname] = subattr.text

            elif attr.tag in ['CardMod', 'CardText']:
                for subattr in attr:
                    keyname = "%s_%s" % (attr.tag, subattr.tag)
                    parts[name][keyname] = subattr.text

            # for everything else, we simply store the tag and its text
            else:
                parts[name][attr.tag] = attr.text

    df = pd.DataFrame.from_dict(parts, 'index')
    df2 = df[~df['PartType'].isin(['Gear Type', 'Item Grade', 'Manufacturer', 'Bullet'])]
    filename = path.replace('.xml','').replace('xml/', 'csv/')
    filename += ".csv"

    df2.to_csv(filename)
    return df2


if __name__ == "__main__":
    g_df = parse_xml('xml/WeaponParts.xml')
    s_df = parse_xml('xml/ShieldParts.xml')


