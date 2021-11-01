from builtins import isinstance

import flatdict
import os
import uuid
import ifcopenshell

rgb = {'Белый': (255, 255, 255),
       'Тёмно-зелёный': (25, 129, 0),
       'Зелёный': (0, 255, 0),
       'Светло-зелёный': (28, 255, 50),
       'Светло-серый': (80, 80, 80),
       'Тёмно-серый': (150, 150, 150),
       'Серый': (120, 120, 120),
       'Голубой': (30, 184, 253),
       'Коричневый': (139, 71, 38),
       'Пурпурный': (205, 38, 38),
       'All': (50, 50, 50)
       }

def create_guid():
    return ifcopenshell.guid.compress(uuid.uuid1().hex)


def dict_merge(j1, j2):
    for k, v in j2.items():
        if k in j1 and isinstance(j1[k], dict) and isinstance(v, dict):
            dict_merge(j1[k], v)
        else:
            if k in j1 and isinstance(j1[k], list) and isinstance(v, list):
                j1[k].extend(v)
            else:
                j1[k] = v


def dict_add_list(key_el, list_el):
    if key_el:
        head, *tail = key_el
        return {head: dict_add_list(tail, list_el)}
    else:
        return list_el


class IFCConvert(object):
    def __init__(self, ifc_file):
        self.ifc_filename = ifc_file
        self.ifc = ifcopenshell.open(ifc_file)
        self.place = self.ifc.by_type("IfcSite")[0]
        self.place = self.ifc.by_type("IfcSite")[0]
        self.owner_history = self.ifc.by_type("IfcOwnerHistory")[0]
        self.del_unused()
        self.color = self.get_dict_material()
        self.stage = {}

    def del_unused(self):
        self.del_storey()
        self.del_layer()

    def get_dict_material(self):
        color = {}
        for c, rgbc in rgb.items():
            mat = self.ifc.createIfcMaterial(c)
            r, g, b = rgbc
            col = self.ifc.createIfcColourRgb(None, r / 255, g / 255, b / 255)
            ssr = self.ifc.createIfcSurfaceStyleRendering(col, None, None, None, None, None, None, None, "FLAT")
            iss = self.ifc.createIfcSurfaceStyle(None, "BOTH", [ssr])
            psa = self.ifc.createIfcPresentationStyleAssignment([iss])
            isi = self.ifc.createIfcStyledItem(None, [psa], None)
            color[c] = [isi, mat]
        return color

    def set_color(self, element):
        context = ''
        try:
            context = element.Representation.Representations[0].ContextOfItems.ParentContext
        except:
            return
        try:
            col = element.Tag
        except:
            return
        if col in self.color:
            isi, mat = self.color[col]
        else:
            isi, mat = self.color['All']
        element.Tag = ''
        isr = self.ifc.createIfcStyledRepresentation(context, "Style", "Material", [isi])
        imd = self.ifc.createIfcMaterialDefinitionRepresentation(None, None, [isr], mat)
        self.ifc.createIfcRelAssociatesMaterial(create_guid(), self.owner_history, 'MaterialLink',
                                                '', [element], mat)
        pass

    def write(self):
        ifc_loc_edit = str(self.ifc_filename.replace('.ifc', '_правильный.ifc'))
        self.ifc.write(ifc_loc_edit)

    def del_layer(self):
        for t in ['IfcRelAssociatesMaterial', 'IfcPresentationLayerAssignment', 'IfcRelAssociatesClassification', 'IfcStyledItem', 'IfcPresentationStyle']:
            for layer in self.ifc.by_type(t):
                self.ifc.remove(layer)

    def del_storey(self):
        new_elements = []
        self.grids = self.ifc.by_type('IfcGrid')
        for c in self.ifc.by_type('IfcRelContainedInSpatialStructure'):
            if c.RelatingStructure.is_a('IfcBuildingStorey'):
                for el in c.RelatedElements:
                    new_elements.append(el)
                self.ifc.remove(c.RelatingStructure)
                self.ifc.remove(c)
        self.ifc.remove(self.ifc.by_type('IfcBuilding')[0])

    def del_assemblies(self):
        for a in self.ifc.by_type('IfcElementAssembly'):
            self.ifc.remove(a)

    def _add_assembly_(self, element, group_name='', parent_name=''):
        if not isinstance(element, list):
            element = [element]
        if len(element) > 0:
            for el in element:
                if not el.is_a('IfcElementAssembly'):
                    self.set_color(el)
            elements_group = self.ifc.create_entity('IfcElementAssembly', create_guid(), self.owner_history, group_name,
                                                    None)
            self.ifc.create_entity("IfcRelAggregates", create_guid(), self.owner_history, parent_name, group_name,
                                   elements_group, element)
            return elements_group
        else:
            return None

    # Уровень 6
    def group_level_6(self, state, key_1, key_2, key_3, key_4, key_5):
        group_name = key_5
        parent_name = key_4
        elements = state[key_1][key_2][key_3][key_4][key_5]
        if 'GRID' in key_3:
            elements.extend(self.grids)
        return self._add_assembly_(elements, group_name, parent_name)

    # Уровень 4
    def group_level_5(self, state, key_1, key_2, key_3, key_4):
        group_name = key_4
        parent_name = key_3
        element_on_level = state[key_1][key_2][key_3][key_4]
        elements = []
        if isinstance(element_on_level, dict):
            for element in element_on_level.keys():
                if element == 'else':
                    elements.extend(element_on_level[element])
                else:
                    elements_group = self.group_level_6(state, key_1, key_2, key_3, key_4, element)
                    if elements_group is not None:
                        elements.append(elements_group)
        if isinstance(element_on_level, list):
            elements = element_on_level
        if len(elements) > 0:
            return self._add_assembly_(elements, group_name, parent_name)
        else:
            return None

    # Уровень 4
    def group_level_4(self, state, key_1, key_2, key_3):
        group_name = key_3
        parent_name = key_2
        element_on_level = state[key_1][key_2][key_3]
        elements = []
        for element in element_on_level.keys():
            if element == 'else':
                elements.extend(element_on_level[element])
            else:
                elements_group = self.group_level_5(state, key_1, key_2, key_3, element)
                if elements_group is not None:
                    elements.append(elements_group)
        return self._add_assembly_(elements, group_name, parent_name)

    # Уровень 3
    def group_level_3(self, state, key_1, key_2):
        group_name = key_2
        parent_name = key_1
        elements = []
        element_on_level = state[key_1][key_2]
        for element in state[key_1][key_2].keys():
            if element == 'else':
                elements.extend(element_on_level[element])
            else:
                elements_group = self.group_level_4(state, key_1, key_2, element)
                if elements_group is not None:
                    elements.append(elements_group)
        return self._add_assembly_(elements, group_name, parent_name)

    # Уровень 2
    def group_level_2(self, state, key_1):
        group_name = key_1
        parent_name = ''
        elements = []
        for element in state[key_1].keys():
            if element == 'else':
                elements.extend(state[key_1][element])
            else:
                elements_group = self.group_level_3(state, key_1, element)
                if elements_group is not None:
                    elements.append(elements_group)
        return self._add_assembly_(elements, group_name, parent_name)

    # Уровень 1
    def group_level_1(self, state):
        projects = []
        for element in state.keys():
            project_group = self.group_level_2(state, element)
            projects.append(project_group)
        self.ifc.createIfcRelContainedInSpatialStructure(create_guid(), self.owner_history, "Beam", None,
                                                         projects,
                                                         self.place)

    def get_stage(self, pset_level, level_name):
        level_dict = {}
        for pset in self.ifc.by_type('IfcPropertySetDefinition'):
            if pset.Name == pset_level:
                level_dict_ = self._set_one_stage_(pset, level_dict, level_name)
                dict_merge(level_dict, level_dict_)
        return level_dict

    def _set_one_stage_(self, pset, level_dict, level_name):
        n_level = len(level_name)
        level_key = ['' for i in range(n_level)]
        color = ''
        for p in pset.HasProperties:
            if p.Name in level_name:
                inx_level = level_name[p.Name]
                level_key[inx_level] = p.NominalValue.wrappedValue
            if p.Name == 'Цвет':
                color = p.NominalValue.wrappedValue
        elements = []
        for p in pset.PropertyDefinitionOf:
            for o in p.RelatedObjects:
                try:
                    o.Tag = color
                except:
                    pass
                elements.append(o)
        t1 = level_key[n_level - 1]
        t2 = level_key[n_level - 2]
        if t1 == t2 or len(t1)<1:
            level_key[n_level - 1] = 'else'
        return dict_add_list(level_key, elements)

    def set_pset(self):
        for pset in self.ifc.by_type('IfcPropertySetDefinition'):
            if "Naviswork" in pset.Name and "уровни" not in pset.Name:
                t = pset.Name
                t = t.replace('Naviswork - ', '')
                pset.Name = t
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        if len(p.NominalValue.wrappedValue)==0:
                            p.NominalValue.wrappedValue = " "
            else:
                if hasattr(pset, 'PropertyDefinitionOf'):
                    for p in pset.PropertyDefinitionOf:
                        self.ifc.remove(p)
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        self.ifc.remove(p)
                self.ifc.remove(pset)


if __name__ == "__main__":
    script_path = os.path.abspath(os.path.dirname(__file__))
    work_path = os.path.abspath(os.getcwd())
    ifc_file = []
    for file in os.listdir(work_path):
        if file.endswith('.ifc') and not file.endswith('_правильный.ifc'):
            ifc_file.append(os.path.join(work_path, file))
            print(os.path.join(work_path, file))
    assert len(ifc_file) > 0
    pset_level = 'Naviswork - уровни'
    level = {'Шифр здания': 0, 'Шифр специализации': 1, 'Шифр подгруппы': 2, 'Шифр сборки': 3, 'Шифр элемента': 4}
    for ifc_loc in ifc_file:
        ifc_t = IFCConvert(ifc_loc)
        stage = ifc_t.get_stage(pset_level, level)
        ifc_t.del_assemblies()
        ifc_t.get_dict_material()
        ifc_t.group_level_1(stage)
        ifc_t.set_pset()
        ifc_t.write()
    print('End')