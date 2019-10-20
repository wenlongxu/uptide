# About uptide
uptide is a python package for tidal calculations. It computes tidal
free surface heights or velocities from the amplitudes and phases of the tidal
constituents. These amplitudes and phases can be read from global tidal
solutions such as [TPXO](http://volkov.oce.orst.edu/tides/) or [FES2014](https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html).
They can be read directly from the netCDF files provided by these sources. Some
limited functionality for tidal harmonic analysis is also available,

# Prerequisites
* python 3 or 2.7 (deprecated)
* numpy
* to read from netCDF sources: python netCDF support. The
[netCDF4](https://github.com/Unidata/netcdf4-python) package is 
recommended. To install:
```
sudo CC=mpicc pip install netcdf4
```

or use the python-netcdf4 package on Ubuntu and Debian.
* for FES2014 support: the [FES package](https://bitbucket.org/cnes_aviso/fes). To build from source
 (note that there is unfortunately no longer a simple pip install):
```
git clone git+https://bitbucket.org/cnes_aviso/fes.git
cd fes/
mkdir build
cmake ../ -DCMAKE_INSTALL_PREFIX=<prefix> -DBUILD_PYTHON=yes
make
make install
```
where `<prefix>` should be the installation. When using a python virtual environment you can use `$VIRTUAL_ENV`.
When using conda replace the above with a single step: `conda install -c fbriol fes` (untested).

# Functionality
## Reconstruction from given amplitudes and phases
Given the phase and amplitudes of the harmonic constituents (M2, S2, etc.) 
reconstruct the tidal signal at an arbitrary date and time (including nodal corrections).

```
import uptide
import datetime
tide = uptide.Tides(['M2', 'S2'])  # select which constituents to use
tide.set_initial_time(datetime.datetime(2001,1,1,12,0,0))  # set t=0 at 1 Jan 2001, UTC 12:00
amp = [2.0, 1.0]  # amplitudes of M2 and S2
pha = [0., 3.14159]  # phases (in radians!) for M2 and S2

import numpy as np
t = np.arange(0, 30*24*3600, 600)
import matplotlib.pyplot as plt
eta = tide.from_amplitude_phase(amp, pha, t)
plt.plot(t, eta)
plt.show()
```

If not timezone is provided, the initial datetime is assumed to be in UTC. Otherwise use [pytz](http://pytz.sourceforge.net/)
and do something like:
```
import pytz
adam = pytz.timezone('Europe/Amsterdam')
tide.set_initial_time(datetime.datetime(2001,1,1,12,0,0, tzinfo=adam))
```

Note that the nodal corrections (the 18.6 years cycle associated with [lunar precession](https://en.wikipedia.org/wiki/Lunar_precession)),
are only calculated for the date-time set with `set_initial_time` (t=0). If the time you calculate the signal for deviates significantly from `t=0`,
you can recompute the correction for any later time t:
```
tide.compute_nodal_corrections(t)
```

## Reconstruct the tide from global solutions like TPXO, FES04 or FES2014
For [TPXO](http://volkov.oce.orst.edu/tides/), we can only use those regional solutions (see [map here](http://volkov.oce.orst.edu/tides/region.html))
for which a netcdf version is given:
- Atlantic Ocean 2011:   ftp://ftp.oce.orst.edu/dist/tides/regional/AO_2011atlas_netcdf.tar.Z
- Bering Sea:   ftp://ftp.oce.orst.edu/dist/tides/regional/BerS_netcdf.tar.Z
- European Shelf 2008:   ftp://ftp.oce.orst.edu/dist/tides/regional/ES_netcdf.tar.Z
- Indian Ocean 2011:   ftp://ftp.oce.orst.edu/dist/tides/regional/IO_2011atlas_netcdf.tar.Z
- Mediterranean:   ftp://ftp.oce.orst.edu/dist/tides/regional/Med_netcdf.tar.Z
- Gulf of Mexico:   ftp://ftp.oce.orst.edu/dist/tides/regional/Mex_netcdf.tar.gz
- North Australia:   ftp://ftp.oce.orst.edu/dist/tides/regional/NAust_netcdf.tar.Z
- Pacific Ocean:   ftp://ftp.oce.orst.edu/dist/tides/regional/PO_2011atlas_netcdf.tar.Z


Each solution comes with a grid file, and a amplitude and phase file for the elevations (currents are currently not supported):
```
grid_file = '<some_path>/gridES2008.nc'
data_file = '<some_path>/hf.ES2008.nc'
tnci = OTPSncTidalInterpolator(tide, grid_file, data_file, ranges=((-4.0, 0.0), (58.0, 61.0)))
```
The optional `ranges` argument should give a longitude, lattiude bounding box of the region of interest (smaller means more efficient)

For [FES2014](https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html), 
after installing the [fes library](https://bitbucket.org/cnes_aviso/fes) following the instructions above, you can either use
```
tnci = uptide.FES2014TidalInterpolator('<path to an ocean_tide.ini file>')
tnci.set_initial_time(datetime.datetime(...)
```
in which case all constituents specified in the specified `ocean_tide.ini` are used, or
```
tnci = uptide.FES2014TidalInterpolator(tide, '<path to all the individual constituent files>')
```
where `tide` is a `Tides` object set-up as in the previous section. In the latter case it only uses the constituents specified in
the definition of `tide` and `t=0` is also defined based on the `tide`-object.

For either TPXO or FES2014, we can now obtain the reconstructed signal for time t, using
```
tnci.set_time(t)
eta = tnci.get_val(x)
```
where the tuple `x` is the longitude,latitude (TPXO) or latitude,longitude (FES2014) coordinates of the point of interest.

## From a given time signal compute the harmonic constituents
Given a time signal `eta` (say surface elevations) at times `t` (`eta` and `t` should be equal-length arrays)
we can do a harmonic analysis
```
amp,pha = uptide.harmonic_analysis(tide, eta, t)
```
where `amp` and `pha` are the amplitudes and phases of each constituent defined in `tide.constitunents`. So to get the "M2" amplitude and phase:
```
idx= tide.constituents.index('M2')
print("M2 amplitude and phase:", amp[idx], pha[idx])
```

Note that the harmonic analysis is a least squares inversion, which means that the result for each individual constituent may depend 
on what other constituents are specified in `tide` in particular constituents with a close frequency. You should therefore ensure that the time-period of the signal
is long enough to distinguish each pair of constituents. A useful criterion for this is given by the so called Rayleigh criterion. As an example, using the following code
you can use uptide to compute the minimum period needed to reliably resolve the M2 and S2 constituents
```
   print("Minimum period (days):", 2*pi/(uptide.tidal.omega['M2']-uptide.tidal.omega['S2'])/(24*3600.))
```
which gives (as expected) 14 days (a full spring-neap cycle).

For the harmonic analysis of a velocity signal. First do a harmonic analysis of the u and v components separately
```
au,pu = uptide.harmonic_analysis(tide, u, t)
av,pv = uptide.harmonic_analysis(tide, v, t)
```
after which you can use
```
a,b,theta,g = uptide.tidal_ellipse_parameters(au, pu, av, pv)
```
which returns the amplitudes along the major and minor axes (a and b), the inclination (theta), and the phase.
