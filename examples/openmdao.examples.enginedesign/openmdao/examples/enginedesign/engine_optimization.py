"""
    engine_optimization.py - Top level assembly for the example problem.
"""

# Optimize an engine disign using the driving_sim component.

# pylint: disable-msg=E0611,F0401
from openmdao.main.api import Assembly, set_as_top
from openmdao.lib.api import CONMINdriver

from openmdao.examples.enginedesign.driving_sim import DrivingSim

class EngineOptimization(Assembly):
    """Optimization of a Vehicle."""
    
    def __init__(self):
        """ Creates a new Assembly containing a DrivingSim and an optimizer"""
        
        super(EngineOptimization, self).__init__()

        # pylint: disable-msg=E1101
        
        # Create DrivingSim instance
        self.add_container('driving_sim', DrivingSim())

        # Create CONMIN Optimizer instance
        self.add_container('driver', CONMINdriver())
        
        # CONMIN Flags
        self.driver.iprint = 0
        self.driver.itmax = 30
        
        # CONMIN Objective 
        self.driver.objective = 'driving_sim.accel_time'
        
        # CONMIN Design Variables 
        self.driver.design_vars = ['driving_sim.spark_angle', 
                                         'driving_sim.bore' ]
        
        self.driver.lower_bounds = [-50, 65]
        self.driver.upper_bounds = [10, 100]
        

if __name__ == "__main__": # pragma: no cover         

    # pylint: disable-msg=E1101

    def prz(title):
        """ Print before and after"""
        
        print '---------------------------------'
        print title
        print '---------------------------------'
        print 'Engine: Bore = ', opt_problem.driving_sim.bore
        print 'Engine: Spark Angle = ', opt_problem.driving_sim.spark_angle
        print '---------------------------------'
        print '0-60 Accel Time = ', opt_problem.driving_sim.accel_time
        print 'EPA City MPG = ', opt_problem.driving_sim.EPA_city
        print 'EPA Highway MPG = ', opt_problem.driving_sim.EPA_highway
        print '\n'
    

    import time
    #import profile
    
    opt_problem = EngineOptimization()
    set_as_top(opt_problem)
    
    opt_problem.driving_sim.run()
    prz('Old Design')

    tt = time.time()
    opt_problem.run()
    prz('New Design')
    print "CONMIN Iterations: ", opt_problem.driver.iter_count
    print ""
    print "Elapsed time: ", time.time()-tt
    
# end engine_optimization.py
