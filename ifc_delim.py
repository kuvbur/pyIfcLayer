import os
import ifcopenshell
import math


def set_placement(site, x=0, y=0, z=0, angle=0):
    ang = angle * math.pi / 180
    vekt = (math.cos(ang), math.sin(ang), 0.0)
    if site.ObjectPlacement is not None and site.ObjectPlacement.is_a("IfcLocalPlacement"):
        site.ObjectPlacement.RelativePlacement.Location.Coordinates = (
            x, y, z)
        site.ObjectPlacement.RelativePlacement.RefDirection.DirectionRatios = vekt
        return site
    return None


class IFCFile(object):
    def __init__(self, schema=None, schema_version=None):
        self.flag_write = True
        self.ifc = ifcopenshell.file(
            schema=schema, schema_version=schema_version)

    def add(self, elements):
        if type(elements) == list:
            for el in elements:
                self.ifc.add(el)
            return
        self.ifc.add(elements)

    def write(self, ifc_filename):
        if self.flag_write:
            self.ifc.write(ifc_filename+".ifc")


ifc = ifcopenshell.open("test.ifc")
project = ifc.by_type("IfcProject")[0]
site = ifc.by_type("IfcSite")[0]
owner_history = ifc.by_type("IfcOwnerHistory")[0]

ifc_f = {}
for layer in ifc.by_type('IfcPresentationLayerAssignment'):
    ifc_f[layer.Name] = IFCFile(ifc.schema, ifc.schema_version)

for n, f in ifc_f.items():
    f.add(project)
    f.add(site)
    f.add(owner_history)


for n, f in ifc_f.items():
    f.write("test//"+n)
hh = 1
