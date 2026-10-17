class PIDController:
    """
    Discrete-time velocity PID controller with implicit anti-windup clamping
    and derivative-on-measurement to prevent setpoint derivative kick.
    """
    
    def __init__(self, kp: float, ki: float, kd: float, dt: float, 
                 u_min: float, u_max: float, setpoint: float = 0.0):
        if dt <= 0.0:
            raise ValueError(f"PID sample period dt must be positive (got {dt}).")
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = float(dt)
        self.u_min = u_min
        self.u_max = u_max
        
        # History
        self.e_prev = 0.0
        self.e_prev2 = 0.0
        self.pv_prev = None
        self.pv_prev2 = None
        self.u_prev = 0.0
        self.setpoint = setpoint
        self._initialized = False

    def reset(self, initial_u: float = 0.0, initial_pv: float = None, setpoint: float = None):
        self.u_prev = initial_u
        if setpoint is not None:
            self.setpoint = setpoint
        if initial_pv is not None:
            e0 = self.setpoint - initial_pv
            self.e_prev = e0
            self.e_prev2 = e0
            self.pv_prev = initial_pv
            self.pv_prev2 = initial_pv
            self._initialized = True
        else:
            self.e_prev = 0.0
            self.e_prev2 = 0.0
            self.pv_prev = None
            self.pv_prev2 = None
            self._initialized = False

    def compute(self, setpoint: float, process_variable: float, dt: float = None) -> float:
        """
        Computes control action output using the velocity PID algorithm.
        Uses derivative-on-measurement (-kd/dt * (pv - 2*pv_prev + pv_prev2))
        and seeds initial error/measurement history on the first call to avoid startup kick.
        """
        step_dt = float(dt) if (dt is not None and dt > 0.0) else self.dt
        self.setpoint = setpoint
        e = setpoint - process_variable

        if not self._initialized:
            self.e_prev = e
            self.e_prev2 = e
            self.pv_prev = process_variable
            self.pv_prev2 = process_variable
            self._initialized = True
        
        # Velocity algorithm terms (derivative on measurement avoids setpoint kick)
        term_p = self.kp * (e - self.e_prev)
        term_i = self.ki * step_dt * e
        term_d = -(self.kd / step_dt) * (process_variable - 2.0 * self.pv_prev + self.pv_prev2)
        
        delta_u = term_p + term_i + term_d
        u = self.u_prev + delta_u
        
        # Clamping outputs (Physical limits provide implicit integral anti-windup)
        u_clamped = max(self.u_min, min(u, self.u_max))
        
        # Save states
        self.e_prev2 = self.e_prev
        self.e_prev = e
        self.pv_prev2 = self.pv_prev
        self.pv_prev = process_variable
        self.u_prev = u_clamped
        
        return u_clamped
