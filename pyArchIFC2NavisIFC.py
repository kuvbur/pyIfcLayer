import cmath
import math
import os
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
       'Серый': (120, 120, 120),
       'Голубой': (30, 184, 253),
       'Коричневый': (139, 71, 38),
       'Пурпурный': (205, 38, 38),
       'All': (50, 50, 50)
       }

pset_level = 'Naviswork - уровни'

level = {'Шифр здания': 0, 'Шифр специализации': 1, 'Шифр подгруппы': 2, 'Шифр сборки': 3, 'Шифр элемента': 4}
coord_file = os.path.join(work_path, 'Координаты начала здания (пересечение А_1).txt')


def get_coord(coord_file):
    f = open(coord_file, 'r', encoding='utf-8')
    coord = {}
    for line in f:
        if '1166' in line:
            c = line.split('\t')
            ang = float(c[4].strip('°').replace(',', '.'))
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
            coord[id] = [float(c[1].replace(',', '.')), float(c[2].replace(',', '.')),
                         float(c[3].replace(',', '.')),
                         ang]
    return coord


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
        self.flag_write = True
        self.start_time = datetime.now()
        self.ifc_filename = ifc_file
        print('\nЧтение файла ' + os.path.split(self.ifc_filename)[1])
        id_bilding = ifc_file.split('\\')[-1]
        id_bilding = id_bilding.split('.')[0]
        self.id_bilding = id_bilding.replace('GCC-SNH-PD-', '')
        self.ifc = ifcopenshell.open(ifc_file)
        self.place = self.ifc.by_type("IfcSite")[0]
        self.place.Name = self.id_bilding
        self.owner_history = self.ifc.by_type("IfcOwnerHistory")[0]
        self.del_unused()
        self.color = self.get_dict_material()
        self.stage = {}

    def set_coord(self, coord):
        if self.id_bilding not in coord:
            print('\n---------------- НЕ НАЙДЕНЫ КООРДИНАТЫ ' + self.id_bilding + ' ----------------')
            self.flag_write = False
            return
        x = coord[self.id_bilding][0] + 4061156
        y = coord[self.id_bilding][1] + 3780570
        z = coord[self.id_bilding][2]
        ang = coord[self.id_bilding][3] * math.pi / 180
        vekt = (math.cos(ang), math.sin(ang), 0.0)
        # Замена координат начала
        if self.place.ObjectPlacement is not None and self.place.ObjectPlacement.is_a("IfcLocalPlacement"):
            print('\nУстановка начала координат')
            self.place.ObjectPlacement.RelativePlacement.Location.Coordinates = (x, y, z)
            self.place.ObjectPlacement.RelativePlacement.RefDirection.DirectionRatios = vekt

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
        for t in ['IfcRelAssociatesMaterial', 'IfcPresentationLayerAssignment', 'IfcRelAssociatesClassification',
                  'IfcStyledItem', 'IfcPresentationStyle', 'IfcMaterial', 'IfcSurfaceStyle']:
            for layer in self.ifc.by_type(t):
                self.ifc.remove(layer)

    def del_storey(self):
        print('Удаление этажей ' + os.path.split(self.ifc_filename)[1])
        new_elements = []
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

    # Уровень 5
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
        if not self.flag_write:
            return
        projects = []
        for element in state.keys():
            project_group = self.group_level_2(state, element)
            projects.append(project_group)
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
        for p in pset.HasProperties:
            if p.Name in level_name:
                inx_level = level_name[p.Name]
                val = p.NominalValue.wrappedValue
                id_building = p.NominalValue.wrappedValue
                if '-' in id_building:
                    id_building = id_building.split('-')[0]
                if not id_building.startswith('1166'):
                    val = val.replace(id_building, self.id_bilding)
                level_key[inx_level] = val
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
        if t1 == t2 or len(t1) < 1:
            level_key[n_level - 1] = 'else'
        return dict_add_list(level_key, elements)

    def set_pset(self):
        if not self.flag_write:
            return
        print('Разбивка по уровням ' + os.path.split(self.ifc_filename)[1])
        for pset in self.ifc.by_type('IfcPropertySetDefinition'):
            if "Naviswork" in pset.Name and "уровни" not in pset.Name:
                t = pset.Name
                t = t.replace('Naviswork - ', '')
                pset.Name = t
                pset.Description = pset.Name
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        if len(p.NominalValue.wrappedValue) == 0:
                            p.NominalValue.wrappedValue = " "
            else:
                if hasattr(pset, 'PropertyDefinitionOf'):
                    for p in pset.PropertyDefinitionOf:
                        self.ifc.remove(p)
                if hasattr(pset, 'HasProperties'):
                    for p in pset.HasProperties:
                        self.ifc.remove(p)
                self.ifc.remove(pset)


def run(ifc_loc):
    ifc_t = IFCConvert(ifc_loc)
    coord = get_coord(coord_file)
    ifc_t.set_coord(coord)
    stage = ifc_t.get_stage(pset_level, level)
    ifc_t.del_assemblies()
    ifc_t.get_dict_material()
    ifc_t.group_level_1(stage)
    ifc_t.set_pset()
    ifc_t.write(out_path)
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
