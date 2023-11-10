import os

script_path = os.path.abspath(os.path.dirname(__file__))
work_path = os.path.abspath(os.getcwd())
ifc_file = []
for file in os.listdir(work_path):
    if file.endswith('.ifc') and not file.endswith('_clean.ifc'):
        ifc_file.append(os.path.join(work_path, file))
assert len(ifc_file) > 0
for ifc_loc in ifc_file:
    new_filename = ifc_loc.replace(".ifc", '_clean.ifc')
    with open(ifc_loc, 'r') as f1, open(new_filename, 'w') as f2:
        content = f1.read()
        # remove end line characters
        content = content.replace("\n", "")
        lines = content.split(");")
        for line in lines:
            if "IFCQUANTITYLENGTH" in line:
                line = line.replace("IFCQUANTITYLENGTH", "IFCPROPERTYSINGLEVALUE")
                txt = line.split(",")
                txt[3] = "IFCINTEGER(" + txt[3].split(".")[0]+ ")"
                txt.pop(1)
                line = ",".join(txt)
            if "IFCQUANTITYWEIGHT" in line:
                line = line.replace("IFCQUANTITYWEIGHT", "IFCPROPERTYSINGLEVALUE")
                txt = line.split(",")
                txt[3] = "IFCREAL(" + txt[3]+ ")"
                txt.pop(1)
                line = ",".join(txt)
            if "IFCQUANTITYCOUNT" in line:
                line = line.replace("IFCQUANTITYCOUNT", "IFCPROPERTYSINGLEVALUE")
                txt = line.split(",")
                txt[3] = "IFCINTEGER(" +  txt[3].split(".")[0]+ ")"
                txt.pop(1)
                line = ",".join(txt)
            if "IFCELEMENTQUANTITY" in line and 'AllplanQuantities' in line:
                line = line.replace("IFCELEMENTQUANTITY", "IFCPROPERTYSET")
                txt = line.split(",")
                txt.pop(3)
                line = ",".join(txt)
            f2.write(line+");\n")
