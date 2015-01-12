
# ----------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------

import SUAVE
from SUAVE.Attributes import Units

import numpy as np
import pylab as plt

import copy, time

from SUAVE.Structure import (
Data, Container, Data_Exception, Data_Warning,
)


# ----------------------------------------------------------------------
#   Main
# ----------------------------------------------------------------------

def main():
    
    # setup the interface
    interface = setup_interface()
    
    inputs = Data()
    inputs.projected_span  = 20.
    inputs.fuselage_length = 40.
    inputs.cruise_distance = 1000.
    
    # evalute!
    results = interface.evaluate(inputs)
    
    # doesnt work...
    # print results
    
    return


# ----------------------------------------------------------------------
#   Optimization Interface Setup
# ----------------------------------------------------------------------

def setup_interface():
    
    # ------------------------------------------------------------------
    #   Instantiate Interface
    # ------------------------------------------------------------------
    
    interface = SUAVE.Optimization.Interface()
    
    # ------------------------------------------------------------------
    #   Vehicle and Analyses Information
    # ------------------------------------------------------------------
    
    from full_setup import full_setup
    
    configs,analyses = full_setup()
    
    interface.configs  = configs
    interface.analyses = analyses
    
    
    # ------------------------------------------------------------------
    #   Analysis Process
    # ------------------------------------------------------------------
    
    process = interface.process
    
    # the input unpacker
    process.unpack_inputs = unpack_inputs
    
    # size the base config
    process.simple_sizing = simple_sizing
    
    # finalizes the data dependencies
    process.finalize_ = finalize # doh!
    
    # the missions
    process.missions = missions
    
    # various performance studies
    process.field_length = field_length
    process.noise = noise
    
    # summarize the results
    process.summary = summarize
    
    # done!
    return interface
    
    
# ----------------------------------------------------------------------
#   Unpack Inputs Step
# ----------------------------------------------------------------------
    
def unpack_inputs(interface):
    
    inputs = interface.inputs
    
    # apply the inputs
    vehicle = interface.configs.base
    vehicle.wings['main_wing'].spans.project = inputs.projected_span
    vehicle.fuselages['fuselage'].length        = inputs.fuselage_length
    
    mission = interface.analyses.missions.base
    mission.segments.cruise.distance = inputs.cruise_distance
     
    return None


# ----------------------------------------------------------------------
#   Apply Simple Sizing Principles
# ----------------------------------------------------------------------

def simple_sizing(interface):
    
    from full_setup import simple_sizing
    
    simple_sizing(interface.configs)
    
    return None


# ----------------------------------------------------------------------
#   Finalizing Function (make part of optimization interface)[needs to come after simple sizing doh]
# ----------------------------------------------------------------------    

def finalize(interface):
    
    interface.configs.finalize()
    interface.analyses.finalize()
    interface.process.finalize()
    
    return None


# ----------------------------------------------------------------------
#   Process Missions
# ----------------------------------------------------------------------    

def missions(interface):
    
    missions = interface.analyses.missions
    
    results = missions.evaluate()
    
    return results
            
    
# ----------------------------------------------------------------------
#   Field Length Evaluation
# ----------------------------------------------------------------------    
    
def field_length(interface):
    
    # unpack tofl analysis
    estimate_tofl = SUAVE.Methods.Performance.estimate_take_off_field_length
    
    # unpack data
    configs  = interface.configs
    analyses = interface.analyses
    missions = interface.analyses.missions
    takeoff_airport = missions.base.airport
    
    # evaluate
    tofl = estimate_tofl( configs.takeoff,  analyses.configs.takeoff, takeoff_airport )
    tofl = tofl[0,0]
    
    # pack
    results = Data()
    results.takeoff_field_length = tofl
        
    return results


# ----------------------------------------------------------------------
#   Noise Evaluation
# ----------------------------------------------------------------------    

def noise(interface):
    
    # TODO - use the analysis
    
    # unpack noise analysis
    evaluate_noise = SUAVE.Methods.Noise.Correlations.shevell
    
    # unpack data
    vehicle = interface.configs.base
    results = interface.results
    mission_profile = results.missions.base
    
    weight_landing    = mission_profile.segments[-1].conditions.weights.total_mass[-1,0]
    number_of_engines = vehicle.propulsors['turbo_fan'].number_of_engines
    thrust_sea_level  = vehicle.propulsors['turbo_fan'].design_thrust
    thrust_landing    = mission_profile.segments[-1].conditions.frames.body.thrust_force_vector[-1,0]
    
    # evaluate
    results = evaluate_noise( weight_landing    , 
                              number_of_engines , 
                              thrust_sea_level  , 
                              thrust_landing     )
    
    return results
    
    
# ----------------------------------------------------------------------
#   Summarize the Data
# ----------------------------------------------------------------------    

def summarize(interface):
    
    vehicle = interface.configs.base
    
    results = interface.results
    mission_profile = results.missions.base
    
    
    # merge all segment conditions
    def stack_condition(a,b):
        if isinstance(a,np.ndarray):
            return np.vstack([a,b])
        else:
            return None
    
    conditions = None
    for segment in mission_profile.segments:
        if conditions is None:
            conditions = segment.conditions
            continue
        conditions = conditions.do_recursive(stack_condition,segment.conditions)
      
    # pack
    summary = SUAVE.Attributes.Results.Result()
    
    summary.weight_empty = vehicle.mass_properties.operating_empty
    
    summary.fuel_burn = max(conditions.weights.total_mass[:,0]) - min(conditions.weights.total_mass[:,0])
    
    #results.output.max_usable_fuel = vehicle.mass_properties.max_usable_fuel
    
    summary.noise = results.noise    
    
    summary.mission_time_min = max(conditions.frames.inertial.time[:,0] / Units.min)
    summary.max_altitude_km = max(conditions.freestream.altitude[:,0] / Units.km)
    
    summary.range_nmi = mission_profile.segments[-1].conditions.frames.inertial.position_vector[-1,0] / Units.nmi
    
    summary.field_length = results.field_length
    
    summary.stability = Data()
    summary.stability.cm_alpha = max(conditions.stability.static.cm_alpha[:,0])
    summary.stability.cn_beta  = max(conditions.stability.static.cn_beta[:,0])
    
    #summary.conditions = conditions
    
    #TODO: revisit how this is calculated
    summary.second_segment_climb_rate = mission_profile.segments[1].climb_rate
    
    return summary




if __name__ == '__main__':
    main()
    
    
    
    
    ## ------------------------------------------------------------------
    ##   Tests
    ## ------------------------------------------------------------------    
    
    #inputs = Data()
    #inputs.projected_span  = 1.0
    #inputs.fuselage_length = 1.0
    #inputs.cruise_distance = 1.0
    
    #strategy.unpack_inputs(interface,inputs)
    
    #import cPickle as pickle
    #i = pickle.dumps(strategy)
    #p = pickle.loads(i)
    
