import cmath
import math
import os
import shutil
import uuid
import ifcopenshell
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool

script_path = os.path.abspath(os.path.dirname(__file__))
work_path = os.path.join(os.path.abspath(os.getcwd()), 'ifc')
out_path = os.path.join(os.path.abspath(os.getcwd()), 'ifc_clean')
done_path = os.path.join(os.path.abspath(os.getcwd()), 'ifc_done')

rgb = {'Белый': (255, 255, 255),
       'Тёмно-зелёный': (25, 129, 0),
       'Зелёный': (0, 255, 0),
       'Светло-зелёный': (28, 255, 50),
       'Тёмно-серый': (80, 80, 80),
       'Светло-серый': (150, 150, 150),
       'Cерый': (120, 120, 120),
       'Голубой': (30, 184, 253),
       'Коричневый': (139, 71, 38),
       'Пурпурный': (205, 38, 38),
       'Прозрачный': (205, 38, 38),
       'All': (50, 50, 50)
       }

def dprint(el, lev):
    pass
    # print(lev, el)

pset_level = 'Naviswork - уровни'

level = {'Шифр здания': 0, 'Шифр специализации': 1, 'Шифр подгруппы': 2, 'Шифр сборки': 3, 'Шифр элемента': 4}
coord_file = os.path.join(work_path, 'coords.txt')
system_file = os.path.join(work_path, 'system.txt')
def get_coord(coord_file):
    f = open(coord_file, 'r', encoding='utf-8')
    coord = {}
    for line in f:
        if '11' in line:
            c = line.split('\t')
            ang = float(c[4].replace('°', '').replace(',', '.').replace('\n', ''))
            if abs(ang - 360) < 0.001:
                ang = 0
            id = c[0]
            i = 0
            if id in coord.keys():
                sid = id
                while sid in coord.keys():
                    i = i + 1
                    sid = id + '.' + str(i)
                id = sid
            coord[id] = [float(c[1].replace(',', '.').replace('\n', '')), float(c[2].replace(',', '.').replace('\n', '')),
                         float(c[3].replace(',', '.').replace('\n', '')),
                         ang]
    return coord

def get_system(system_file):
    f = open(system_file, 'r', encoding='utf-8')
    system = {}
    for line in f:
        c = line.split('\t')
        system[c[0].strip()+c[1].strip()]=c[2].strip()
    return system


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

coord = get_coord(coord_file)
system = get_system(system_file)

class IFCConvert(object):
    def __init__(self, ifc_file):
        self.flag_write = True
        self.start_time = datetime.now()
        self.ifc_filename = ifc_file
        print('\nЧтение файла ' + os.path.split(self.ifc_filename)[1])
        id_bilding = ifc_file.split('\\')[-1]
        id_bilding = id_bilding.split('.')[0]
        self.id_bilding = id_bilding.replace('GCC-SNH-PD-', '')
        self.ifc = ifcopenshell.open(ifc_file)
        self.place = self.ifc.by_type("IfcProject")[0] #self.ifc.by_type("IfcSite")[0]
        self.placement = self.ifc.by_type("IfcSite")[0].ObjectPlacement
        self.ifc.remove(self.ifc.by_type("IfcSite")[0])
        self.place.Name = self.id_bilding
        self.owner_history = self.ifc.by_type("IfcOwnerHistory")[0]
        self.del_unused()
        self.color = self.get_dict_material()
        self.stage = {}
        self.system = {}
        self.subpos = []
        self.coord = {}

    def set_coord(self, site):
        id = self.ifc_filename.split('\\')[-1].strip('.ifc')
        if id not in self.coord or '1100000' not in self.coord:
            print('\n---------------- НЕ НАЙДЕНЫ КООРДИНАТЫ ' + id + ' ----------------')
            self.flag_write = False
            return
        x = self.coord[id][0] + self.coord['1100000'][0]#4061156
        y = self.coord[id][1] + self.coord['1100000'][1]#3780570
        z = self.coord[id][2]
        ang = self.coord[id][3] * math.pi / 180
        vekt = (math.cos(ang), math.sin(ang), 0.0)
        # Замена координат начала
        if site.ObjectPlacement is not None and site.ObjectPlacement.is_a("IfcLocalPlacement"):
            print('\nУстановка начала координат')
            site.ObjectPlacement.RelativePlacement.Location.Coordinates = (x, y, z)
            site.ObjectPlacement.RelativePlacement.RefDirection.DirectionRatios = vekt

    def del_unused(self):
        if not self.flag_write:
            return
        self.del_storey()
        self.del_layer()

    def get_dict_material(self):
        color = {}
        print('\nСоздание словаря с материалами ' + os.path.split(self.ifc_filename)[1])
        for c, rgbc in rgb.items():
            mat = self.ifc.createIfcMaterial(c)
            r, g, b = rgbc
            col = self.ifc.createIfcColourRgb(c, r / 255, g / 255, b / 255)
            t = None
            if c == 'Прозрачный':
                t = 0.5
            else:
                t = None
            ssr = self.ifc.createIfcSurfaceStyleRendering(col, t, None, None, None, None, None, None, "FLAT")
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
            print(col)
            isi, mat = self.color['All']
        element.Tag = ''
        isr = self.ifc.createIfcStyledRepresentation(context, "Style", "Material", [isi])
        imd = self.ifc.createIfcMaterialDefinitionRepresentation(None, None, [isr], mat)
        self.ifc.createIfcRelAssociatesMaterial(create_guid(), self.owner_history, 'MaterialLink',
                                                '', [element], mat)

    def write(self, out_path):
        if not self.flag_write:
            return
        print('\nЗапись в файл ' + os.path.split(self.ifc_filename)[1])
        ifc_loc_edit = os.path.join(out_path, os.path.split(self.ifc_filename)[1])
        self.ifc.write(ifc_loc_edit)
        print('\nВремя обработки - ' + os.path.split(self.ifc_filename)[1] + ' {}'.format(
            datetime.now() - self.start_time))

    def del_layer(self):
        print('Удаление слоёв ' + os.path.split(self.ifc_filename)[1])
        hh = self.ifc.by_type('IfcMaterial')
        for t in ['IfcRelAssociatesMaterial', 'IfcPresentationLayerAssignment', 'IfcRelAssociatesClassification',
                  'IfcStyledItem', 'IfcPresentationStyle', 'IfcMaterial', 'IfcSurfaceStyle']:
            for layer in self.ifc.by_type(t):
                self.ifc.remove(layer)

    def del_storey(self):
        print('Удаление этажей ' + os.path.split(self.ifc_filename)[1])
        new_elements = []
        for pset in self.ifc.by_type('IfcPropertySetDefinition'):
            if "Naviswork" not in pset.Name:
                if hasattr(pset, 'PropertyDefinitionOf'):
                    for p in pset.PropertyDefinitionOf:
                        self.ifc.remove(p)
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        self.ifc.remove(p)
                self.ifc.remove(pset)
        self.grids = self.ifc.by_type('IfcGrid')
        for c in self.ifc.by_type('ifcrelcontainedinspatialstructure'):
            if c.RelatingStructure.is_a('ifcbuildingstorey'):
                for el in c.RelatedElements:
                    new_elements.append(el)
                self.ifc.remove(c.RelatingStructure)
                self.ifc.remove(c)
        self.ifc.remove(self.ifc.by_type('ifcbuilding')[0])

    def del_assemblies(self):
        if not self.flag_write:
            return
        print('\nУдаление сборок ' + os.path.split(self.ifc_filename)[1])
        for a in self.ifc.by_type('IfcElementAssembly'):
            self.ifc.remove(a)

    def _get_naen(self, element):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Наименование" in p.Name:
                                return p.NominalValue.wrappedValue.strip()
                    return ''

    def _get_pos(self, element):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Шифр элемента" in p.Name:
                                return p.NominalValue.wrappedValue.strip()
        return ''

    def _get_obozn(self, element):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Позиция оборудования" in p.Name:
                                return p.NominalValue.wrappedValue.strip()
        return ''

    def _get_system(self, element):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Обозначение системы" in p.Name:
                                return p.NominalValue.wrappedValue.strip()

    def _get_subpos(self, element):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Позиция вложенного элемента" in p.Name:
                                return p.NominalValue.wrappedValue.strip()


    def _set_system(self, element, sys):
        for definition in element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                    if definition.RelatingPropertyDefinition.HasProperties is not None:
                        for p in definition.RelatingPropertyDefinition.HasProperties:
                            if p.Name is not None and "Назначение системы" in p.Name:
                                s_ = self._get_system(element)
                                if len(s_)>0:
                                    sys_ = sys+s_
                                    s = self.system.get(sys_, p.NominalValue.wrappedValue)
                                    if len(s)==0:
                                        print(sys_)
                                    p.NominalValue.wrappedValue = s
                                return
        return

    def _set_km_profile_(self, element):
        if not element.is_a('IfcElementAssembly') and element.IsDefinedBy is not None:
            set_type = False
            set_stal = False
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                        if definition.RelatingPropertyDefinition.HasProperties is not None:
                            for p in definition.RelatingPropertyDefinition.HasProperties:
                                if p.Name is not None and "Материал профиля" in p.Name:
                                    set_stal = True
                                    if len(p.NominalValue.wrappedValue)==0 and element.Description is not None:
                                        p.NominalValue.wrappedValue = "C345"
                                if p.Name is not None and "Тип профиля" in p.Name:
                                    set_type = True
                                    if len(p.NominalValue.wrappedValue)==0 and element.Description is not None:
                                        p.NominalValue.wrappedValue = element.Description
                                if set_type and set_stal:
                                    return


    def _change_name_(self, element, setpos):
        if not element.is_a('IfcElementAssembly') and element.IsDefinedBy is not None:
            if setpos:
                element.Name = self._get_pos(element)
            else:
                element.Name = self._get_naen(element)
            return


    def _change_element_(self, elements, tag, setpos):
        if not isinstance(elements, list):
            elements = [elements]
        if len(elements) > 0:
            for el in elements:
                if not el.is_a('IfcElementAssembly'):
                    self.set_color(el)
                    if tag is not None and "KM" in tag:
                        self._set_km_profile_(el)
                    if tag is not None and ("OV" in tag or "TH" in tag or "VK" in tag or "NVK" in tag):
                        if "OV" in tag:
                            sys = "OV"
                        else:
                            sys = "VK"
                        self._set_system(el, sys)
                    self._change_name_(el, setpos)


    def _add_assembly_(self, elements, group_name, parent_name, parent_element=None, copy_property=True, setpos=True):
        if not isinstance(elements, list):
            elements = [elements]
        if len(elements) == 0:
            return None
        self._change_element_(elements, group_name, setpos)
        elements_group = self.ifc.create_entity('IfcElementAssembly', create_guid(), self.owner_history, group_name,
                                                None)
        self.ifc.create_entity("IfcRelAggregates", create_guid(), self.owner_history, parent_name, group_name,
                               elements_group, elements)
        if copy_property:
            if parent_element is None:
                parent_element = elements[0]
            if parent_element is not None and parent_element.IsDefinedBy is not None:
                for definition in parent_element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        if definition.RelatingPropertyDefinition.Name is not None and "Naviswork" in definition.RelatingPropertyDefinition.Name:
                            pset_name = definition.RelatingPropertyDefinition.Name
                            property_values = []
                            if "борудование" in pset_name:
                                naen = self._get_naen(parent_element)
                                property_values.append(self.ifc.createIfcPropertySingleValue("Наименование", "Наименование", self.ifc.create_entity("IfcLabel", naen), None))
                            if definition.RelatingPropertyDefinition.HasProperties is not None:
                                for p in definition.RelatingPropertyDefinition.HasProperties:
                                    if p.Name is not None and "размер" not in p.Name and "Диаметр" not in p.Name:
                                        property_values.append(self.ifc.createIfcPropertySingleValue(p.Name, p.Name, p.NominalValue, None))
                            property_set = self.ifc.createIfcPropertySet(parent_element.GlobalId, self.owner_history, pset_name, None, property_values)
                            self.ifc.createIfcRelDefinesByProperties(parent_element.GlobalId, self.owner_history, None, None, [elements_group], property_set)
        return elements_group

    def _get_parent(self, elements):
        for el in elements:
            if el.IsDefinedBy is not None:
                obozn = self._get_obozn(el)
                subpos = self._get_subpos(el)
                if obozn == subpos and len(subpos)>0:
                    return el
        return None


    # Уровень 6
    def group_level_6(self, state, key_1, key_2, key_3, key_4, key_5):
        group_name = key_5
        parent_name = key_4
        elements = state[key_1][key_2][key_3][key_4][key_5]
        parent_element = None
        dprint(key_5, 6)
        parent_element = self._get_parent(elements)
        group = self._add_assembly_(elements, group_name, parent_name, parent_element, True, False)
        # if parent_element is not None:
        #     self.ifc.remove(parent_element)
        return group

    # Уровень 5
    def group_level_5(self, state, key_1, key_2, key_3, key_4):
        group_name = key_4
        parent_name = key_3
        element_on_level = state[key_1][key_2][key_3][key_4]
        elements = []
        if isinstance(element_on_level, dict):
            for element in element_on_level.keys():
                dprint(element, 5)
                if element == 'else' or element[8:].strip() not in self.subpos:
                    elements.extend(element_on_level[element])
                else:
                    elements_group = self.group_level_6(state, key_1, key_2, key_3, key_4, element)
                    if elements_group is not None:
                        elements.append(elements_group)
        if isinstance(element_on_level, list):
            elements = element_on_level
        if len(elements) > 0:
            return self._add_assembly_(elements, group_name, parent_name, None, True, True)
        else:
            return None

    # Уровень 4
    def group_level_4(self, state, key_1, key_2, key_3):
        group_name = key_3
        parent_name = key_2
        element_on_level = state[key_1][key_2][key_3]
        elements = []
        if self.grids is not None and len(self.grids)>0 and "KG" in key_3:
            elements.append(self._add_assembly_(self.grids, parent_name + "-GRID", parent_name, None, True, True))
            self.grids = None
        for element in element_on_level.keys():
            dprint(element, 4)
            if element == 'else':
                elements.extend(element_on_level[element])
            else:
                if element.replace(key_3+"-","").strip() not in self.subpos and 'EQP' in key_3:
                    for el in element_on_level[element]:
                        dprint(el, 9)
                        if el == 'else':
                            print(element)
                        for e in element_on_level[element][el]:
                            group_name_eqp = element
                            parent_name_eqp = group_name
                            eqp = self._add_assembly_(e, group_name_eqp, parent_name_eqp, e, True, True)
                            if eqp is not None:
                                elements.append(eqp)
                else:
                    elements_group = self.group_level_5(state, key_1, key_2, key_3, element)
                    if elements_group is not None:
                        elements.append(elements_group)
        return self._add_assembly_(elements, group_name, parent_name, None, False, False)

    # Уровень 3
    def group_level_3(self, state, key_1, key_2):
        group_name = key_2
        parent_name = key_1
        elements = []
        element_on_level = state[key_1][key_2]
        for element in state[key_1][key_2].keys():
            dprint(element, 3)
            if element == 'else':
                elements.extend(element_on_level[element])
            else:
                elements_group = self.group_level_4(state, key_1, key_2, element)
                if elements_group is not None:
                    elements.append(elements_group)
        site = self.ifc.createIfcSite(create_guid(), self.owner_history, group_name, None, None, self.placement, None, None, "ELEMENT",None, None, None, None, None)
        self.set_coord(site)
        container_project = self.ifc.createIfcRelAggregates(create_guid(), self.owner_history, "Project Container", None,site, elements)
        container_project = self.ifc.createIfcRelAggregates(create_guid(), self.owner_history, "Project Container", None,self.place, [site])
        return container_project

    # Уровень 2
    def group_level_2(self, state, key_1):
        group_name = key_1
        parent_name = ''
        elements = []
        for element in state[key_1].keys():
            dprint(element, 2)
            if element == 'else':
                elements.extend(state[key_1][element])
            else:
                elements_group = self.group_level_3(state, key_1, element)
                if elements_group is not None:
                    elements.append(elements_group)
        return elements

    # Уровень 1
    def group_level_1(self, state):
        if not self.flag_write:
            return
        projects = []
        for element in state.keys():
            dprint(element, 1)
            project_group = self.group_level_2(state, element)
            projects.extend(project_group)
        self.ifc.createIfcRelContainedInSpatialStructure(create_guid(), self.owner_history, "Beam", None,
                                                         projects,
                                                         self.place)

    def get_stage(self, pset_level, level_name):
        if not self.flag_write:
            return
        print('Получение списка свойств ' + os.path.split(self.ifc_filename)[1])
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
        system = {}
        for p in pset.HasProperties:
            if p.Name in level_name:
                inx_level = level_name[p.Name]
                val = p.NominalValue.wrappedValue
                id_building = p.NominalValue.wrappedValue
                if '-' in id_building:
                    id_building = id_building.split('-')[0]
                if not id_building.startswith('11'):
                    val = val.replace(id_building, self.id_bilding)
                    p.NominalValue.wrappedValue = val
                level_key[inx_level] = val
            if p.Name == 'Цвет':
                color = p.NominalValue.wrappedValue
            if p.Name == 'Позиция вложенного элемента':
                s = p.NominalValue.wrappedValue
                if len(s)>0 and s not in self.subpos:
                    self.subpos.append(s.strip())
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
        if "ОШИБКА" in val:
            # self.flag_write = False
            print(val)
        if (t1 == t2 or len(t1) < 1) and 'EQP-' not in t1:
            level_key[n_level - 1] = 'else'
        return dict_add_list(level_key, elements)

    def set_pset(self):
        if not self.flag_write:
            return
        print('Разбивка по уровням ' + os.path.split(self.ifc_filename)[1])
        for pset in self.ifc.by_type('IfcPropertySetDefinition'):
            if pset.Name is not None and "Naviswork" in pset.Name and "уровни" not in pset.Name:
                t = pset.Name
                t = t.replace('Naviswork - ', 'СНХП - ')
                pset.Name = t
                pset.Description = pset.Name
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        if len(p.NominalValue.wrappedValue) == 0:
                            p.NominalValue.wrappedValue = " "
                        if "none" in p.NominalValue.wrappedValue:
                            p.NominalValue.wrappedValue = p.NominalValue.wrappedValue.replace("none", self.id_bilding)
            else:
                # if hasattr(pset, 'PropertyDefinitionOf'):
                #     for p in pset.PropertyDefinitionOf:
                #         self.ifc.remove(p)
                #     if hasattr(pset, 'HasProperties'):
                #         for p in pset.HasProperties:
                #             self.ifc.remove(p)
                self.ifc.remove(pset)

def run(ifc_loc):
    ifc_t = IFCConvert(ifc_loc)
    ifc_t.system = system
    ifc_t.coord = coord
    stage = ifc_t.get_stage(pset_level, level)
    ifc_t.del_assemblies()
    ifc_t.get_dict_material()
    ifc_t.group_level_1(stage)
    ifc_t.set_pset()
    ifc_t.write(out_path)
    if ifc_t.flag_write:
        os.replace(ifc_loc, os.path.join(done_path, os.path.split(ifc_loc)[1]))


if __name__ == "__main__":
    ifc_file = []
    start_time = datetime.now()
    for file in os.listdir(work_path):
        if file.endswith('.ifc') and not file.endswith('_clean.ifc'):
            ifc_file.append(os.path.join(work_path, file))
            fname = os.path.split(os.path.join(work_path, file))
    assert len(ifc_file) > 0
    if len(ifc_file) > 1:
        pool = ThreadPool(min(len(ifc_file), 8))
        results = pool.map(run, ifc_file)
        pool.close()
        pool.join()
    else:
        run(ifc_file[0])
    print('Общее время обработки ' + str(len(ifc_file)) + ' файлов обработки - {}'.format(datetime.now() - start_time))
