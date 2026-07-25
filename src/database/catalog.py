class EquipmentCatalog:
    """Industrial catalog containing standard commercial equipment dimensions and sizes."""

    # ASME B36.10 Standard steel pipes (NPS, Outer Diameter m, Schedule 40 ID m, Schedule 80 ID m)
    PIPING_CATALOG = [
        {"nps": "0.5", "od": 0.0213, "sch40_id": 0.0158, "sch80_id": 0.0139},
        {"nps": "0.75", "od": 0.0267, "sch40_id": 0.0209, "sch80_id": 0.0189},
        {"nps": "1.0", "od": 0.0334, "sch40_id": 0.0266, "sch80_id": 0.0243},
        {"nps": "1.5", "od": 0.0483, "sch40_id": 0.0409, "sch80_id": 0.0381},
        {"nps": "2.0", "od": 0.0603, "sch40_id": 0.0525, "sch80_id": 0.0493},
        {"nps": "3.0", "od": 0.0889, "sch40_id": 0.0779, "sch80_id": 0.0737},
        {"nps": "4.0", "od": 0.1143, "sch40_id": 0.1023, "sch80_id": 0.0972},
        {"nps": "6.0", "od": 0.1683, "sch40_id": 0.1541, "sch80_id": 0.1463}
    ]

    # Standard industrial centrifugal pump motor powers in Watts (commercial sizes)
    PUMP_MOTOR_CATALOG = [
        180.0,   # 0.25 HP
        370.0,   # 0.5 HP
        750.0,   # 1.0 HP
        1500.0,  # 2.0 HP
        2200.0,  # 3.0 HP
        3700.0,  # 5.0 HP
        5500.0,  # 7.5 HP
        7500.0,  # 10.0 HP
        11000.0, # 15.0 HP
        15000.0  # 20.0 HP
    ]

    # Standard industrial vessel capacities in m^3
    VESSEL_VOLUME_CATALOG = [
        0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0
    ]

    @classmethod
    def select_pipe(cls, min_id_required: float, preferred_schedule: str = "sch40") -> dict:
        """Finds the smallest commercial pipe that satisfies the required internal diameter."""
        id_key = "sch40_id" if preferred_schedule == "sch40" else "sch80_id"
        for pipe in cls.PIPING_CATALOG:
            if pipe[id_key] >= min_id_required:
                return {
                    "nps": pipe["nps"],
                    "od_m": pipe["od"],
                    "id_m": pipe[id_key],
                    "schedule": preferred_schedule
                }
        return cls.PIPING_CATALOG[-1]  # Fallback to largest if none fit

    @classmethod
    def select_pump_motor(cls, hydraulic_power_required: float) -> float:
        """Finds the closest matching standard motor size in Watts (rounding up)."""
        for motor in cls.PUMP_MOTOR_CATALOG:
            if motor >= hydraulic_power_required:
                return motor
        return cls.PUMP_MOTOR_CATALOG[-1]

    @classmethod
    def select_vessel_volume(cls, required_volume: float) -> float:
        """Finds the closest matching commercial vessel size in m3 (rounding up)."""
        for vol in cls.VESSEL_VOLUME_CATALOG:
            if vol >= required_volume:
                return vol
        return cls.VESSEL_VOLUME_CATALOG[-1]
