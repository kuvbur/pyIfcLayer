#!/usr/bin/env python3

# Convert zone shape representation from 'Tessellation' to 'SweptSolid'

import sys

APP_TITLE = 'Renga IFC Compatibility Tool'
APP_DESCRIPTION = 'Convert zones shape representation in IFC file from "Tessellation" to "SweptSolid" to be compatible with Renga.\n'

APP_VER_MAJOR = 1
APP_VER_MINOR = 0

# Maximum absolute zone height in mm
MAX_ZONE_HEIGH_ABS = 1000000


def zones(file_in, file_out):
	print('\nProcessing input file …\n')

	import ifcopenshell

	zones_processed = 0

	ifc_file = ifcopenshell.open(file_in)

	# Collect zones
	zones = ifc_file.by_type("IfcSpace", include_subtypes=True)
	zones_count = len(zones)
	print(f'Zones count:\n\t{zones_count}')

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

			## Получаем список точек
			poly_zone = footprint_rep.Items[0].Elements
			if len(poly_zone) > 1:
				ifcclosedprofile = ifc_file.createIfcArbitraryProfileDefWithVoids("AREA", None, poly_zone[0], poly_zone[1:])
			else:
				ifcclosedprofile = ifc_file.createIfcArbitraryClosedProfileDef("AREA", None, poly_zone[0])

			## Получаем максимальную высоту
			min_z = MAX_ZONE_HEIGH_ABS
			max_z = -min_z

			for i in body_rep.Items:
				for point in i.Coordinates.CoordList:
					min_z = min(min_z, point[2])
					max_z = max(max_z, point[2])
			height = max(0, max_z - min_z)
			zone_solid = ifc_file.createIfcExtrudedAreaSolid(ifcclosedprofile,  axis2placement, ifc_direction, height)
			ifc_file.remove(body_rep.Items[0])
			body_rep.RepresentationType = "SweptSolid"
			body_rep.Items = [zone_solid]
			zones_processed += 1

	if zones_count > 0:
		# Save new IFC file with converted zones
		ifc_file.write(file_out)
	return zones_processed


def info():
	print(f'{APP_TITLE} {APP_VER_MAJOR}.{APP_VER_MINOR}')
	print(APP_DESCRIPTION)


def usage():
	print('\nUsage:\n./renga_ifc_compat.py input.ifc output.ifc\n')
	print('input.ifc\n\tinput IFC file with "Tessellation" zone shape representation')
	print('output.ifc\n\tnew converted output IFC file with "SweptSolid" zone shape representation\n')


def main(file_in=None, file_out=None):
	info()

	if file_in is None:
		usage()
		return 0

	if file_out is None:
		file_out = 'new.ifc'

	print(f'Input file:\n\t{file_in}')
	print(f'Output file:\n\t{file_out}')

	# Process zones
	result = zones(file_in, file_out)
	print(f'Processed zones:\n\t{result}')


if __name__ == '__main__':
	if len(sys.argv) > 2:
		main(sys.argv[1], sys.argv[2])
	elif len(sys.argv) > 1:
		main(sys.argv[1])
	else:
		main()
