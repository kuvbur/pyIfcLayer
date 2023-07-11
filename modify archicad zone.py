import os
import ifcopenshell

ifc_loc = "D:\\work\\renga\\test.ifc"
ifc_new = "D:\\work\\renga\\test_new.ifc"
ifc_file = ifcopenshell.open(ifc_loc)
zones = ifc_file.by_type("IfcSpace", include_subtypes=True)
for zone in zones:
    footprint_rep = None
    body_rep = None
    for repl in zone.Representation.Representations:
        if repl.RepresentationIdentifier == 'FootPrint':
            footprint_rep = repl
        if repl.RepresentationIdentifier == 'Body':
            body_rep = repl
    if footprint_rep is not None and body_rep is not None:
        axis2placement = footprint_rep.ContextOfItems.WorldCoordinateSystem
        ifc_direction = ifc_file.createIfcDirection((0., 0., 1.))
        ## Получаем спсок точек
        poly_zone = footprint_rep.Items[0].Elements
        if len(poly_zone)>1:
            ifcclosedprofile = ifc_file.createIfcArbitraryProfileDefWithVoids("AREA", None, poly_zone[0], poly_zone[1:])
        else:
            ifcclosedprofile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, poly_zone[0])
        ## Получаем маскимальную высоту
        min_z = 1000000
        max_z = -min_z
        for i in body_rep.Items:
            for point in i.Coordinates.CoordList:
                min_z = min(min_z, point[2])
                max_z = max(max_z, point[2])
        height = max(0, max_z-min_z)
        zone_solid = ifc_file.createIfcExtrudedAreaSolid(ifcclosedprofile,  axis2placement, ifc_direction, height)
        ifc_file.remove(body_rep.Items[0])
        body_rep.RepresentationType = "SweptSolid"
        body_rep.Items = [zone_solid]
ifc_file.write(ifc_new)