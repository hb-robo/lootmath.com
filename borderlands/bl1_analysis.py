# LOOTMATH - BORDERLANDS

import pandas as pd
import xml.etree.ElementTree as ET
from itertools import product

pd.options.mode.chained_assignment = None  # default='warn'

def parse_xml(path, incl_knoxx=True):
    # first, we parse the XML file into an ElementTree for QOL
    tree = ET.parse(path)
    parts = {} # dict to store essential part info

    # iterates through ET until it finds "part" elements
    for part in tree.findall('.//Part'):

        id = part.attrib['id']
        name = part.find('Name').text
        if name in parts:
            name = "%s_2" % (name)

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
    df2 = df.loc[~df['PartType'].isin(['Bullet'])]

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

# a small function that changes the part id numbers to part names in LootRules
def identify_parts(df, g_df):

    for index, row in df.iterrows():
        for col in list(df):
            if col == 'BaseStats' or row[col] != row[col]: # checks for NaN instead of list
                continue
            elif row[col]:
                replacement_list = []
                for id in row[col]:
                    item_name = g_df.loc[g_df['id'] == id].index.format()
                    replacement_list.append(item_name)
                flat_list = [item for sublist in replacement_list for item in sublist]

                row[col] = flat_list
                print(flat_list)

    return df


def parse_rules(xml_file, g_df):

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

    # now we fill the missing Part Types on the Knoxx weapons.
    # here is a list of the unique and legendary Knoxx DLC weapons and their weapon type.
    knoxx_crs = ['Tediore Avenger']
    knoxx_cshots = ['Dahl Jackal']
    knoxx_rps = ['Hyperion Nemesis', "Athena's Wisdom","Chiquito Amigo", "Knoxx's Gold"]
    knoxx_mps = ['Vladof Stalker']
    knoxx_revs = ['Atlas Aries']
    knoxx_rls = ['Torgue Undertaker']
    knoxx_smgs = ['Maliwan Tsunami', 'Dahl Typhoon']
    knoxx_srs = ['Jakobs Bessie']
    knoxx_sasrs = ["Kyros' Power"]
    knoxx_mgs = ['SandS Serpens', "Ajax's Spear", "The Chopper"]

    # Since these weapons have their own row, we will correct their Gear Type to the proper weapon category.
    for index, row in df.iterrows():
        if any(knoxx_r in index for knoxx_r in knoxx_revs):
            row['Gear Type'] = ['j001']
        elif any(knoxx_cs in index for knoxx_cs in knoxx_cshots):
            row['Gear Type'] = ['j003']
        elif any(knoxx_cr in index for knoxx_cr in knoxx_crs):
            row['Gear Type'] = ['j004']
        elif any(knoxx_mg in index for knoxx_mg in knoxx_mgs):
            row['Gear Type'] = ['j005']
        elif any(knoxx_mp in index for knoxx_mp in knoxx_mps):
            row['Gear Type'] = ['j006']
        elif any(knoxx_rp in index for knoxx_rp in knoxx_rps):
            row['Gear Type'] = ['j007']
        elif any(knoxx_smg in index for knoxx_smg in knoxx_smgs):
            row['Gear Type'] = ['j008']
        elif any(knoxx_rl in index for knoxx_rl in knoxx_rls):
            row['Gear Type'] = ['j009']
        elif any(knoxx_sr in index for knoxx_sr in knoxx_srs):
            row['Gear Type'] = ['j010']
        elif any(knoxx_sasr in index for knoxx_sasr in knoxx_sasrs):
            row['Gear Type'] = ['j011']

    # Next, we need to replace all four-character ID codes with the names of the
    # corresponding loot part name, for readability and to make some indexing easier.
    df = identify_parts(df, g_df)

    # Next, we have to handle empty data cells. Two cases in particular:
    #   1. Only the default weapons have the weapon type base stats and
    #       stat modifiers. These need to be copied over to all variants.
    #   2. Unique weapons have empty cells that indicate a deferral to
    #       the base weapon type's part pool. These need to copied over as well.



    df.to_csv('./csv/LootRules.csv')


if __name__ == "__main__":
    g_df = parse_xml('xml/WeaponParts.xml', incl_knoxx=False)
    s_df = parse_xml('xml/ShieldParts.xml', incl_knoxx=False)

    #guns = generate(g_df)
    #shields = generate(s_df)
    parse_rules('xml/WeaponRules.xml', g_df)
    #identify_parts()
