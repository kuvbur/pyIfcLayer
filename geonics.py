import os
import ifcopenshell

def ifc_proc(ifc_loc):
    new_filename = ifc_loc.replace('.ifc', '_clean.ifc')
    ifc = ifcopenshell.open(ifc_loc)
    ifc_t = ifcopenshell.file(schema=ifc.schema, schema_version=ifc.schema_version)
    project = ifc.by_type('IfcProject')[0]
    site = ifc.by_type('IfcSite')[0]
    owner_history = ifc.by_type('IfcOwnerHistory')[0]
    owner_t = ifc_t.add(owner_history)
    for unit in ifc.by_type('IFCUNITASSIGNMENT'):
        ifc_t.add(unit)
    project_t = ifc_t.add(project)
    site_t = ifc_t.add(site)
    ifc_t.create_entity('IfcRelAggregates',
                        site.Decomposes[0].GlobalId, owner_t, None, None, project_t, [site_t])
    lands = []
    for zone in ifc.by_type('IfcSpatialZone'):
        placement = ifc_t.add(zone.ObjectPlacement)
        shape = ifc_t.add(zone.Representation)
        land = ifc_t.create_entity('IfcCivilElement', GlobalId=zone.GlobalId, Name=zone.Name,
                            Representation=shape,
                            ObjectPlacement=placement
                            )
        lands.append(land)

    ifc_t.create_entity('IfcRelAggregates',
                        ifcopenshell.guid.new(), owner_t, None, None, site_t, lands)

    ifc_t.write(new_filename)



script_path = os.path.abspath(os.path.dirname(__file__))
work_path = os.path.abspath(os.getcwd())
ifc_file = []
for file in os.listdir(work_path):
    if file.endswith('.ifc') and not file.endswith('_clean.ifc'):
        ifc_file.append(os.path.join(work_path, file))
assert len(ifc_file) > 0
for ifc_loc in ifc_file:
    ifc_proc(ifc_loc)
