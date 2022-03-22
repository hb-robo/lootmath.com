# LOOTMATH - BORDERLANDS

import pandas as pd
import xml.etree.ElementTree as ET
from itertools import product

pd.options.mode.chained_assignment = None  # default='warn'

uniques = {
    'combat_rifles':
        ['Sentinel','Raven','Guardian','Destroyer','Avenger'],
    'machine_guns':
        ['Grinder','Ajax','Chopper','Draco','Ogre','Bastard','Revolution','Serpens'],
    'repeaters':
        ['Finger','Dove','Krom','Chiquito','Knoxx','Athena','Troll','Hornet','Invader',
         'Firehawk','Gemini','Protector','Violator','Rebel','Nemesis'],
    'machine_pistols':
        ['Clipper','Reaper','Thanatos','Vengeance','Stalker'],
    'revolvers':
        ['Patton','Madjack','Chimera','Anaconda','Unforgiven','Defiler','Equalizer','Aries'],
    'submachine_guns':
        ['Shredder','Spy','Typhoon','Wildcat','Bitch','Hellfire','Savior','Gasher','Tsunami']
}


def parse_xml(path, incl_knoxx=True):
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
    df2 = df.loc[~df['PartType'].isin(['Gear Type', 'Item Grade', 'Manufacturer', 'Bullet'])]

    weap_type = []
    part_names = []

    for rowname in list(df2.index):
        split_name = rowname.split('.')
        weap_type.append(split_name[0].replace('gd_weap_', ''))
        part_names.append(split_name[2])

    df2['LootCategory'] = weap_type
    df2.index = part_names

    cols = list(df2)
    cols.insert(0, cols.pop(cols.index('LootCategory')))
    df2 = df2.loc[:, cols]

    if not incl_knoxx:
        df2 = df2.loc[~df2['LootCategory'].str.contains("UniqueParts", case=False)]

    filename = path.replace('.xml','').replace('xml/', 'csv/')
    if incl_knoxx: filename += "_incl_knoxx"
    filename += ".csv"

    df2.to_csv(filename)

    return df2


def generate(df):

    # collect a list of unique PartType values
    part_types = df['PartType'].unique()
    type_dicts = {}

    for part_type in part_types:
        filtered_df = df[(df['PartType'] == part_type)]
        part_type_list = []
        for index, row in filtered_df.iterrows():
            part_type_list.append(index)
        type_dicts[part_type] = part_type_list



    all_permutations = [dict(zip(type_dicts, x)) for x in product(*type_dicts.values())]
    print(len(all_permutations))

    return 0

def parse_rules(xml_file):

    tree = ET.parse(xml_file)
    generation_rules = {} # dict to store essential generation info

    # iterates through ET until it finds "part" elements
    for gear_type in tree.findall('.//GearTemplate'):

        gear_name = gear_type.find('TargetType').text # e.g. 'Revolver'
        generation_rules[gear_name] = {}

        for attr in gear_type:
            if attr.tag == 'TargetType': continue  # already stored as name

            # next, we handle the list of valid manufacturers for the loot type
            elif attr.tag == 'ValidMakes':
                manufacturer_list = []
                for manufacturer in attr:
                    manufacturer_list.append(manufacturer.find('Name').text)
                generation_rules[gear_name]['Manufacturer'] = manufacturer_list

            # parse and collect base stats for loot type
            elif attr.tag in ['BaseStats', 'AttrMod']:
                stats = {}
                for stat in attr:
                    if attr.tag == 'AttrMod':
                        statname = "AttrMod_%s_%s" % (stat.tag, stat.attrib['modType'])
                    else:
                        statname = "%s_%s" % (stat.tag, stat.attrib['modType'])

                    stats[statname] = stat.text

                generation_rules[gear_name]['BaseStats'] = stats

            # now the meat of it, parsing list of legal part variants
            elif attr.tag == 'PartList':
                part_type = attr.find('PartType').text
                part_list = set()
                for part_pool in attr:
                    if part_pool.tag == 'PartType': continue
                    elif part_pool.tag == 'Option':
                        part_list.add(part_pool.text)
                    elif part_pool.tag == 'GeneralPool':
                        split_pool = part_pool.text.split(',')
                        part_list.update(split_pool)
                    elif part_pool.tag == 'OptionBin':
                        if '-' in part_pool.text:
                            pool_range = part_pool.text.split('-')
                            prefix = pool_range[0][0] #first letter of range lower bound
                            low_bound = int(''.join(i for i in pool_range[0] if i.isdigit()))
                            high_bound = int(''.join(i for i in pool_range[1] if i.isdigit()))
                            for i in range(low_bound, high_bound+1):
                                if i < 10:
                                    part_id = "%s00%s" % (prefix, i)
                                elif i < 100:
                                    part_id = "%s0%s" % (prefix, i)
                                else:
                                    part_id = "%s%s" % (prefix, i)
                                part_list.add(part_id)
                        else:
                            split_pool = part_pool.text.split(',')
                            part_list.update(split_pool)
                generation_rules[gear_name][part_type] = list(part_list)

    df = pd.DataFrame.from_dict(generation_rules, 'index')
    identify_parts()

    df.to_csv('./csv/LootRules.csv')


# a small function that changes the part id numbers to part names in LootRules
def identify_parts(df):

    for col in list(df):
        if col == 'BaseStats': continue
        elif:



if __name__ == "__main__":
    g_df = parse_xml('xml/WeaponParts.xml', incl_knoxx=False)
    s_df = parse_xml('xml/ShieldParts.xml', incl_knoxx=False)

    #guns = generate(g_df)
    #shields = generate(s_df)
    #parse_rules('xml/WeaponRules.xml')
    identify_parts()
