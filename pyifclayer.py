import csv
import os
import re

import ifcopenshell

IFCALLTYPE = ['IfcColumn', 'IfcSlab', 'IfcDiscreteAccessory', 'IfcBeam', 'IfcMember', 'IfcGrid']


def get_rule(layers_rule):
    # Загружаем правила
    rule_list = []
    with open(layers_rule, mode='r') as infile:
        reader = csv.reader(infile, delimiter='\t')
        for rows in reader:
            if len(rows)>0:
                layer_name = rows[0].strip()
                if layer_name != 'Layer Name':
                    if rows[1] == 'All':
                        ifctype = IFCALLTYPE
                    else:
                        ifctype = rows[1].split(';')
                    regtxt = rows[2].replace('\\\\', '\\')
                    rule_list.append({'Layer Name': layer_name, 'IfcType': ifctype, 'Name': regtxt.split(';')})
    return rule_list


def get_assambly_element(ifc_file, element):
    out = []
    out_id = [element.id()]
    for ass in ifc_file.get_inverse(element):
        if 'RelatingObject' in ass.get_info():
            if ass.RelatingObject.is_a('IfcElementAssembly'):
                for assembly in ass.RelatingObject.IsDecomposedBy:
                    for el in assembly.RelatedObjects:
                        if el.id() not in out_id:
                            out.append(el)
                            out_id.append(el.id())
    return out


def main(ifc_loc, rule_list):
    # Парсим IFC и разбиваем на слои
    ifc_file = ifcopenshell.open(ifc_loc)
    used_element = []
    list_element = {}
    for rule in rule_list:
        for IfcType in rule['IfcType']:
            IfcType = IfcType.strip()
            if len(IfcType) > 0:
                products = ifc_file.by_type(IfcType, include_subtypes=True)
                for element in products:
                    # Добавляем основной элемент
                    for IfcName in rule['Name']:
                        repl = element.Representation.Representations[0]
                        if repl is not None and repl.id() not in used_element and len(
                                ''.join(re.findall(IfcName.strip(), element.Name))) > 0:
                            if rule['Layer Name'] not in list_element:
                                list_element[rule['Layer Name']] = []
                            list_element[rule['Layer Name']].append(repl)
                            used_element.append(repl.id())
                            # Добавляем элементы сборок
                            for el in get_assambly_element(ifc_file, element):
                                repl = el.Representation.Representations[0]
                                assert repl.is_a('IfcShapeRepresentation')
                                if repl.id() not in used_element:
                                    if rule['Layer Name'] not in list_element:
                                        list_element[rule['Layer Name']] = []
                                    list_element[rule['Layer Name']].append(repl)
                                    used_element.append(repl.id())
    # Удаляем старые слои
    for layer in ifc_file.by_type('IfcPresentationLayerAssignment'):
        IfcShapes = []
        name = layer.Name
        for IfcShape in list(layer.AssignedItems):
            if IfcShape.id() not in used_element:
                IfcShapes.append(IfcShape)
        ifc_file.remove(layer)
        if len(IfcShapes) > 0:
            new_layer = ifc_file.createIfcPresentationLayerAssignment(name, '', IfcShapes, '')
    for name, element in list_element.items():
        new_layer = ifc_file.createIfcPresentationLayerAssignment(name, "", element, "")
    ifc_loc_edit = str(ifc_loc.replace('.ifc', '_правильный.ifc'))
    ifc_file.write(ifc_loc_edit)
    return len(used_element)


if __name__ == "__main__":
    script_path = os.path.abspath(os.path.dirname(__file__))
    work_path = os.path.abspath(os.getcwd())
    ifc_file = []
    for file in os.listdir(work_path):
        if file.endswith('.ifc') and not file.endswith('_правильный.ifc'):
            ifc_file.append(os.path.join(work_path, file))
            print(os.path.join(work_path, file))
    assert len(ifc_file) > 0
    layers_rule = os.path.join(script_path, 'layers_rule.csv')
    if os.path.exists(layers_rule):
        rule_list = get_rule(layers_rule)
        assert len(rule_list) > 0
    for ifc_loc in ifc_file:
        print(ifc_loc, main(ifc_loc, rule_list))
    print('End')
