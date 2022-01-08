# bubble-creator2
Creates a compilable LaTeX file from exported Telegram chat data.

**Usage:** 

bubblecreator.py [-h] [-a A] source target

* source = Directory where the result.json file from the exported data is located.
* target = Directory where the LaTeX files will be created. Will be created if not existing.
* -a = If set, causes the application to run pdflatex on the created files.