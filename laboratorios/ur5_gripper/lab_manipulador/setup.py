from setuptools import setup
setup(name='lab_manipulador', version='1.0.0', packages=['lab_manipulador'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/lab_manipulador']),
                  ('share/lab_manipulador', ['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='Brayan Mateo Bravo Losada', maintainer_email='brayan@example.invalid',
      description='Laboratorio de manipulacion UR5 con pinza', license='Apache-2.0',
      entry_points={'console_scripts': [
          'pick_place = lab_manipulador.pick_place:main',
          'digital_io = lab_manipulador.digital_io:main']})
