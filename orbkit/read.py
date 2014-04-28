# -*- coding: iso-8859-1 -*-
'''Module for reading the output files of quantum chemical software. 
'''
'''
orbkit
Gunter Hermann, Vincent Pohl, and Axel Schild

Institut fuer Chemie und Biochemie, Freie Universitaet Berlin, 14195 Berlin, Germany

This file is part of orbkit.

orbkit is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as 
published by the Free Software Foundation, either version 3 of 
the License, or any later version.

orbkit is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public 
License along with orbkit.  If not, see <http://www.gnu.org/licenses/>.
'''

import copy
import numpy

from orbkit.core import l_deg, lquant, orbit
from orbkit.display import display
from orbkit.qcinfo import QCinfo

def main_read(filename,itype='molden',all_mo=False):
  '''Calls the requested read function.
  
  **Parameters:**
  
    filename : str
      Specifies the filename for the input file.
    itype : str, choices={'molden', 'gamess', 'gaussian.log', 'gaussian.fchk'}
      Specifies the type of the input file.
    all_mo : bool, optional
      If True, all molecular orbitals are returned.
  
  **Returns:**
  
  qc (class QCinfo) with attributes geo_spec, geo_info, ao_spec, mo_spec, etot :
        See `Central Variables`_ for details.
  '''
  display('Opened \n\t%s\n' % filename)
  
  itypes = ['molden', 'gamess', 'gaussian.log', 'gaussian.fchk']
  
  # What kind of input file has to be read?
  reader = {'molden': read_molden, 
          'gamess': read_gamess, 
          'gaussian.log': read_gaussian_log, 
          'gaussian.fchk': read_gaussian_fchk}
  display('Loading %s file...' % itype)
  
  # Return required data
  return reader[itype](filename, all_mo=all_mo)
  # main_read 

def read_molden(filename, all_mo=False):
  '''Reads all information desired from a molden file.
  
  **Parameters:**
  
    filename : str
      Specifies the filename for the input file.
    all_mo : bool, optional
      If True, all molecular orbitals are returned.
  
  **Returns:**
  
  qc (class QCinfo) with attributes geo_spec, geo_info, ao_spec, mo_spec, etot :
      See `Central Variables`_ for details.
  '''

  fid    = open(filename,'r')      # Open the file
  flines = fid.readlines()         # Read the WHOLE file into RAM
  fid.close()                      # Close the file
  
  # Is this really a molden file? 
  if not '[Molden Format]\n' in flines:
    display('The input file %s is no valid molden file!\nIt does' +
          ' not contain the keyword: [Molden Format]\nEXIT\n' % filename)
    raise IOError('Not a valid input file')
  
  # Set a counter for the AOs 
  basis_count = 0

  # Declare synonyms for molden keywords 
  synonyms = {'Sym': 'sym',
              'Ene': 'energy',
              'Occup': 'occ_num',
             }
  MO_keys = synonyms.keys()
  
  # Go through the file line by line 
  for il in range(len(flines)):
    line = flines[il]              # The current line as string
    thisline = line.split()        # The current line split into segments
    
    # Check the file for keywords 
    if '[Molden Format]' in line:
      # A new file begins 
      # Initialize the variables 
      qc = QCinfo()
      sec_flag = False             # A Flag specifying the current section 
    elif '_ENERGY=' in line:
      qc.etot = float(thisline[1])
    elif '[Atoms]' in line:
      # The section containing information about 
      # the molecular geometry begins 
      sec_flag = 'geo_info'
      if 'Angs' in line:
        # The length are given in Angstroem 
        # and have to be converted to Bohr radii --
        aa_to_au = 1/0.52917720859
      else:
        # The length are given in Bohr radii 
        aa_to_au = 1.0
    elif '[GTO]' in line:
      # The section containing information about 
      # the atomic orbitals begins 
      sec_flag = 'ao_info'
      bNew = True                  # Indication for start of new AO section
    elif '[MO]' in line:
      # The section containing information about 
      # the molecular orbitals begins 
      sec_flag = 'mo_info'
      bNew = True                  # Indication for start of new MO section
    elif '[STO]' in line:
      # The orbkit does not support Slater type orbitals 
      display('orbkit does not work for STOs!\nEXIT\n');
      raise IOError('Not a valid input file')
    else:
      # Check if we are in a specific section 
      if sec_flag == 'geo_info':
        # Geometry section 
        qc.geo_info.append(thisline[0:3])
        qc.geo_spec.append([float(ii)*aa_to_au for ii in thisline[3:]])
      if sec_flag == 'ao_info':
        # Atomic orbital section 
        if thisline == []:
          # There is a blank line after every AO 
          bNew = True
        elif bNew:
          # The following AOs are for which atom? 
          bNew = False
          at_num = int(thisline[0]) - 1
          ao_num = 0
        elif len(thisline) == 3:
          # AO information section 
          # Initialize a new dict for this AO 
          ao_num = 0               # Initialize number of atomic orbiatls 
          ao_type = thisline[0]    # Which type of atomic orbital do we have
          pnum = int(thisline[1])  # Number of primatives
          # Calculate the degeneracy of this AO and increase basis_count 
          basis_count += l_deg(lquant[ao_type])
          qc.ao_spec.append({'atom': at_num,
                             'type': ao_type,
                             'pnum': pnum,
                             'coeffs': numpy.zeros((pnum, 2))
                          })
        else:
          # Append the AO coefficients 
          coeffs = numpy.array(line.replace('D','e').split(), dtype=numpy.float64)
          qc.ao_spec[-1]['coeffs'][ao_num,:] = coeffs
          ao_num += 1
      if sec_flag == 'mo_info':
        # Molecular orbital section 
        if '=' in line:
          # MO information section 
          if bNew:
            # Create a numpy array for the MO coefficients and 
            # for backward compability create a simple counter for 'sym'
            qc.mo_spec.append({'coeffs': numpy.zeros(basis_count),
                               'sym': '%d.1' % (len(qc.mo_spec)+1)})
            bNew = False
          # Append information to dict of this MO 
          info = line.replace('\n','').replace(' ','')
          info = info.split('=')
          if info[0] in MO_keys: 
            if info[0] != 'Sym':
              info[1] = float(info[1])
            elif not '.' in info[1]:
              from re import search
              a = search(r'\d+', info[1]).group()
              if a == info[1]:
                info[1] = '%s.1' % a
              else:
                info[1] = info[1].replace(a, '%s.' % a)
            qc.mo_spec[-1][synonyms[info[0]]] = info[1]
        else:
          if ('[' or ']') in line:
            # start of another section that is not (yet) read
            sec_flag = None
          else:
            # Append the MO coefficients 
            bNew = True            # Reset bNew
            index = int(thisline[0])-1
            try: 
              # Try to convert coefficient to float 
              qc.mo_spec[-1]['coeffs'][index] = float(thisline[1])
            except ValueError:
              # If it cannot be converted print error message 
              display('Error in coefficient %d of MO %s!' % (index, 
                qc.mo_spec[-1]['sym']) + '\nSetting this coefficient to zero...')
  
  # Are all MOs requested for the calculation? 
  if not all_mo:
    mo_range   = copy.deepcopy(qc.mo_spec)
    qc.mo_spec = []
    for ii_mo in mo_range:
      if ii_mo['occ_num'] > 0.0000001:
        qc.mo_spec.append(ii_mo)
  
  return qc
  # read_molden 

def read_gamess(filename, all_mo=False):
  '''Reads all information desired from a Gamess-US output file.
  
  **Parameters:**
  
    filename : str
      Specifies the filename for the input file.
    all_mo :   bool, optional
      If True, all molecular orbitals are returned.
  
  **Returns:**
  
  qc (class QCinfo) with attributes geo_spec, geo_info, ao_spec, mo_spec, etot :
      See `Central Variables`_ for details.
  '''
  
  # Initialize the variables 
  qc = QCinfo()
  occ = []
  AO = []
  sec_flag = False                 # A Flag specifying the current section
  element_list = {}
  element_count = 0
  geo_skip = 0
  ao_skip = 0
  basis_count = 0
  blast = False

  # Go through the file line by line 
  with open(filename) as fileobject:
    for line in fileobject:
      thisline = line.split()      # The current line split into segments
      # Check the file for keywords 
      if ' ATOM      ATOMIC                      COORDINATES' in line:
        # The section containing information about 
        # the molecular geometry begins 
        sec_flag = 'geo_info'
        geo_skip = 1
        atom_count = 1
        if '(BOHR)' in line:
          # The length are given in Angstroem 
          # and have to be converted to Bohr radii 
          aa_to_au = 1.0
        else:
          # The length are given in Bohr radii 
          aa_to_au = 1/0.52917720859
      
      elif 'ATOMIC BASIS SET' in line:
        # The section containing information about 
        # the atomic orbitals begins 
        sec_flag = 'ao_info'
        ao_skip = 6
        at_type = []
      elif '          EIGENVECTORS' in line:
        # The section containing information about 
        # the molecular orbitals begins 
        sec_flag = 'mo_info'
        mo_skip = 1
        init_mo = False             # Initialize new MO section
        mo_new = False              # Indication for start of new MO section
        ene = False
        len_mo = 0
      elif 'CIS TRANSITION DIPOLE MOMENTS AND' in line:
        # Section containing transition dipole momemts and expectation values
        # of dipole moments begins (CIS calculation)
        sec_flag = 'tdm_info'
        tdm_flag = None
      elif 'NUMBER OF STATES REQUESTED' in line:
        # get the number of states for the transition dipole moment information
        tdm_nstates = int(line.split('=')[1])
        tdm_state_dipole = None
      elif 'SPIN MULTIPLICITY' in line:
        # odd way to get gound state multiplicity
        gs_multi = int(line.split()[3])
      elif 'FINAL' in line:
        # get (last) energy
        qc.etot = float(line.split()[4])
      elif ' NUMBER OF OCCUPIED ORBITALS (ALPHA)          =' in line:
        occ.append(int(thisline[-1]))
      elif ' NUMBER OF OCCUPIED ORBITALS (BETA )          =' in line:
        occ.append(int(thisline[-1]))
      elif '          ECP POTENTIALS' in line:
        occ = []
      elif ' NUMBER OF OCCUPIED ORBITALS (ALPHA) KEPT IS    =' in line:
        occ.append(int(thisline[-1]))
      elif ' NUMBER OF OCCUPIED ORBITALS (BETA ) KEPT IS    =' in line:
        occ.append(int(thisline[-1]))
      else:
        # Check if we are in a specific section 
        if sec_flag == 'geo_info':
          if not geo_skip:
            if line == '\n':
              sec_flag = None
              a = numpy.array(qc.geo_info)
            else:
              qc.geo_info.append([thisline[0],atom_count,thisline[1]])
              qc.geo_spec.append([float(ii)*aa_to_au for ii in thisline[2:]])
              atom_count += 1
          elif geo_skip:
            geo_skip -= 1
        
        if sec_flag == 'ao_info':
          if not ao_skip:
            if ' TOTAL NUMBER OF BASIS SET SHELLS' in line:
              sec_flag = None
            else:
              if len(thisline) == 1:
                # Read atom type 
                at_type = thisline[0]
                AO.append([])
                new_ao = False
              elif len(thisline) == 0 and new_ao == False:
                new_ao = True
              else:
                coeffs = [float(ii) for ii in thisline[3:]]
                if new_ao:
                  ao_type = thisline[1].lower().replace('l','sp')
                  for i_ao,t_ao in enumerate(ao_type):
                    AO[-1].append({'atom_type': at_type,
                                  'type': t_ao,
                                  'pnum': 1,
                                  'coeffs': [[coeffs[0],coeffs[1+i_ao]]]})
                  new_ao = False
                else:
                  for i_ao in range(len(ao_type)):
                    AO[-1][-len(ao_type)+i_ao]['coeffs'].append([coeffs[0],
                                                                coeffs[1+i_ao]])
                    AO[-1][-len(ao_type)+i_ao]['pnum'] += 1
          elif ao_skip:
            ao_skip -= 1
        if sec_flag == 'mo_info':
          if not mo_skip:
            if '...... END OF RHF CALCULATION ......' in line:
              sec_flag = None
            else:
              if thisline == []:
                if blast:
                  sec_flag = None
                  blast = False
                blast = True
                init_mo = True
                mo_new = False
                ene = False
              elif init_mo and not mo_new:
                init_len = len(thisline)
                for ii in range(len(thisline)):
                  #len_mo += 1
                  qc.mo_spec.append({'coeffs': [],
                                  'energy': 0.0,
                                  'occ_num': 0.0,
                                  'sym': ''
                                  })
                init_mo = False
                mo_new = True
                blast = False
              elif len(thisline) == init_len and ene == False:
                for ii in range(init_len,0,-1):
                  qc.mo_spec[-ii]['energy'] = float(thisline[init_len-ii])
                ene = True
              elif len(thisline) == init_len and ene == True:
                for ii in range(init_len,0,-1):
                  len_mo += 1
                  qc.mo_spec[-ii]['sym'] = '%d.%s' % (len_mo-1, thisline[init_len-ii])
              elif thisline != [] and not init_mo and mo_new:
                for ii in range(init_len,0,-1):
                  qc.mo_spec[-ii]['coeffs'].append(float(line[16:].split()[init_len-ii]))
          elif mo_skip:
            mo_skip -= 1
        if sec_flag == 'tdm_info':
          # instead of giving the output in a useful human and machine readable 
          # way, gamess output syntax differs for transitions involving the 
          # ground state compared to transitions between excited states...
          if tdm_state_dipole == None:
            # initialize variables
            tdm_state_dipole = numpy.zeros((tdm_nstates+1,3))
            tdm_state_multiplicity = numpy.zeros(tdm_nstates+1)
            tdm_state_energy = numpy.zeros(tdm_nstates+1)
            tdm_tdm = numpy.zeros((tdm_nstates,tdm_nstates+1,3))
          if 'GROUND STATE (SCF) DIPOLE=' in line:
            line_dummy = line.split()
            # ground state dipole is in debye...convert to atomic units
            tdm_state_dipole[0,:] = numpy.multiply( 
                                    [float(line_dummy[4]),
                                     float(line_dummy[5]),
                                     float(line_dummy[6])],0.393430307)

          if 'EXPECTATION VALUE DIPOLE MOMENT FOR EXCITED STATE' in line:
            tdm_state = int(line.split('STATE')[1])
            tdm_flag = 'state_info'
          if 'TRANSITION FROM THE GROUND STATE TO EXCITED STATE' in line:
            tdm_trans_states = [0, int(line.split('EXCITED STATE')[1])]
            tdm_flag = 'transition_info'
          if 'TRANSITION BETWEEN EXCITED STATES' in line:
            line_dummy = line.split('STATES')[1]
            tdm_trans_states = [int(line_dummy.split('AND')[0]), 
                                int(line_dummy.split('AND')[1])]
            tdm_flag = 'transition_info'
          if 'CIS NATURAL ORBITAL OCCUPATION NUMBERS FOR EXCITED STATE' in line:
            sec_flag = None
            tdm_flag = None
          if tdm_flag == 'state_info':
            if 'STATE MULTIPLICITY' in line:
              tdm_state_multiplicity[tdm_state] = int(line.split('=')[1])
            if 'STATE ENERGY' in line:
              tdm_state_energy[tdm_state] = float(line.split('=')[1])
            if 'STATE DIPOLE' and 'E*BOHR' in line:
              line_dummy = line.split()
              tdm_state_dipole[tdm_state,:] = [float(line_dummy[3]),
                                               float(line_dummy[4]),
                                               float(line_dummy[5])]
          elif tdm_flag == 'transition_info':
            if 'TRANSITION DIPOLE' and 'E*BOHR' in line:
              line_dummy = line.split()
              tdm_tdm[tdm_trans_states[0],tdm_trans_states[1],:] = \
                                 [float(line_dummy[3]),
                                  float(line_dummy[4]),
                                  float(line_dummy[5])]
         
  # Check usage of same atomic basis sets 
  basis_set = {}
  for ii in range(len(AO)):
    if not AO[ii][0]['atom_type'] in basis_set.keys():
      basis_set[AO[ii][0]['atom_type']] = AO[ii]
    else:
      for jj in range(len(AO[ii])):
        if AO[ii][jj]['coeffs'] !=  basis_set[AO[ii][0]['atom_type']][jj]['coeffs']:
          raise IOError('Different basis sets for the same atom.')
  # Numpy array 
  for ii in basis_set.iterkeys():
    for jj in range(len(basis_set[ii])):
      basis_set[ii][jj]['coeffs'] = numpy.array(basis_set[ii][jj]['coeffs'])

  for kk in range(len(qc.mo_spec)):
    qc.mo_spec[kk]['coeffs'] = numpy.array(qc.mo_spec[kk]['coeffs'])

  # Complement atomic basis sets 
  for kk in range(len(qc.geo_info)):
    for ll in range(len(basis_set[qc.geo_info[kk][0]])):
      qc.ao_spec.append({'atom': qc.geo_info[kk][1]-1,
                         'type': basis_set[qc.geo_info[kk][0]][ll]['type'],
                         'pnum': basis_set[qc.geo_info[kk][0]][ll]['pnum'],
                         'coeffs': basis_set[qc.geo_info[kk][0]][ll]['coeffs']
                         })

  for ii in range(len(qc.mo_spec)):
    if occ[0] and occ[1]:
      qc.mo_spec[ii]['occ_num'] += 2.0
      occ[0] -= 1
      occ[1] -= 1
    if not occ[0] and occ[1]:
      qc.mo_spec[ii]['occ_num'] += 1.0
      occ[1] -= 1
      print 'occ_1'
    if not occ[1] and occ[0]:
      print 'occ_0'
      qc.mo_spec[ii]['occ_num'] += 1.0
      occ[0] -= 1
  
  # save results from a CIS calculation to qc
  tdm_state_energy[0]           = qc.etot
  tdm_state_multiplicity[0]     = gs_multi
  qc.tdm_states['multiplicity'] = tdm_state_multiplicity
  qc.tdm_states['energy']       = tdm_state_energy
  qc.tdm_states['dipole']       = tdm_state_dipole
  qc.tdm_transitions['dipole']  = tdm_tdm
  
  return qc
  # read_gamess 

def read_gaussian_fchk(filename, all_mo=False):
  '''Reads all information desired from a Gaussian FChk file. 

  **Parameters:**
  
    filename : str
      Specifies the filename for the input file.
    all_mo : bool, optional
      If True, all molecular orbitals are returned.
  
  **Returns:**
  
  qc (class QCinfo) with attributes geo_spec, geo_info, ao_spec, mo_spec, etot :
      See `Central Variables`_ for details.
  '''

  fid    = open(filename,'r')   # Open the file
  flines = fid.readlines()      # Read the WHOLE file into RAM
  fid.close()                   # Close the file
  
  sec_flag = None
  
  el_num = [0,0]
  index = 0
  at_num = 0
  ao_num = 0 
  switch = 0
  qc = QCinfo()
  count_mo = 0
  
  # Set a counter for the AOs 
  basis_count = 0
  
  # Go through the file line by line 
  for il in range(len(flines)):
    line = flines[il]         # The current line as string
    thisline = line.split()   # The current line split into segments
    
    # Check the file for keywords 
    if 'Number of alpha electrons' in line:
      el_num[0] = int(thisline[5]) 
    elif 'Number of beta electrons' in line:
      el_num[1] = int(thisline[5])
    #elif 'Number of basis functions' in line:
      #basis_count = int(thisline[5])
    elif 'Atomic numbers'  in line:
      sec_flag = 'geo_info'
      index = 0
      at_num = int(thisline[-1])
      count = 0
      if qc.geo_info == []:
        for ii in range(at_num):
          qc.geo_info.append(['',ii,''])
    elif 'Integer atomic weights' in line:
      sec_flag = 'geo_info'
      index = 2
      at_num = int(thisline[-1])
      count = 0
      if qc.geo_info == []:
        for ii in range(at_num):
          qc.geo_info.append(['',ii,''])
    elif 'Total Energy' in line:
      qc.etot = float(thisline[3])
    elif 'Current cartesian coordinates' in line:
      at_num = int(thisline[-1])/3
      sec_flag = 'geo_pos'
      qc.geo_spec = []
      count = 0
      xyz = []
    elif 'Shell types' in line:
      sec_flag = 'ao_info'
      index = 'type'
      ao_num = int(thisline[-1])
      count = 0
      if qc.ao_spec == []:
        for ii in range(ao_num):
          qc.ao_spec.append({})
    elif 'Number of primitives per shell' in line:
      sec_flag = 'ao_info'
      index = 'pnum'
      ao_num = int(thisline[-1])
      count = 0
      if qc.ao_spec == []:
        for ii in range(ao_num):
          qc.ao_spec.append({})
    elif 'Shell to atom map' in line:
      sec_flag = 'ao_info'
      index = 'atom'
      ao_num = int(thisline[-1])
      count = 0
      if qc.ao_spec == []:
        for ii in range(ao_num):
          qc.ao_spec.append({})
    elif 'Primitive exponents' in line:
      sec_flag = 'ao_coeffs'
      ao_num = int(thisline[-1])
      count = 0
      switch = 0
      index = 0
      if qc.ao_spec == []:
        raise IOError('Shell types need to be defined before the AO exponents!')
      if not 'coeffs' in qc.ao_spec[0].keys():
        for ii in range(len(qc.ao_spec)):
          pnum = qc.ao_spec[ii]['pnum']
          qc.ao_spec[ii]['coeffs'] = numpy.zeros((pnum, 2))
    elif 'Contraction coefficients' in line:
      sec_flag = 'ao_coeffs'
      ao_num = int(thisline[-1])
      count = 0
      switch = 1
      index = 0
      if qc.ao_spec == []:
        raise IOError('Shell types need to be defined before the AO exponents!')
      if not 'coeffs' in qc.ao_spec[0].keys():
        for ii in range(len(qc.ao_spec)):
          pnum = qc.ao_spec[ii]['pnum']
          qc.ao_spec[ii]['coeffs'] = numpy.zeros((pnum, 2))
    elif 'Orbital Energies' in line:
      sec_flag = 'mo_eorb'
      mo_num = int(thisline[-1])
      index = 0
      count = len(qc.mo_spec)
      if el_num[0] == el_num[1]:
        i = el_num[0]
        occ = 2
      else:
        i = el_num[0 if 'Alpha' in line else 1]
        occ = 1
      for ii in range(mo_num):
        qc.mo_spec.append({'coeffs': numpy.zeros(basis_count),
                        'energy': 0.0,
                        'occ_num': float(occ if ii < i else 0)
                        })
        qc.mo_spec[-1]['sym'] = '%i.1' % len(qc.mo_spec)
    elif 'MO coefficients' in line:
      sec_flag = 'mo_coeffs'
      count = 0
      mo_num = int(thisline[-1])
    else:
      # Check if we are in a specific section 
      if sec_flag == 'geo_info':
        for ii in thisline:
          qc.geo_info[count][index] = ii
          count += 1
          if count == at_num:
            sec_flag = None
      elif sec_flag == 'geo_pos':
        for ii in thisline:
          xyz.append(float(ii))
          if len(xyz) == 3:
            qc.geo_spec.append(xyz)
            xyz = []
            count += 1
            if count == at_num:
              sec_flag = None
      elif sec_flag == 'ao_info':
        for ii in thisline:
          ii = int(ii)
          if index is 'type':
            ii = orbit[abs(ii)]
            basis_count += l_deg(lquant[ii])
          elif index is 'atom':
            ii -= 1
          qc.ao_spec[count][index] = ii
          count += 1
          if count == ao_num:
            sec_flag = None
      elif sec_flag == 'ao_coeffs':
        for ii in thisline:
          qc.ao_spec[index]['coeffs'][count,switch] = float(ii)
          count += 1
          ao_num -= 1
          if count == qc.ao_spec[index]['pnum']:
            index += 1
            count = 0
        if not ao_num:
          sec_flag = None
      elif sec_flag == 'mo_eorb':
        for ii in thisline:
          qc.mo_spec[count]['energy'] = float(ii)
          count += 1
          if index != 0 and not count % basis_count:
            sec_flag = None
      elif sec_flag == 'mo_coeffs':
        for ii in thisline:
          qc.mo_spec[index]['coeffs'][count] = float(ii)
          count += 1
          if count == basis_count:
            count = 0
            index += 1
          if index != 0 and not index % basis_count:
            sec_flag = None
  
  # Are all MOs requested for the calculation? 
  if not all_mo:
    mo_range = copy.deepcopy(qc.mo_spec)
    qc.mo_spec = []
    for ii_mo in mo_range:
      if ii_mo['occ_num'] > 0.0000001:
        qc.mo_spec.append(ii_mo)
  
  return qc
  # read_gaussian_fchk 

def read_gaussian_log(filename,all_mo=False,orientation='standard',
                      i_geo=-1,i_ao=-1,i_mo=-1,interactive=True):
  '''Reads all information desired from a Gaussian .log file.

  **Parameters:**
  
    filename : str
      Specifies the filename for the input file.
    all_mo :  bool, optional
      If True, all molecular orbitals are returned.
    orientation : string, choices={'input', 'standard'}, optional
      Specifies orientation of the molecule in Gaussian nomenclature. [#first]_ 
    i_geo : int, default=-1
      Selects the geometry section of the output file.
    i_ao : int, default=-1
      Selects the atomic orbital section of the output file.
    i_mo : int, default=-1
      Selects the molecular orbital section of the output file.
    interactive : bool
      If True, the user is asked to select the different sets.
  
  **Returns:**
  
  qc (class QCinfo) with attributes geo_spec, geo_info, ao_spec, mo_spec, etot :
      See `Central Variables`_ for details.

.. [#first] Attention: The MOs in the output are only valid for the standard orientation!

  '''
  
  fid    = open(filename,'r')      # Open the file
  flines = fid.readlines()         # Read the WHOLE file into RAM
  fid.close()                      # Close the file
  
  # Search the file the specific sections
  count = {'geometry': 0, 'geometry_input': 0, 'atomic orbitals': 0, 
           'molecular orbitals': [], 'state': []}

  def check_sel(count,i,interactive=False):
    if count == 0:
      raise IndexError
    elif count == 1:
      return 0
    message = '\tPlease give an integer from 0 to %d: ' % (count-1)
    
    try:
      if interactive:
        i = int(raw_input(message))
      i = range(count)[i]
    except (IndexError,ValueError):
      raise IOError(message.replace(':','!'))
    else:
      display('\tSelecting the %s' %
              ('last element.' if (i == count-1) else 'element %d.' % i))
    return i
  
  # Go through the file line by line 
  for il in range(len(flines)):
      line = flines[il]            # The current line as string
      thisline = line.split()      # The current line split into segments
      
      # Check the file for keywords 
      if ' orientation:' in line:
        if '%s orientation:' % orientation in line.lower():
          count['geometry'] += 1
        if 'input orientation:' in line.lower():
          count['geometry_input'] += 1
      elif 'Standard basis:' in line or 'General basis read from cards:' in line:
        # Check if a cartesian basis has been applied
        if '(6D, 10F)' not in line:
          raise IOError('Please apply a Cartesian Gaussian Basis Sets (6D, 10F)!')
      elif 'AO basis set' in line:
        count['atomic orbitals'] += 1
      elif 'The electronic state is ' in line:
        count['state'].append(thisline[-1][:-1])
      elif 'Orbital Coefficients:' in line:
        mo_type = thisline[0]
        if mo_type != 'Beta':
          count['molecular orbitals'].append(mo_type)
        else:
          count['molecular orbitals'][-1] = 'Alpha&Beta'
 
  display('\nContent of the GAUSSIAN .log file:')
  display('\tFound %d geometry section(s). (%s orientation)' % 
          (count['geometry'], orientation))
  try:
    i_geo = check_sel(count['geometry'],i_geo,interactive=interactive)
  except IndexError:
    count['geometry'] = count['geometry_input']
    orientation = 'input'
    display('\Looking for "Input orientation": \n' + 
            '\tFound %d geometry section(s). (%s orientation)' % 
            (count['geometry'], orientation))
    try:
      i_geo = check_sel(count['geometry'],i_geo,interactive=interactive)
    except IndexError:
      raise IOError('Found no geometry section!'+
                    ' Are you sure this is a GAUSSIAN .log file?')
    
  
  try:
    display('\tFound %d atomic orbitals section(s).' % count['atomic orbitals'])
    i_ao = check_sel(count['atomic orbitals'],i_ao,interactive=interactive)
  except IndexError:
    raise IOError('Write GFINPUT in your GAUSSIAN route section to print' + 
                  ' the basis set information!')
  
  try:
    display('\tFound the following %d molecular orbitals section(s):' % 
            len(count['molecular orbitals']))
  except IndexError:
    raise IOError('Write IOP(6/7=3) in your GAUSSIAN route section to print\n' + 
                  ' all molecular orbitals!')
  for i,j in enumerate(count['molecular orbitals']):
    string = '\t\tSection %d: %s Orbitals'% (i,j)
    try:
      string += ' (electronic state: %s)' % count['state'][i]
    except IndexError:
      pass
    display(string)
  i_mo = check_sel(len(count['molecular orbitals']),i_mo,interactive=interactive)
  
  aa_to_au = 1/0.52917720859  # conversion factor for Angstroem to bohr radii

  # Set a counter for the AOs 
  basis_count = 0
  
  # Initialize some variables 
  sec_flag = None
  skip = 0
  c_geo = 0
  c_ao = 0
  c_mo = 0
  occ = []
  eigen = []
  orb_sym = []
  qc = QCinfo()
  index = []
  
  # Go through the file line by line 
  for il in range(len(flines)):
    line = flines[il]              # The current line as string
    thisline = line.split()        # The current line split into segments
    
    # Check the file for keywords 
    if '%s orientation:' % orientation in line.lower():
      # The section containing information about 
      # the molecular geometry begins 
      if i_geo == c_geo:
        qc.geo_info = []
        qc.geo_spec = []
        sec_flag = 'geo_info'
      c_geo += 1
      skip = 4
    elif 'Standard basis:' in line:
      # Check if a cartesian basis has been applied
      if '(6D, 10F)' not in line:
        raise IOError('Please apply a Cartesian Gaussian Basis Sets (6D, 10F)!')
    elif 'AO basis set' in line:
      # The section containing information about 
      # the atomic orbitals begins
      if i_ao == c_ao:
        qc.ao_spec = []
        sec_flag = 'ao_info'
      c_ao += 1
      basis_count = 0
      bNew = True                  # Indication for start of new AO section
    elif 'Orbital symmetries:' in line:
        sec_flag = 'mo_sym'
        add = ''
        orb_sym = []
    elif 'Orbital Coefficients:' in line:
      # The section containing information about 
      # the molecular orbitals begins 
      if (i_mo == c_mo):
        sec_flag = 'mo_info'
        mo_type = count['molecular orbitals'][i_mo]
        qc.mo_spec = []
        offset = 0
        add = ''
        if orb_sym == []:
          if 'Alpha' in mo_type:
            add = '(a)'
          orb_sym = ['A1'+add] * basis_count
          if 'Beta' in mo_type:
            add = '(b)'
            orb_sym += ['A1'+add] * basis_count
        for i in range(len(orb_sym)):
          # for numpy version < 1.6 
          c = ((numpy.array(orb_sym[:i+1]) == orb_sym[i]) != 0).sum()
          # for numpy version >= 1.6 this could be used:
          #c = numpy.count_nonzero(numpy.array(orb_sym[:i+1]) == orb_sym[i])
          qc.mo_spec.append({'coeffs': numpy.zeros(basis_count),
                          'energy': 0.,
                          'sym': '%d.%s' % (c,orb_sym[i])})
      if mo_type != 'Beta':
        c_mo += 1
      bNew = True                  # Indication for start of new MO section
    elif 'E(' in line:
      qc.etot = float(line.split('=')[1].split()[0])
    else:
      # Check if we are in a specific section 
      if sec_flag == 'geo_info':
        if not skip:
          qc.geo_info.append([thisline[1],thisline[0],thisline[1]])
          qc.geo_spec.append([aa_to_au*float(ij) for ij in thisline[3:]])
          if '-----------' in flines[il+1]:
            sec_flag = None
        else:
          skip -= 1
      if sec_flag == 'ao_info':
        # Atomic orbital section 
        if ' ****' in line: 
          # There is a line with stars after every AO 
          bNew = True
          # If there is an additional blank line, the AO section is complete
          if flines[il+1].split() == []:
            sec_flag = None
        elif bNew:
          # The following AOs are for which atom? 
          bNew = False
          at_num = int(thisline[0]) - 1
          ao_num = 0
        elif len(thisline) == 4:
          # AO information section 
          # Initialize a new dict for this AO 
          ao_num = 0               # Initialize number of atomic orbiatls 
          ao_type = thisline[0].lower()   # Type of atomic orbital
          pnum = int(thisline[1])  # Number of primatives
          for i_ao in ao_type:
            # Calculate the degeneracy of this AO and increase basis_count 
            basis_count += l_deg(lquant[i_ao])
            qc.ao_spec.append({'atom': at_num,
                            'type': i_ao,
                            'pnum': pnum,
                            'coeffs': numpy.zeros((pnum, 2))
                            })
        else:
          # Append the AO coefficients 
          coeffs = numpy.array(line.replace('D','e').split(), dtype=numpy.float64)
          for i_ao in range(len(ao_type)):
            qc.ao_spec[-len(ao_type)+i_ao]['coeffs'][ao_num,:] = [coeffs[0],
                                                               coeffs[1+i_ao]]
          ao_num += 1
      if sec_flag == 'mo_sym':
        if 'The electronic state is' in line:
          sec_flag = None
        else:
          info = line[18:].replace('(','').replace(')','').split()
          if 'Alpha' in line:
            add = '(a)'
          elif 'Beta' in line:
            add = '(b)'
          for i in info:
            orb_sym.append(i + add)   
      if sec_flag == 'mo_info':
        # Molecular orbital section 
        info = line[:21].split()
        coeffs = line[21:].split()
        if info == []:
          if bNew:
            index = [offset+i for i in range(len(coeffs))]
            bNew = False
          else:
            for i,j in enumerate(index):
              qc.mo_spec[j]['occ_num'] = int('O' in coeffs[i])
              if mo_type not in 'Alpha&Beta':
                qc.mo_spec[j]['occ_num'] *= 2
        elif 'Eigenvalues' in info:
          if mo_type == 'Natural':
            key = 'occ_num'
          else:
            key = 'energy'
          for i,j in enumerate(index):
            qc.mo_spec[j][key] = float(coeffs[i])
        else:
          for i,j in enumerate(index):
            qc.mo_spec[j]['coeffs'][int(info[0])-1] = float(coeffs[i])
          if int(info[0]) == basis_count:
            bNew = True
            offset = index[-1]+1
            if index[-1]+1 == len(orb_sym):
              sec_flag = None
              orb_sym = []
  
  # Are all MOs requested for the calculation? 
  if not all_mo:
    mo_range = copy.deepcopy(qc.mo_spec)
    qc.mo_spec = []
    for ii_mo in mo_range:
      if ii_mo['occ_num'] > 0.0000001:
        qc.mo_spec.append(ii_mo)
  
  return qc
  # read_gaussian_log 
