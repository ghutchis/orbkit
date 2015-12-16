# -*- coding: iso-8859-1 -*-
'''
This file is part of orbkit. See the main program or documentation 
for information on the license.

Example file that shows how to use orbkit for ordering molecular orbitals
using analytical integrals for the bending of a CO2 molecule.

Please note that the input files are compressed in .tar.gz file and
need to be decompressed.
'''
import os,copy
from time import time
from orbkit import multiple_files as mult
from orbkit.display import init_display,display,tForm
import numpy

t = [time()]

# Create a list containing the filenames of the input files
path = 'pec_co2'
if not os.path.exists(path):
  raise IOError('%s does not exist! Please extract pec_co2.tar.gz' % path)

# The bond angle
oco = numpy.arange(170,191,2)
# How are input files formatted?
fid = '%d.molden'
fid_list = []
for i in range(1,len(oco)+1):
  f = os.path.join(path,fid % i)
  if not os.path.exists(f):
    raise IOError('%s does not exist!' % f)
  fid_list.append(f)

# Read all input files
mult.read(fid_list,itype='molden')

# Save the unordered molecular orbital coefficients for depiction
mo_before = copy.deepcopy(mult.mo_coeff_all)


# Run the ordering routine using analytical overlap integrals
# Input argument None has been used because input files have been read already
index_list, mo_overlap = mult.order_using_analytical_overlap(None)


import pylab as plt

mo = mo_before[0]
for j in range(mo.shape[2]):
  plt.plot(oco,mo[:,11,j], '-', color=(0.7,0.7,0.7))

mo = mult.mo_coeff_all[0]
for j in range(mo.shape[2]):
  plt.plot(oco,mo[:,11,j], '--',color=(0.7,0.7,0.7))

plt.plot(oco,mo_before[0][:,11,5], 'b-', label='before ordering')
plt.plot(oco,mo[:,11,5], 'b--', label='after ordering')

plt.xlabel(r'$\sphericalangle{\rm OCO}\,({}^{\circ})$')
plt.ylabel(r'$C_{ia}$')
plt.legend()
plt.show()