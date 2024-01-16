"""
Code to make simulated PTA datasets with PINT
Created by Bence Becsy, Jeff Hazboun, Aaron Johnson
With code adapted from libstempo (Michele Vallisneri)
"""
import glob
import os
from dataclasses import dataclass
from astropy.time import TimeDelta

import scipy.constants as sc

from pint.residuals import Residuals
import pint.toa as toa
from pint import models
import pint.fitter

DAY_IN_SEC = 86400
YEAR_IN_SEC = 365.25 * DAY_IN_SEC
DMk = 4.15e3  # Units MHz^2 cm^3 pc sec
SOLAR2S = sc.G / sc.c**3 * 1.98855e30
KPC2S = sc.parsec / sc.c * 1e3
MPC2S = sc.parsec / sc.c * 1e6


@dataclass
class SimulatedPulsar:
    """
    Class to hold properties of a simulated pulsar
    """
    ephem: str = 'DE440'
    model: models.TimingModel = None
    toas: toa.TOAs = None
    residuals: Residuals = None
    name: str = None
    loc: dict = None

    def __repr__(self):
        return f"SimulatedPulsar({self.name})"

    def update_residuals(self):
        """Method to take the current TOAs and model and update the residuals with them"""
        self.residuals = Residuals(self.toas, self.model)

    def fit(self):
        """Refit the timing model and update everything"""
        #self.f = pint.fitter.WLSFitter(self.toas, self.model)
        #self.f = pint.fitter.GLSFitter(self.toas, self.model)
        #self.f = pint.fitter.DownhillGLSFitter(self.toas, self.model)
        self.f = pint.fitter.Fitter.auto(self.toas, self.model)
        self.f.fit_toas()
        self.model = self.f.model
        self.update_residuals()

    def write_partim(self, outpar: str, outtim: str, tempo2: bool = False):
        """Format for either PINT or Tempo2"""
        self.model.write_parfile(outpar)
        if tempo2:
            self.toas.write_TOA_file(outtim, format='Tempo2')
        else:
            self.toas.write_TOA_file(outtim)


def load_pulsar(parfile: str, timfile: str, ephem:str = 'DE440') -> SimulatedPulsar:
    """
    Load a SimulatedPulsar object from a par and tim file

    Parameters
    ----------
    parfile : str
        Path to par file
    timfile : str
        Path to tim file
    """
    if not os.path.isfile(parfile):
        raise FileNotFoundError("par file does not exist.")
    if not os.path.isfile(timfile):
        raise FileNotFoundError("tim file does not exist.")

    model = models.get_model(parfile)
    toas = toa.get_TOAs(timfile, ephem=ephem, planets=True)
    residuals = Residuals(toas, model)
    name = model.PSR.value

    try:
        loc = {'RAJ': model.RAJ.value, 'DECJ': model.DECJ.value}
    except AttributeError:
        loc = {'ELONG': model.ELONG.value, 'ELAT': model.ELAT.value}
    else:
        raise AttributeError("No pulsar location information (RAJ/DECJ or ELONG/ELAT) in parfile.")

    return SimulatedPulsar(ephem=ephem, model=model, toas=toas, residuals=residuals, name=name, loc=loc)


def load_from_directories(par_dir: str, tim_dir: str, ephem:str = 'DE440', num_psrs: int = None) -> list:
    """
    Takes a directory of par files and a directory of tim files and
    loads them into a list of SimulatedPulsar objects
    """
    unfiltered_pars = sorted(glob.glob(par_dir + "/*.par"))
    filtered_pars = [p for p in unfiltered_pars if ".t2" not in p]
    unfiltered_tims = sorted(glob.glob(tim_dir + "/*.tim"))
    combo_list = list(zip(filtered_pars, unfiltered_tims))
    psrs = []
    for par, tim in combo_list:
        if num_psrs:
            if len(psrs) >= num_psrs:
                break
        psrs.append(load_pulsar(par, tim, ephem=ephem))
    return psrs


def make_ideal(psr: SimulatedPulsar, iterations: int = 2):
    """
    Takes a pint.TOAs and pint.TimingModel object and effectively zeros out the residuals.
    """
    for ii in range(iterations):
        residuals = Residuals(psr.toas, psr.model)
        psr.toas.adjust_TOAs(TimeDelta(-1.0*residuals.time_resids))
    psr.update_residuals()
