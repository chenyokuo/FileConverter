from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
# Core PDF operations need MuPDF, not PyMuPDF 2's optional layout / AI stack.
datas=collect_data_files('pymupdf',excludes=['layout/**','mupdf-devel/**'])
binaries=collect_dynamic_libs('pymupdf')
