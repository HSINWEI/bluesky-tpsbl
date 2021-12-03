import tempfile
from pathlib import Path
import os
from datetime import datetime
import databroker

def get_catalog(name, msgpack_dir=None):
    if msgpack_dir is None:
        home = str(Path.home())
        archive_root = os.path.join(home, 'data_temp')
        date_str = datetime.now().strftime('%Y%m%d')
        msgpack_dir = os.path.join(archive_root, date_str)

    cat_name = f'{name}_temp'

    path = tempfile.mkdtemp()
    catalog_file = os.path.join(path, f'{cat_name}.yaml')
    with open(catalog_file, 'w') as f:
        f.write(f'''
    sources:
      {cat_name}:
        description: Some imaginary beamline
        driver: "bluesky-msgpack-catalog"
        container: catalog
        args:
          paths: {msgpack_dir}/*.msgpack
        metadata:
          beamline: "TPS Beamline"

        ''')

    combo_catalog_path = databroker.catalog._catalogs[-1].path
    if all(cat_name not in cat for cat in  databroker.catalog._catalogs[-1].path):
        combo_catalog_path.append(catalog_file)
        databroker.catalog.force_reload()

    catalog = databroker.catalog[cat_name]
    return catalog
