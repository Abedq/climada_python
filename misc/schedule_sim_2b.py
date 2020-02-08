#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import sys
import os
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import argparse
from climada.entity.exposures.gdp_asset import GDP2Asset
from climada.entity.exposures.exp_people import ExpPop
from climada.entity.impact_funcs.flood import IFRiverFlood,flood_imp_func_set, assign_if_simple
from climada.hazard.flood import RiverFlood
from climada.hazard.centroids import Centroids
from climada.entity import ImpactFuncSet
from climada.util.constants import NAT_REG_ID
import copy

from climada.engine import Impact

parser = argparse.ArgumentParser(
    description='run climada for different climate and runoff models')
parser.add_argument(
    '--RF_model', type=str, default='H08',
    help='runoff model')
parser.add_argument(
    '--CL_model', type=str, default='princeton',
    help='Climate model')
parser.add_argument(
    '--scenario', type=str, default='rcp26',
    help='Climate model')
args = parser.parse_args()

#Todo for cluster application
# set cluster true
# set output path
# set all countries
# set output dir


PROT_STD = ['0','flopros','100']
#for LPJ longrun
SCENARIO = ['rcp26',
            'rcp60']

#flood_dir = '/p/projects/ebm/data/hazard/floods/isimip2a-advanced/'
#flood_dir = '/p/projects/ebm/data/hazard/floods/benoit_input_data/'
gdp_path = '/p/projects/ebm/data/exposure/gdp/processed_data/gdp_1850-2100_downscaled-by-nightlight_2.5arcmin_remapcon_new_yearly_shifted.nc'
#pop_path = '/p/projects/ebm/data/exposure/population/hyde_ssp2_1860-2100_0150as_yearly_zip.nc4'
RF_PATH_FRC = '/p/projects/ebm/tobias_backup/floods/climada/isimip2a/flood_maps/fldfrc24_2.nc'
output = currentdir
#For lpj longrun
flood_dir = '/p/projects/ebm/data/hazard/floods/isimip2b/'
years = np.arange(2006, 2100)

#years = np.arange(1971, 2011)
country_info = pd.read_csv(NAT_REG_ID)
isos = country_info['ISO'].tolist()
regs = country_info['Reg_name'].tolist()
conts = country_info['if_RF'].tolist()
l = len(years) * len(isos)
continent_names = ['Africa', 'Asia', 'Europe', 'NorthAmerica', 'Oceania', 'SouthAmerica']

dataDF = pd.DataFrame(data={'Year': np.full(l, np.nan, dtype=int),
                            'Country': np.full(l, "", dtype=str),
                            'Region': np.full(l, "", dtype=str),
                            'Continent': np.full(l, "", dtype=str),
                            'TotalAssetValue': np.full(l, np.nan, dtype=float),
                            'TotalAssetValue2005': np.full(l, np.nan, dtype=float),
                            'FloodedArea0': np.full(l, np.nan, dtype=float),
                            'FloodedAreaFlopros': np.full(l, np.nan, dtype=float),
                            'FloodedArea100': np.full(l, np.nan, dtype=float),
                            'ImpFixExp0': np.full(l, np.nan, dtype=float),
                            'ImpFixExpFlopros': np.full(l, np.nan, dtype=float),
                            'ImpFixExp100': np.full(l, np.nan, dtype=float),
                            'Impact0': np.full(l, np.nan, dtype=float),
                            'ImpactFlopros': np.full(l, np.nan, dtype=float),
                            'Impact100': np.full(l, np.nan, dtype=float),
                            'ImpFixExp2y0': np.full(l, np.nan, dtype=float),
                            'ImpFixExp2yFlopros': np.full(l, np.nan, dtype=float),
                            'Impact2y0': np.full(l, np.nan, dtype=float),
                            'Impact2yFlopros': np.full(l, np.nan, dtype=float),
                            })

if_set = flood_imp_func_set()

fail_lc = 0
line_counter = 0

for cnt_ind in range(len(isos)):
    country = [isos[cnt_ind]]
    reg = regs[cnt_ind]
    #print(conts[cnt_ind]-1)
    cont = continent_names[int(conts[cnt_ind]-1)]
    gdpaFix = GDP2Asset()
    gdpaFix.set_countries(countries=country, ref_year=2005, path=gdp_path)
    save_lc = line_counter
    for prot_std in range(len(PROT_STD)):
        line_counter = save_lc
        dph_path = flood_dir + '{}/{}/{}/depth-150arcsec/flddph_annual_max_gev_0.1mmpd_protection-{}.nc'\
            .format(args.CL_model, args.RF_model, args.scenario, PROT_STD[prot_std])
        frc_path= flood_dir + '{}/{}/{}/area-150arcsec/fldfrc_annual_max_gev_0.1mmpd_protection-{}.nc'\
            .format(args.CL_model, args.RF_model, args.scenario, PROT_STD[prot_std])
        if not os.path.exists(dph_path):
            print('{} path not found'.format(dph_path))
            break
        if not os.path.exists(frc_path):
            print('{} path not found'.format(frc_path))
            break
        rf = RiverFlood()
        rf.set_from_nc(dph_path=dph_path, frc_path=frc_path, countries=country, years=years)
        rf2y = copy.copy(rf)
        rf2y.exclude_returnlevel(RF_PATH_FRC)
        rf.set_flooded_area()
        for year in range(len(years)):
            print('country_{}_year_{}_protStd_{}'.format(country[0], str(years[year]), PROT_STD[prot_std]))
            ini_date = str(years[year]) + '-01-01'
            fin_date = str(years[year]) + '-12-31'
            dataDF.iloc[line_counter, 0] = years[year]
            dataDF.iloc[line_counter, 1] = country[0]
            dataDF.iloc[line_counter, 2] = reg
            dataDF.iloc[line_counter, 3] = cont
            gdpa = GDP2Asset()
            gdpa.set_countries(countries=country, ref_year=years[year], path = gdp_path)
            imp_fl=Impact()
            imp_fl.calc(gdpa, if_set, rf.select(date=(ini_date, fin_date)))
            imp_fix=Impact()
            imp_fix.calc(gdpaFix, if_set, rf.select(date=(ini_date, fin_date)))
            if prot_std < 2:
                imp2y_fl=Impact()
                imp2y_fl.calc(gdpa, if_set, rf2y.select(date=(ini_date,fin_date)))
                imp2y_fix=Impact()
                imp2y_fix.calc(gdpaFix, if_set, rf2y.select(date=(ini_date,fin_date)))
                dataDF.iloc[line_counter, 15 + prot_std] = imp2y_fix.at_event[0]
                dataDF.iloc[line_counter, 17 + prot_std] = imp2y_fl.at_event[0]

            dataDF.iloc[line_counter, 4] = imp_fl.tot_value
            dataDF.iloc[line_counter, 5] = imp_fix.tot_value
            dataDF.iloc[line_counter, 6 + prot_std] = rf.fla_annual[year]
            dataDF.iloc[line_counter, 9 + prot_std] = imp_fix.at_event[0]
            dataDF.iloc[line_counter, 12 + prot_std] = imp_fl.at_event[0]
            line_counter+=1

    dataDF.to_csv('Isimip2b_Dam_{}_{}_{}_Full_2yr_24_01.csv'.format(args.RF_model, args.CL_model, args.scenario))