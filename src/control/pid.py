class PIDController:
    """Discrete-time velocity PID algorithm implementation."""
    
    def __init__(self, kp: float, ki: float, kd: float, dt: float, 
                 u_min: float, u_max: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.u_min = u_min
        self.u_max = u_max
        
        # History
        self.e_prev = 0.0
        self.e_prev2 = 0.0
        self.u_prev = 0.0

    def reset(self, initial_u: float = 0.0):
        self.e_prev = 0.0
        self.e_prev2 = 0.0
        self.u_prev = initial_u

    def compute(self, setpoint: float, process_variable: float) -> float:
        """Compute control action output using velocity algorithm."""
        e = setpoint - process_variable
        
        # Velocity algorithm terms
        term_p = self.kp * (e - self.e_prev)
        term_i = self.ki * self.dt * e
        term_d = (self.kd / self.dt) * (e - 2 * self.e_prev + self.e_prev2)
        
        delta_u = term_p + term_i + term_d
        u = self.u_prev + delta_u
        
        # Clamping outputs (Physical limits)
        u_clamped = max(self.u_min, min(u, self.u_max))
        
        # Save states
        self.e_prev2 = self.e_prev
        self.e_prev = e
        self.u_prev = u_clamped
        
        return u_clamped
