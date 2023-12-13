# pyIfcLayer
Python scrip for IFC

***pyifclayer.py***

Небольшой скрипт для изменения слоёв элементов в IFC файле на осонве заданных правил. 
layers_rule.csv - Файл с правилами. Первый столбец - имя слой, второй столбец - тип элемента (All - все типы), третий столбец - ID элемента (поддерживаются regexp выражения)
ЗаменаСлоёвIFC.bat - пример bat файла для конвертации содержимого папки, из которой запускается bat

***pyArchIFC2NavisIFC.py***

Перевод Архикада в Навис через IFC


## Renga IFC Compatibility Tool

Convert zones shape representation in IFC file from "Tessellation" to "SweptSolid" to be compatible with Renga.

- [renga_ifc_compat.py](renga_ifc_compat.py)
