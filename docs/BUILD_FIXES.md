# Build fixes 4.7.1

1. Win7 tkinter: multi-path Python38 (Program Files, C:\Python38, py -3.8, official installer)
2. Argos only on Python 3.11; skip 3.8 (spacy has no cp38 wheels)
3. Argos packs only in profiles/argos_packages; pruned to en_fa, fa_en, en_ar, ar_en before NSIS
4. NSIS no longer File /r payload\*.* (avoid double python trees)
5. نصب.txt added
