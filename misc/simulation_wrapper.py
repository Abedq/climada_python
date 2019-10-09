import numpy as np
import pandas as pd
import sys
import os
import matplotlib.pyplot as plt
from climada.entity.exposures.gdp_asset import GDP2Asset
from climada.entity.exposures.gdp2a_multi import GDP2AMulti
from climada.entity.exposures.exp_people import ExpPop
from climada.entity.impact_funcs.flood import IFRiverFlood,flood_imp_func_set, assign_if_simple
from climada.hazard.flood import RiverFlood
from climada.hazard.centroids import Centroids
from climada.entity import ImpactFuncSet
from climada.util.constants import NAT_REG_ID

from climada.engine import Impact
from climada.engine.multi_exp import MultiImpact

RF_MODEL = ['ORCHIDEE',
            'CLM',
            'DBH',
            'H08',
            #'JULES-TUC',
            #'JULES-UoE',
            #'LPJmL',
            #'MATSIRO',
            #'MPI-HM',
            #'PCR-GLOBWB',
            #'WaterGAP'
            ]
CL_MODEL = ['princeton',
            'gswp3'
            #'watch',
            #'wfdei'        
            ]

PROT_STD = ['0', '100', 'flopros']

#Todo for cluster application
# set cluster true
# set output path
# set all countries
# set output dir

cluster = False

flood_dir = '/home/insauer/data/Fang/Benoit/'
gdp_path = '/home/insauer/data/Tobias/gdp_1850-2100_downscaled-by-nightlight_2.5arcmin_remapcon_new_yearly_shifted.nc'
output = '/home/insauer/data/TestData/'

if cluster:
    flood_dir = '/p/projects/ebm/data/hazard/floods/benoit_input_data'
    gdp_path = '/p/projects/ebm/data/exposure/gdp/processed_data/gdp_1850-2100_downscaled-by-nightlight_2.5arcmin_remapcon_new_yearly_shifted.nc'
years = np.arange(1971, 2011)
country_info = pd.read_csv(NAT_REG_ID)
isos = country_info['ISO'].tolist()
regs = country_info['Reg_name'].tolist()
conts = country_info['if_RF'].tolist()
l = len(years) * len(isos)
continent_names = ['Africa', 'Asia', 'Europe', 'NorthAmerica', 'Oceania', 'SouthAmerica']

dataDF = pd.DataFrame(data={'Year': np.full(l, np.nan, dtype=int),
                            'Country': np.full(l, "", dtype=str),
                            'Continent': np.full(l, "", dtype=str),
                            'Region': np.full(l, "", dtype=str),
                            'TotalAssetValue': np.full(l, np.nan, dtype=float),
                            'FloodedArea0': np.full(l, np.nan, dtype=float),
                            'FloodedArea100': np.full(l, np.nan, dtype=float),
                            'FloodedAreaFlopros': np.full(l, np.nan, dtype=float),
                            'ExpAsset0': np.full(l, np.nan, dtype=float),
                            'ExpAsset100': np.full(l, np.nan, dtype=float),
                            'ExpAssetFlopros': np.full(l, np.nan, dtype=float),
                            'ImpactAnnual0': np.full(l, np.nan, dtype=float),
                            'ImpactAnnual100': np.full(l, np.nan, dtype=float),
                            'ImpactAnnualFlopros': np.full(l, np.nan, dtype=float)
                            })
maxF = len(RF_MODEL) * len(CL_MODEL) * len(PROT_STD)
failureDF = pd.DataFrame(data={'rfModel': np.full(maxF, "", dtype=str),
                               'CLData': np.full(maxF, "", dtype=str),
                               'ProtStd': np.full(maxF, "", dtype=str),
                              })
if_set = flood_imp_func_set()

fail_lc = 0

for rf_mod in RF_MODEL:
    for cl_mod in CL_MODEL:
        line_counter = 0
        try:
            for cnt_ind in range(1,2):
                country = [isos[cnt_ind]]
                reg = regs[cnt_ind]
                #print(conts[cnt_ind]-1)
                cont = continent_names[int(conts[cnt_ind]-1)]
                for year in range(len(years)):
                
                    dataDF.iloc[line_counter, 0] = years[year]
                    dataDF.iloc[line_counter, 1] = country[0]
                    dataDF.iloc[line_counter, 2] = reg
                    dataDF.iloc[line_counter, 3] = cont
                    gdpa = GDP2Asset()
                    gdpa.set_countries(countries=country, ref_year=years[year], path = gdp_path)
                    gdpa.check()
                    
                    for pro_std in range(len(PROT_STD)):
                        dph_path = flood_dir +'flddph_{}_{}_{}_gev_0.1.nc'\
                           .format(rf_mod, cl_mod, PROT_STD[pro_std])
                        frc_path= flood_dir+'fldfrc_{}_{}_{}_gev_0.1.nc'\
                           .format(rf_mod, cl_mod, PROT_STD[pro_std])
                        
                        if not os.path.exists(dph_path):
                            print('{} path not found'.format(dph_path))
                            raise KeyError
                        if not os.path.exists(frc_path):
                            print('{} path not found'.format(frc_path))
                            raise KeyError
                        
                        
                        rf = RiverFlood()
                        rf.set_from_nc(dph_path=dph_path, frc_path=frc_path, countries=country, years=[years[year]])
                        
                        imp_fl=Impact()
                        imp_fl.calc(gdpa, if_set, rf)
                        rf.set_flooded_area()
                        dataDF.iloc[line_counter, 4] = imp_fl.tot_value
                        dataDF.iloc[line_counter, 5 + pro_std] = rf.fla_annual[0]
                        dataDF.iloc[line_counter, 8 + pro_std] = imp_fl.tot_value
                        dataDF.iloc[line_counter, 11 + pro_std] = imp_fl.at_event[0]
                        
                    line_counter+=1
            dataDF.to_csv(output + 'output_{}_{}_{}.csv'.format(rf_mod, cl_mod, PROT_STD[pro_std]))
        except KeyError:
            print('run failed')
            failureDF.iloc[fail_lc, 0] = rf_mod
            failureDF.iloc[fail_lc, 1] = cl_mod
            failureDF.iloc[fail_lc, 2] = PROT_STD[pro_std]
            fail_lc+=1
        except AttributeError:
            print('run failed')
            failureDF.iloc[fail_lc, 0] = rf_mod
            failureDF.iloc[fail_lc, 1] = cl_mod
            failureDF.iloc[fail_lc, 2] = PROT_STD[pro_std]
            fail_lc+=1
        except NameError:
            print('run failed')
            failureDF.iloc[fail_lc, 0] = rf_mod
            failureDF.iloc[fail_lc, 1] = cl_mod
            failureDF.iloc[fail_lc, 2] = PROT_STD[pro_std]
            fail_lc+=1
        except IOError:
            print('run failed')
            failureDF.iloc[fail_lc, 0] = rf_mod
            failureDF.iloc[fail_lc, 1] = cl_mod
            failureDF.iloc[fail_lc, 2] = PROT_STD[pro_std]
            fail_lc+=1
        except IndexError:
            print('run failed')
            failureDF.iloc[fail_lc, 0] = rf_mod
            failureDF.iloc[fail_lc, 1] = cl_mod
            failureDF.iloc[fail_lc, 2] = PROT_STD[pro_std]
            fail_lc+=1
                    

failureDF.to_csv(output + 'failure_{}_{}_{}.csv'.format(rf_mod, cl_mod, PROT_STD[pro_std]))                
        
                    
                
            