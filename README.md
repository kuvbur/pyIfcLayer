# pyIfcLayer
Python scrip for IFC

***pyifclayer.py***

Небольшой скрипт для изменения слоёв элементов в IFC файле на осонве заданных правил. 
layers_rule.csv - Файл с правилами. Первый столбец - имя слой, второй столбец - тип элемента (All - все типы), третий столбец - ID элемента (поддерживаются regexp выражения)
ЗаменаСлоёвIFC.bat - пример bat файла для конвертации содержимого папки, из которой запускается bat

***pyArchIFC2NavisIFC.py***

Перевод Архикада в Навис через IFC

***geonics.py***

Обрабатывает IFC файлы, полученные из NanoCAD GeoniCS. Переводит IfcSpatialZone в IfcCivilElement, связывая их с IfcSite. Обработка ведётся дл всех файлов IFC в папке со скриптом, обработанные файлы сохраняются с суффиксом _clean

## Renga IFC Compatibility Tool

Convert zones shape representation in IFC file from "Tessellation" to "SweptSolid" to be compatible with Renga.

- [renga_ifc_compat.py](renga_ifc_compat.py)

### Usage

```sh
./renga_ifc_compat.py input.ifc output.ifc
```

- `input.ifc`
	- input IFC file with "Tessellation" zone shape representation
- `output.ifc`
	- new converted output IFC file with "SweptSolid" zone shape representation
