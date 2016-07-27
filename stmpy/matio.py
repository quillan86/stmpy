import numpy as np
import scipy
import scipy.io as sio
import sys
import stmpy

def loadmat(filePath):
	'''
Load in all variables from a .mat file.
If you want to list all the variables in the file, use
    >>> fo = sio.loadmat(filename)
    >>> list(fo)

STM_View structures will be stored as dictionaries.
Ignore any variables starting with '__', to avoid __header__, etc...
Return the variables imported in a dictionary.

Useage:
    >>> data_dict = loadmat(filename)
	   '''
	fileObject = sio.loadmat(filePath)
	data = {}
	for x in fileObject:
		if not x.startswith('__'):
			print('Importing ', x)
			mat_raw = fileObject[x]
			try:
				mat = {}
				for key in mat_raw.dtype.names:
					mat[key] = mat_raw[key][0][0]
				data[x] = mat
			except:
				data[x] = mat_raw
		else:
			print('Skip ',x)
	return data

def nvl2mat(nvlfile, matfile):
	'''
Convert an NVL file to a .mat file containing an (almost) STM_View compatible data structure.
Returns the NVL file data in a pymap object.

Useage:
    >>> nvl2mat('infile.NVL', 'outfile.mat')
		'''
	nvl = stmpy.load(nvlfile)		# Load NVL data from file
	pymap_dat = pymap()				# Create a pymap data structure
	pymap_dat.nvl2pymap(nvl)		# Convert from NVL object to pymap object
	pymap_dat.savemat(matfile)		# Save the data in the .mat file
	return pymap_dat
	

class pymap():
	def __init__(self):
		self.ops = []
		print('Created pymap')

	def nvl2pymap(self,nvl):
		'''
Example useage:
    >>> nvl_data = stmpy.load('filename.NVL')
    >>> pymap_data = pymap()
    >>> pymap_data.nvl2pymap(nvl_data)
			'''
		self.map = np.copy(nvl.data)
		self.en = np.copy(nvl.en)
		self.ave = np.copy(nvl.averageSpectrum)
		self.add_op('nvl2pymap')

		# Handle dictionaries properly
		for key in ['info', 'header']:
			tmp = getattr(nvl, key).copy()
			nvlred = {}

			# Get rid of Nonetypes and recarrays
			for ikey in tmp:
				x = tmp[ikey]
				if x is None:
					tmp[ikey] = 'No value'
				elif type(x) is np.recarray:
					tmp[ikey] = 'Recarray deleted in NVL to MAT conversion'
					print(ikey, 'Deleted because of recarray type')
				nvlred[ikey] = tmp[ikey]
			setattr(self, key, nvlred)

		# Additional attributes that are not in NVL file
		self.coord_type = 'r'
		print('Assumed this is in r.  If in k, change coord_type to k')
		self.name = self.info['FILENAME']
		self.var = self.name

		return self
			
	def mat2pymap(self,mhh):
		'''
Example useage:
    >>> rawmat = loadmat('filename.mat')
    >>> mat_data = rawmat['varname']
    >>> pymap_data = pymap()
    >>> pymap_data = mat2pymap(mat_data)
			'''
		for key in mhh:
			if type(mhh[key][0]) is np.str_:
				print(key, ' is a string')
				setattr(self, key, mhh[key][0])
			elif key == 'info':
				self.info = {}
				x = mhh[key]
				for ikey in x.dtype.names:
					self.info[ikey] = x[ikey][0][0][0]
			elif key == 'ops':
				self.ops = []
				x = mhh[key][0]
				for i, obj in enumerate(x):
					self.ops.append(obj[0])
			elif key == 'e':
				self.en = mhh[key]
			else:
				setattr(self, key, mhh[key])

		# Make the energy axis the first index
		# start with [i,j,e]
		self.map = np.swapaxes(self.map, 1, 2)		# [i,e,j]
		self.map = np.swapaxes(self.map, 0, 1)		# [e,i,j]

		return self
	
	def pymap2mat(self):
		'''
Converts data in a pymap object to a dictionary with fields formatted for writing to a .mat file using the scipy.io module.  The pymap object will be (mostly) compatible with STM_View in Matlab.

Conversion:
- strings are nested in an np.array (will be strings in Matlab)
- dictionaries will become structures in Matlab
- lists will become cell arrays in Matlab

Input: pymap data structure.
Output: dictionary which can be written to a matlab file.
			'''
		pydct = vars(self)
		mhh = {}
		for key in pydct:
			obj = pydct[key]

			if type(obj) == np.str_:
				mhh[key] = np.array([obj])
			elif type(obj) == dict:
				mhh[key] = format_mat_struct(obj)
			elif type(obj) == list:
				mhh[key] = format_mat_cell(obj)
			elif key == 'en':
				mhh['e'] = np.copy(obj)
			else:
				mhh[key] = np.copy(obj)
		
		return mhh

	def savemat(self, filename):
		mhh = self.pymap2mat()
		sio.savemat(filename, mhh)
		print('In Matlab, you will need to permute map indeces:')
		print('A.map = permute(A.map, [2,3,1])')

	def add_op(self, new_op_string):
		self.ops.append(new_op_string)

#######################################################################
def format_mat_struct(matred):
# Input: dictionary of strings and arrays
# Output: .mat structure format
    # First make get the dtype list
    dtype_ar = []
    
    for ikey in matred:
        dtype_ar.append((ikey, np.object))
        
    # Want a np.ndarray of size (1,1)
    matstruct = np.ndarray(shape=(1,1), dtype=dtype_ar)
    
    for i,entry in enumerate(dtype_ar):
        ikey = entry[0]     # key for the dictionary
        # print('format_mat_struct: ', i, ikey, entry)
        x = np.copy(matred[ikey])
        matstruct[0,0][ikey] = [x]
    
    return matstruct

def format_mat_cell(matred):
# Input: list of objects
# Outupt: .mat file format for cell array
    sz = len(matred)
    matcell = np.ndarray(shape=(1,sz),dtype=np.object)
    
    for i,obj in enumerate(matred):
        x = np.copy(matred[i])
        matcell[0][i] = np.array([x])
        
    return matcell