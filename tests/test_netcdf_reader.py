import unittest
from uptide.netcdf_reader import NetCDFGrid, CoordinateError, NetCDFFile
import itertools
import os
from numpy import arange, array, ones

# function used to fill the netcdf field, has to be linear
def f(lat, lon):
  return lat*10 + lon

test_file_name1='tests/test_netcdf_reader1.nc'
test_file_name2='tests/test_netcdf_reader2.nc'

class TestNetCDFGrid(unittest.TestCase):
  """Tests the uptide.netcdf.NetCDFGrid class"""
  def setUp(self):
    # it seems that many scipy installations are broken for
    # netcdf writing - therefore simply committing the
    # test files instead of writing them out on the fly here
    return
    zval = array(
        [[f(lat,lon) for lon in arange(10.0)]
                     for lat in arange(10.0)])
    nc = NetCDFFile(test_file_name1, 'w')
    nc.createDimension('lat', 10)
    nc.createDimension('lon', 10)
    nc.createVariable('latitude', 'float64', ('lat',))
    nc.createVariable('longitude', 'float64', ('lon',))
    nc.variables['latitude'][:] = arange(10.0)
    nc.variables['longitude'][:] = arange(10.0)
    nc.createVariable('z', 'float64', ('lat','lon'))
    nc.variables['z'][:,:] = zval
    nc.createVariable('mask', 'float64', ('lat','lon'))
    mask = ones((10,10),dtype='float64')
    mask[3:,:] = 0.0
    nc.variables['mask'][:,:] = mask
    nc.createVariable('transposed_mask', 'float64', ('lon','lat'))
    nc.variables['transposed_mask'][:,:] = mask.T
    nc.close()
    # same thing but without the coordinate fields and mask
    nc = NetCDFFile(test_file_name2, 'w')
    nc.createDimension('lat', 10)
    nc.createDimension('lon', 10)
    nc.createVariable('z', 'float64', ('lat','lon'))
    nc.variables['z'][:,:] = zval
    nc.close()

  def tearDown(self):
    # don't remove them either (see above) 
    return
    os.remove(test_file_name1)
    os.remove(test_file_name2)
    pass

  def _test_prepared_ncg(self, ncg, perm, coordinate_perm):
    interpolator = ncg.get_interpolator(field_name='z')
    # first the tests common to all permutations
    # point that is always inside:
    xy = [[4.33, 5.2][i] for i in coordinate_perm]
    self.assertAlmostEqual(interpolator.get_val(xy), f(4.33, 5.2))
    # point outside the domain, should raise exception:
    xy = [[-4.95, 8.3][i] for i in coordinate_perm]
    self.assertRaises(CoordinateError, interpolator.get_val, xy)

    if set(perm).intersection(('mask','transposed_mask','mask_from_fill_value')):
      # point between row of land and of sea points, should extrapolate from nearest sea row:
      xy = [[1.2, 8.3][i] for i in coordinate_perm]
      self.assertAlmostEqual(interpolator.get_val(xy), f(3.0,8.3))
      # point inside the first two land rows, should raise exception
      xy = [[0.95, 8.3][i] for i in coordinate_perm]
      self.assertRaises(CoordinateError, interpolator.get_val, xy)
    if 'ranges' in perm:
      # test within the range
      xy = [[3.0, 7.0][i] for i in coordinate_perm]
      self.assertAlmostEqual(interpolator.get_val(xy), f(3.0,7.))
      # tests outside the range, should raise exception
      xy = [[3.2, 0.9][i] for i in coordinate_perm]
      self.assertRaises(CoordinateError, interpolator.get_val, xy)
      xy = [[5.9, 9.0][i] for i in coordinate_perm]
      self.assertRaises(CoordinateError, interpolator.get_val, xy)

  # test a specific permutation of the calling sequence set_mask, set_ranges
  # and specific coordinate_perm (lat,lon) or (lon,lat)
  def _test_permutation(self, perm, coordinate_perm):
    # load the netcdf created in setup()
    if coordinate_perm==(0,1):
      ncg = NetCDFGrid(test_file_name1, ('lat', 'lon'), ('latitude', 'longitude'))
    else:
      ncg = NetCDFGrid(test_file_name1, ('lon', 'lat'), ('longitude', 'latitude'))
    # call the methods in the order given by perm
    for x in perm:
      if x=='mask':
        ncg.set_mask('mask')
      elif x=='transposed_mask':
        ncg.set_mask('transposed_mask')
      elif x=='mask_from_fill_value':
        ncg.set_mask_from_fill_value('mask', 1.0)
      elif x=='ranges':
        if coordinate_perm==(0,1):
          ncg.set_ranges(((0.,4.),(2.,8.)))
        else:
          ncg.set_ranges(((2.,8.),(0.,4.)))
      else:
        raise Exception("Unknown method")

    # if 'field' is not in perm we only test reading the field from ncg2
    self._test_prepared_ncg(ncg, perm, coordinate_perm)

    # now try the same for the case where the field values are stored in a separate file
    ncg2 = NetCDFGrid(test_file_name2, ncg)
    self._test_prepared_ncg(ncg2, perm, coordinate_perm)


  # test all permutations of the calling sequence set_mask, set_ranges
  # including all permutations that only call 1 or 2 of these methods
  # also try out coordinate permutations lat,lon and lon,lat (the read nc file is lat,lon in both cases)
  def test_all_permutations(self):
    for n in range(1,4):
      for perm in itertools.permutations(['mask','ranges'], n):
        for coordinate_perm in ((0,1), (1,0)):
          self._test_permutation(perm, coordinate_perm)

  def test_all_permutations_with_fill_value(self):
    for n in range(1,4):
      for perm in itertools.permutations(['mask_from_fill_value','ranges'], n):
        for coordinate_perm in ((0,1), (1,0)):
          self._test_permutation(perm, coordinate_perm)

  def test_all_permutations_with_transposed_mask(self):
    for n in range(1,4):
      for perm in itertools.permutations(['transposed_mask','ranges'], n):
        for coordinate_perm in ((0,1), (1,0)):
          self._test_permutation(perm, coordinate_perm)

if __name__ == '__main__':
      unittest.main()
